from datetime import date, time

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from extensions import db
from models import Booking, TurfSettings
from routes.auth import bp as auth_bp
from routes.auth import current_customer, customer_login_required
from services.bookings import (
    ADVANCE_DEFAULT_BDT,
    BookingValidationError,
    SlotUnavailableError,
    create_booking_request,
)
from services.pricing import price_cards
from services.settings import why_points
from services.slots import (
    ALL_HOURS,
    PERIODS,
    booking_window,
    current_operating_day,
    date_chip_label,
    operating_day,
    period_of,
    slot_end,
    slot_label,
    slot_times,
    today_dhaka,
)

bp = Blueprint("public", __name__)

# Owner photos (M7.1, C-13), built from assets_raw/ by scripts/build_images.py into
# static/images/photos/<name>-{400,800,1280}.webp. All 4:3. Alt text describes only
# what is visible in each photo - no claims about facilities (D-23: developer-managed).
PHOTO_WIDTHS = (400, 800, 1280)
PHOTOS = [
    {"name": "night-floodlights", "alt": "The pitch at night under the floodlights, palm trees behind the fence"},
    {"name": "night-goal", "alt": "Floodlit pitch at night with a ball near the far goal"},
    {"name": "night-wide", "alt": "Wide view of the striped turf at night, floodlights along the palm-tree side"},
    {"name": "day-palms", "alt": "The pitch in daylight, striped turf with palm trees along the fence"},
    {"name": "day-netting", "alt": "Low view across the turf in sunshine, white lines and netting overhead"},
    {"name": "day-pitch", "alt": "The pitch in daylight from a corner, goal at the far end"},
]
PHOTO_BY_NAME = {p["name"]: p for p in PHOTOS}

# CR-12: the hero is the owner's floodlit night photo (it replaced the CR-7 illustration).
HERO_PHOTO = "night-wide"
# One photo per part of the day for the "One day, 24 hours" list, and the Find the ground backdrop.
DAY_PHOTOS = {"morning": "day-palms", "afternoon": "day-pitch", "night": "night-floodlights"}
VISIT_PHOTO = "night-goal"


BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


@bp.app_template_filter("taka")
def taka(amount) -> str:
    """4500 -> '৪,৫০০৳': Bangla digits and a trailing taka sign, like the reference site (CR-11)."""
    return f"{amount:,}".translate(BANGLA_DIGITS) + "৳"


@bp.context_processor
def inject_common():
    """Values every public template needs.

    show_todos / sections: whether TODO notes and empty sections show (D-50).
    slot_span: first open slot start and last open slot end, e.g. ("06:00 PM", "12:00 AM");
               None when all 24 hours are open ("Open 24 hours").
    now_year:  footer copyright.
    wa_link:   wa.me deep link, or "" when the owner has not given a number (C-06).
    book_href: every "Book now" link - the inline picker on the homepage,
               the booking page everywhere else (#book only exists on /).
    """
    settings = TurfSettings.current_or_default()
    digits = (settings.whatsapp or "").strip()
    show_todos = current_app.config["SHOW_TODO_NOTES"]
    times = slot_times(settings)
    return {
        "show_todos": show_todos,
        # D-50: in production a section with nothing real to show is hidden (with its links)
        "sections": {
            "pricing": show_todos or bool(price_cards(settings)),
            "location": show_todos or any(_is_real(v) for v in (settings.address, settings.map_embed_url, settings.map_link)),
            "reviews": show_todos or bool(settings.reviews),
            "why": show_todos or bool(why_points(settings)),
            "rules": show_todos or _is_real(settings.booking_rules_text),
        },
        "slot_span": None if len(times) == len(ALL_HOURS) else (slot_label(times[0]), slot_label(slot_end(times[-1]))),
        "now_year": today_dhaka().year,
        "wa_link": f"https://wa.me/{digits}" if digits else "",
        "book_href": "#book" if request.endpoint == "public.home" else url_for("public.book"),
    }


