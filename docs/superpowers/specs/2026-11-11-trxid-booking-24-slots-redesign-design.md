# TTURFZONE: bKash TrxID booking, 24 hourly slots, reference-style redesign

Status: design for approval (2026-11-11). Becomes CR-9, CR-10, CR-11 in `docs/PROJECT_PLAN.md` once approved.

## Why

- The owner has only a bKash **merchant number** (01827881299), no Payment Gateway API keys, so the site cannot verify payments by itself. The client accepts a manual check: the customer pays the advance, types the transaction ID (TrxID), and the owner confirms.
- The client wants **24 one-hour slots** around the clock, grouped Morning / Afternoon / Night.
- The client wants the site to **look like https://turfxsonagazi.com/** (studied 2026-11-11).

Success: a customer signs in with Google, picks an hour, pays ৳500 by bKash Payment, submits the TrxID, sees "payment being checked", and gets an email from tturfzone@gmail.com when the owner confirms. The public site looks and flows like the reference with TTURFZONE's own photos, logo and text.

## Decided by the developer (2026-11-11)

1. Pay to the bKash merchant number, enter the TrxID while booking; the owner confirms from the admin; on confirmation an email goes to the customer **from tturfzone@gmail.com**.
2. **Google sign-in is required to book** (like the reference). The customer's email comes from Google. Reverses D-35 ("an account is never required").
3. **24 slots of 60 minutes.** Tabs: **Morning 6 AM–12 PM** (6 slots), **Afternoon 12 PM–6 PM** (6), **Night 6 PM–6 AM** (12).
4. **One hour per booking.** Two hours = two bookings.
5. A submitted request **holds its slot until the owner confirms or rejects** it (no auto-release).
6. Advance: **৳500** (C-22), balance at the ground. **No refund on cancellation.**
7. Look: like the reference.

## Not copied from the reference

Layout, structure, colours, card style and flow are matched. Their code, photos, logo and wording are not: TTURFZONE's own assets and the owner's own text go in. Their "Why Choose Us" and "Ground Rules" claims (FIFA grass, CCTV, changing rooms…) are business facts: ours show only what the owner enters (never-invent rule, D-50 hiding when empty).

## Part A: 24 hourly slots (CR-10)

- `SLOT_MINUTES = 60`; the 24 starts are 00:00 … 23:00.
- **Operating day.** Day D runs from 06:00 on D to 06:00 on D+1. Periods: Morning 06:00–11:00 starts, Afternoon 12:00–17:00, Night 18:00–23:00 then 00:00–05:00 (on D+1).
- **Storage is the real calendar date + time** (unchanged columns). A slot's operating day = its date if time ≥ 06:00, else date − 1. The unique slot rule (`uq_active_slot` / `active_slot_key`, D-42) is untouched.
- **Cards show the real date** of the slot: Wednesday's Night tab shows "Thu 12 Nov, 1:00 AM" for the after-midnight hours. *(Builder's call, chosen so nobody arrives a day late; the reference shows the evening's date.)*
- "Today" (first selectable operating day) = date of (now_dhaka − 6 h). At 03:00 Thursday the Wednesday night slots 03:00–05:00 are still bookable under Wednesday. The booking window counts operating days from there (`booking_window_days`, default 14).
- "Past" = the slot's real start ≤ now_dhaka (unchanged rule, real datetimes).
- `/api/availability?date=D` returns the 24 slots of operating day D in order 06:00 … 05:00, each `{time, label, date, period, state, price_bdt}`. Still no customer data.
- **Pricing = three prices**, one per period (Morning, Afternoon, Night), set once in Settings and applied to every day until changed (developer, 2026-11-11). A slot's price is its period's price; no weekday/weekend split, no bands, no default price. Stored in `turf_settings.pricing` as `{"morning": int, "afternoon": int, "night": int}`. Supersedes D-46/D-47 (C-31 obsolete).
- **Date buttons show dates** ("Wed 11 Nov"), never "Today"/"Tomorrow" (developer, 2026-11-11).
- **Open hours replace the slot-time editor (D-48).** `turf_settings.slot_times` keeps its column and type but now means "which of the 24 hourly starts are offered" (NULL = all 24). Settings shows 24 checkboxes grouped by period. Unticked hours are hidden from customers. Unticking an hour with upcoming PENDING/CONFIRMED/BLOCKED bookings is refused, naming them (reuses `stranded_bookings`). No migration: production has `slot_times` NULL and no prices yet. *(Builder's call; keeps CR-6's "owner controls the timings" without free-form times.)*
- Admin calendar: one operating day, 24 rows in the three period groups.

