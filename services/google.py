"""Google sign-in (CR-9) over plain HTTPS, standard library only (no new dependency).

Authorization-code flow for a web app with a client secret:
  1. sign_in_url(state) sends the customer to Google;
  2. Google returns to SITE_URL/auth/google/callback with ?code=&state=;
  3. user_from_code(code) swaps the code for an access token at Google's token
     endpoint and reads the user's profile from the userinfo endpoint.
Both calls go from our server straight to Google over HTTPS, so the answers can be
trusted without checking a signed ID token.

The three _post_form / _get_json / _post_json helpers are the only network calls;
tests replace them. Never log tokens, codes or response bodies.
"""
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
TIMEOUT_SECONDS = 15


class GoogleError(Exception):
    """Any failure talking to Google. The message never contains tokens or bodies."""


def _read_json(request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise GoogleError(f"Google answered HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise GoogleError(f"Google request failed ({type(exc).__name__})") from None


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode("ascii")
    return _read_json(urllib.request.Request(url, data=body, method="POST"))


def _get_json(url: str, token: str) -> dict:
    return _read_json(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}))


def _post_json(url: str, token: str, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return _read_json(request)


def callback_url() -> str:
    """Where Google sends the customer back. Built from SITE_URL, never the request Host."""
    return current_app.config["SITE_URL"].rstrip("/") + "/auth/google/callback"


def sign_in_url(state: str) -> str:
    """Google's sign-in page for this app, asking only for the name and email."""
    query = urllib.parse.urlencode({
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": callback_url(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    return f"{AUTH_URL}?{query}"


def user_from_code(code: str) -> dict:
    """{"sub", "email", "name"} for the Google account that just signed in.

    Raises GoogleError on any failure, or when Google hasn't verified the email.
    """
    tokens = _post_form(TOKEN_URL, {
        "code": code,
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": callback_url(),
        "grant_type": "authorization_code",
    })
    access_token = tokens.get("access_token")
    if not access_token:
        raise GoogleError("no access token in Google's answer")
    profile = _get_json(USERINFO_URL, access_token)
    email = (profile.get("email") or "").strip().lower()
    if not email or profile.get("email_verified") is not True:
        raise GoogleError("Google account email is not verified")
    return {"sub": str(profile.get("sub", "")), "email": email, "name": (profile.get("name") or "").strip()}


# --- Gmail API: booking emails from tturfzone@gmail.com (CR-9) -------------------------
# The host blocks outgoing SMTP (ports 465/587), so mail goes over HTTPS. The developer
# authorises the Gmail account once on their PC (`flask gmail-authorize`), which prints a
# refresh token for the GMAIL_REFRESH_TOKEN environment variable. Scope: send only.

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_REDIRECT_URI = "http://localhost:8765/gmail-callback"  # registered on the Google client
_gmail_token: dict = {}  # {"value": access token, "expires": unix time}; per process, never logged


def gmail_access_token() -> str:
    """A short-lived Gmail access token from the refresh token, reused until 60 s before it expires."""
    if _gmail_token and time.time() < _gmail_token["expires"] - 60:
        return _gmail_token["value"]
    cfg = current_app.config
    answer = _post_form(TOKEN_URL, {
        "client_id": cfg["GOOGLE_CLIENT_ID"],
        "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
        "refresh_token": cfg["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    if not answer.get("access_token"):
        raise GoogleError("no access token for Gmail (re-run flask gmail-authorize?)")
    _gmail_token.update(value=answer["access_token"], expires=time.time() + int(answer.get("expires_in", 3600)))
    return _gmail_token["value"]


def gmail_send(raw_message: bytes) -> None:
    """Send one RFC 822 message as the authorised Gmail account. Raises GoogleError."""
    token = gmail_access_token()
    try:
        _post_json(GMAIL_SEND_URL, token, {"raw": base64.urlsafe_b64encode(raw_message).decode("ascii")})
    except GoogleError:
        _gmail_token.clear()  # a refused token is dropped; the next send fetches a new one
        raise


def gmail_consent_url(state: str) -> str:
    """Google's consent page asking the Gmail account for permission to send email."""
    query = urllib.parse.urlencode({
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return f"{AUTH_URL}?{query}"


def refresh_token_from_code(code: str) -> str:
    """Swap the one-time consent code for a long-lived refresh token. Raises GoogleError."""
    cfg = current_app.config
    answer = _post_form(TOKEN_URL, {
        "code": code,
        "client_id": cfg["GOOGLE_CLIENT_ID"],
        "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": GMAIL_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if not answer.get("refresh_token"):
        raise GoogleError("Google gave no refresh token")
    return answer["refresh_token"]