# The sign-in page (auth blueprint) shows the same nav and footer. Not app-wide: the
# error pages must not read the database (the 500 page shows when the database fails).
auth_bp.context_processor(inject_common)


@bp.app_template_global("is_real")
def _is_real(value) -> bool:
    """True when an owner text field has real content, not empty or still a TODO."""
    return bool(value and "TODO" not in value and value.strip())


def _local_business_json_ld(settings: TurfSettings) -> dict:
    """LocalBusiness structured data (M7.3). Only confirmed fields - never invented."""
    data = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": settings.turf_name or "TTURFZONE",
        "url": request.url_root,
        "image": url_for("static", filename="images/photos/night-floodlights-1280.webp", _external=True),
        "logo": url_for("static", filename="icons/apple-touch-icon.png", _external=True),
    }
    if _is_real(settings.facebook_url):
        data["sameAs"] = [settings.facebook_url.strip()]
    if _is_real(settings.about_text):
        data["description"] = settings.about_text.strip()
    if _is_real(settings.phone):
        data["telephone"] = settings.phone.strip()
    if _is_real(settings.address):
        data["address"] = settings.address.strip()
    return data


def _date_chips():
    """Bookable operating days for the slot picker: [{"iso", "label"}, ...], Dhaka time (D-10, D-52)."""
    days = TurfSettings.current_or_default().booking_window_days or 14
    return [{"iso": d.isoformat(), "label": date_chip_label(d)}
            for d in booking_window(current_operating_day(), days)]


def _day_label(iso: str) -> str:
    """'2026-11-11' -> 'Wednesday, November 11, 2026' (the picker's heading line, CR-11)."""
    d = date.fromisoformat(iso)
    return f"{d:%A, %B} {d.day}, {d.year}"


def _preselect_day(form) -> str:
    """The operating day to open the picker on: a night slot after midnight (real date
    Thursday 01:00) belongs to the evening before (Wednesday)."""
    try:
        return operating_day(date.fromisoformat(form["date"]), time.fromisoformat(form["slot"])).isoformat()
    except ValueError:
        return form["date"]


def _render_booking_page(form, errors):
    """Render the booking page with the picker + details form (GET, or a failed POST)."""
    chips = _date_chips()
    valid = {chip["iso"] for chip in chips}
    wanted = _preselect_day(form)
    preselect_date = wanted if wanted in valid else chips[0]["iso"]
    settings = TurfSettings.current_or_default()
    return render_template(
        "booking.html",
        settings=settings,
        slot_labels=[slot_label(t) for t in slot_times()],
        date_chips=chips,
        preselect_date=preselect_date,
        preselect_label=_day_label(preselect_date),
        preselect_slot=form["slot"],
        periods=PERIODS,
        form=form,
        errors=errors,
        advance=_advance(settings),
        bkash_number=settings.bkash_number if _is_real(settings.bkash_number) else "",
    )


@bp.get("/")
def home():
    """Homepage. All business content comes from turf_settings (plan D-13)."""
    settings = TurfSettings.current_or_default()
    chips = _date_chips()
    return render_template(
        "index.html",
        settings=settings,
        slot_labels=[slot_label(t) for t in slot_times()],
        day_rows=_day_rows(settings),
        date_chips=chips,
        preselect_date=chips[0]["iso"],
        preselect_label=_day_label(chips[0]["iso"]),
        periods=PERIODS,
        json_ld=_local_business_json_ld(settings),
        photos=PHOTOS,
        why=why_points(settings),
        rules=[line.strip() for line in (settings.booking_rules_text or "").splitlines()
               if line.strip() and "TODO" not in line][:10],
        hero=PHOTO_BY_NAME[HERO_PHOTO],
        visit_photo=PHOTO_BY_NAME[VISIT_PHOTO],
        advance=_advance(settings),
        booking_open=_is_real(settings.bkash_number),
    )