## Part B: Google sign-in, TrxID, owner confirmation, email (CR-9)

### Google sign-in
- OAuth 2.0 authorization-code flow written with the standard library (`urllib`), **no new dependency**: `GET /auth/google` (stores a random `state` and a safe `next` in the session, redirects to Google with scopes `openid email profile`), `GET /auth/google/callback` (checks `state`, exchanges the code at Google's token endpoint, reads the userinfo endpoint server-to-server, requires `email_verified`), `POST /auth/logout`.
- Session key `customer = {sub, email, name}`. Admin login/logout still clear the whole session (owner and customer are different people).
- `GET /login` = the "Continue with Google" page. `/book` and `POST /book` redirect there (with `next`) when signed out.
- Env: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. Redirect URI `SITE_URL + /auth/google/callback`.
- New page `/privacy`: plain description of what is collected (Google name + email, phone, bKash number paid from, TrxID), why (bookings only), not shared. Google's consent screen needs it.

### Booking with a TrxID
- Booking page (signed in): slot summary (real date, time, price), payment box: "Open bKash → **Payment** → merchant number **{bkash_number}** → amount **৳{advance_bdt}**", then fields: **name** (prefilled from Google, editable), **phone**, **bKash number you paid from**, **TrxID**, required checkbox "I understand the advance is not refunded if I cancel". The Google email is shown, not editable.
- TrxID: trimmed, upper-cased, 8–12 letters/digits *(builder's call; bKash IDs are 10)*. **Unique across all bookings (database unique index)**, so one payment can't confirm two slots. Known limit: a wrongly rejected TrxID can't be reused; the owner books that customer by hand later (M5.6) or un-rejects in the database.
- `create_booking_request` inserts **PENDING** (existing status, already holds the slot) with `customer_email`, `payer_number`, `trx_id`. `PAYMENTS_ENABLED=false` now means this flow; `true` stays reserved for a future gateway (still raises).
- New booking columns (one migration): `customer_email` String(254), `payer_number` String(11), `trx_id` String(20) unique. All nullable (blocks have none).
- Success page: "Payment being checked", booking code, slot, TrxID, "We'll email {email} when it's confirmed", WhatsApp link if set.
- Public grid shows PENDING like CONFIRMED (unavailable, "Booked"). *(Builder's call; matches the reference, customers don't need the difference.)*
- Settings gain **bKash merchant number** and **advance amount** (default 500). If no bKash number is set, the booking form says online booking isn't open yet (production: the owner/developer enters 01827881299 in Settings; it is not hard-coded).

### Owner confirmation and email
- Dashboard leads with **"Payments to check"**: each PENDING row with TrxID, payer number, amount, slot, customer; Confirm / Reject (existing actions). The owner checks the TrxID and sender in the bKash merchant app.
- Confirm → CONFIRMED + email "Your TTURFZONE booking is confirmed" (code, date, time, advance paid, balance due at the ground, rules). Reject → REJECTED (slot free) + email "We couldn't confirm your payment" (contact details).
- Email is sent after the status is saved. **A failed email never undoes the confirm/reject**: the owner sees "Confirmed, but the email couldn't be sent" and a **Resend email** button on the booking (`POST /admin/bookings/<id>/email`).
- Sending: **Gmail API over HTTPS** as tturfzone@gmail.com. The host blocks outgoing SMTP: on 2026-11-11 ports 465 and 587 to smtp.gmail.com were unreachable over both IPv6 and IPv4, while HTTPS works. Standard library only (`urllib`): refresh-token grant at `https://oauth2.googleapis.com/token` → access token (cached in memory until it expires) → `POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with the base64url MIME message. Scope `gmail.send` only (send, never read).
- One-time authorisation, on the developer's PC, never on the server: `flask gmail-authorize` opens Google's consent page for tturfzone@gmail.com (local redirect `http://localhost:5000/...`), then prints a **refresh token** once. That goes into the cPanel environment as `GMAIL_REFRESH_TOKEN`, with the same `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` as sign-in. It is a secret: never in the repo, the database or the logs.
- `services/mailer.send_email` keeps its signature and uses the Gmail API when `GMAIL_REFRESH_TOKEN` is set. The SMTP path stays for any host where SMTP works. The forgot-password email (M5.10) uses the same transport. `MAIL_FROM = TTURFZONE <tturfzone@gmail.com>`. Replaces the noreply mailbox of D17.
- The Google Cloud project must be **"In production"**, not "Testing". In Testing, refresh tokens expire after 7 days and the emails would silently stop. Because `gmail.send` is a sensitive scope and the app is unverified, the owner sees "Google hasn't verified this app" once during authorisation (Advanced → continue). Customers only ever see the plain sign-in scopes.
- If the refresh token stops working (password change, access revoked), sends fail. Confirm/reject still save and the owner sees "email couldn't be sent", then re-runs `gmail-authorize`.

## Part C: reference-style look (CR-11)

Public pages only; the admin keeps its current look.

- **Theme:** light by default (white/grey surfaces, green accent), dark mode via a header toggle remembered in `localStorage` (set before paint, no flash).
- **Header:** logo, Home / Book Turf / Pricing / About Us / Contact, theme toggle, **Login** button (Google) or the customer's name with Sign out.
- **Hero:** full-width photo slideshow with dots (our real photos plus the CR-7 illustration), "Welcome to TTURFZONE", the owner's tagline, "Book Your Slot". Autoplay off under `prefers-reduced-motion`.
- **Book Your Turf:** heading + full date; a card with ‹ date › (native date input, min/max = window) and **Available / Booked** counts for the operating day; tabs Morning / Afternoon / Night; slot cards in 3 / 2 / 1 columns: logo emblem, status pill (Available / Booked / Past), time range, "60 mins", real date, price, **BOOK NOW**. Booked cards show the price in red with no button.
- **Pricing:** one card per period with its price (60 min). Hidden until prices exist (D-50).
- **About Our Turf:** gallery (existing photos + lightbox).
- **Why Choose Us:** owner-entered list (title + one line each) in Settings, stored in the unused `turf_settings.facilities` column. Hidden when empty.
- **Ground Rules:** the owner's `booking_rules_text`, one rule per line, shown as cards; the no-refund rule is always shown on the booking page regardless.
- **Contact:** phone, WhatsApp, email (tturfzone@gmail.com), location + map when set; footer with the same plus opening hours.
- Prices in **Bangla digits** like the reference (`১,০০০৳`) on public pages. *(Builder's call.)*
- The sticky mobile WhatsApp / Book now bar **stays** (brief §2 requires it), restyled to match. *(Builder's call; the reference has none.)*

## Order of work

1. Part A (slots), because every other screen depends on the slot model.
2. Part B (sign-in, TrxID, confirm + email), after the SMTP port test.
3. Part C (look), last, on top of the final flow.

Each part: tests first, `pytest -q` and `pytest -m mariadb` green, plan updated, committed and pushed separately.

## Out of scope

Customer "my bookings" page, customer self-cancel, SMS, the bKash gateway (M10, kept for later), CR-3 phone-OTP accounts (superseded by Google sign-in), admin restyle, admin manual booking (M5.6).

## Setup the developer does (no secrets in the repo)

- Google Cloud Console: project → OAuth consent screen (External, app name TTURFZONE, support email, privacy policy URL `https://tturfzone.com/privacy`, scopes openid/email/profile) → **Publish** → OAuth client (Web) with redirect URIs `https://tturfzone.com/auth/google/callback` and `http://localhost:5000/auth/google/callback` → put the client ID and secret in the cPanel Python App environment.
- In the same project: enable the **Gmail API**; add the `gmail.send` scope to the consent screen; set publishing status to **In production**.
- tturfzone@gmail.com: 2-step verification on. On the developer's PC: `flask gmail-authorize`, sign in as tturfzone@gmail.com, then copy the printed refresh token into the cPanel environment as `GMAIL_REFRESH_TOKEN`, plus `MAIL_FROM=TTURFZONE <tturfzone@gmail.com>`.
- Check the server reaches the Gmail API: `curl -s -o /dev/null -w '%{http_code}\n' https://gmail.googleapis.com/` (any 3-digit code means it's reachable; `000` means blocked).

## Plan changes on approval

- CR-9 (TrxID + owner confirmation + Google sign-in + Gmail), CR-10 (24 hourly slots), CR-11 (reference look).
- Superseded or amended: CR-2's "no manual confirmation", D-35 and CLAUDE.md's "guest booking never behind login" rule, CR-3's phone-OTP login, D-09/D-48 (slot editing → open hours), D-17 mailbox, CR-5 (an owner-entered "Why Choose Us" returns), "Reference site, inspiration only" in §1.
