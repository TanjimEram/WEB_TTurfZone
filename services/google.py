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
import json
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