def _day_rows(settings) -> list[dict]:
    """Rows for "One day, 24 hours" (CR-12): each open part of the day with its price per hour
    (None until the owner sets it) and its photo. Prices come from the same function as the
    slot cards (D-53)."""
    prices = {card["key"]: card["price_bdt"] for card in price_cards(settings)}
    open_keys = {period_of(t) for t in slot_times(settings)}
    return [{"key": p["key"], "name": p["name"], "span": p["span"], "price_bdt": prices.get(p["key"]),
             "photo": PHOTO_BY_NAME[DAY_PHOTOS[p["key"]]]}
            for p in PERIODS if p["key"] in open_keys]


def _advance(settings) -> int:
    return settings.advance_bdt or ADVANCE_DEFAULT_BDT


@bp.get("/book")
@customer_login_required
def book():
    """Booking page: date + slot picker (preselected from the query), bKash payment box
    and the details form (CR-9). Signed-in customers only."""
    form = {
        "name": current_customer().get("name", ""),
        "phone": "",
        "payer_number": "",
        "trx_id": "",
        "no_refund": "",
        "date": request.args.get("date", ""),
        "slot": request.args.get("slot", ""),
    }
    return _render_booking_page(form, errors={})


@bp.post("/book")
@customer_login_required
def book_submit():
    """Create a PENDING booking that waits for the owner to check the bKash payment (CR-9).

    The server re-validates everything (D-04). The email is the Google session's, never
    the form's. The slot is held until the owner confirms or rejects.
    """
    form = {key: request.form.get(key, "").strip()
            for key in ("name", "phone", "payer_number", "trx_id", "no_refund", "date", "slot")}
    settings = TurfSettings.current_or_default()
    if not _is_real(settings.bkash_number):
        return _render_booking_page(form, {}), 400  # the page itself says booking isn't open yet
    if not form["no_refund"]:
        return _render_booking_page(form, {"no_refund": "Please confirm you understand the advance isn't refunded if you cancel."}), 400

    try:
        booking_date = date.fromisoformat(form["date"])
        slot_time = time.fromisoformat(form["slot"])
    except ValueError:
        return _render_booking_page(form, {"slot": "Pick a date and time above."}), 400

    try:
        booking = create_booking_request(
            form["name"], form["phone"], booking_date, slot_time,
            email=current_customer()["email"], payer_number=form["payer_number"], trx_id=form["trx_id"])
    except BookingValidationError as exc:
        return _render_booking_page(form, exc.errors), 400
    except SlotUnavailableError:
        return _render_booking_page(
            form, {"slot": "Sorry, that slot was just taken. Please pick another."}
        ), 409

    session["booking_request"] = booking.id
    return redirect(url_for("public.booking_success"))


@bp.get("/book/success")
def booking_success():
    """One-time confirmation, read from the session (D-11). Refresh -> home."""
    booking_id = session.pop("booking_request", None)
    booking = db.session.get(Booking, booking_id) if booking_id else None
    if booking is None:
        return redirect(url_for("public.home"))

    settings = TurfSettings.current_or_default()
    slot_display = slot_label(booking.slot_time)
    wa_text = (
        f"Hi, I booked at {settings.turf_name or 'TTURFZONE'} and paid the bKash advance. "
        f"Booking ID: {booking.booking_code}, TrxID: {booking.trx_id}, "
        f"Date: {booking.booking_date:%d %b %Y}, Time: {slot_display}"
    )
    return render_template(
        "booking_success.html",
        settings=settings,
        booking=booking,
        slot_display=slot_display,
        end_display=slot_label(slot_end(booking.slot_time)),
        date_display=f"{booking.booking_date:%A, %d %b %Y}",
        wa_text=wa_text,
        confirm_note=settings.confirm_time_text.strip() if _is_real(settings.confirm_time_text) else "",
    )


@bp.get("/privacy")
def privacy():
    """What the booking collects and why (CR-9; Google's sign-in screen links here)."""
    return render_template("privacy.html", settings=TurfSettings.current_or_default())


@bp.get("/healthz")
def healthz():
    """Uptime check. Must not touch the database (plan D-12)."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}
