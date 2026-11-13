"""Emails to the customer when the owner confirms or rejects a bKash payment (CR-9).

Sent after the status change is committed and never undo it: a failure is logged
(exception type only) and reported back, so the admin can show "Resend email".
"""
from flask import current_app

from extensions import db
from models import Booking, TurfSettings
from models._time import utcnow
from services.bookings import ADVANCE_DEFAULT_BDT
from services.mailer import mail_configured, send_email
from services.pricing import price_for
from services.slots import slot_end, slot_label


def _taka(amount: int) -> str:
    return f"৳{amount:,}"


def booking_email(booking: Booking, settings: TurfSettings) -> tuple[str, str]:
    """(subject, plain-text body) for a CONFIRMED or REJECTED booking."""
    name = settings.turf_name or "TTURFZONE"
    when = (f"{booking.booking_date:%a %d %b %Y}, "
            f"{slot_label(booking.slot_time)} – {slot_label(slot_end(booking.slot_time))}")
    contact = " · ".join(v for v in (settings.phone, "tturfzone@gmail.com") if v and "TODO" not in v)

    if booking.status == Booking.CONFIRMED:
        advance = settings.advance_bdt or ADVANCE_DEFAULT_BDT
        price = price_for(settings, booking.slot_time)
        lines = [
            f"Hi {booking.customer_name},",
            "",
            f"Your {name} booking is confirmed. We received your bKash advance.",
            "",
            f"Booking ID: {booking.booking_code}",
            f"When: {when}",
            f"Advance paid: {_taka(advance)} (bKash TrxID {booking.trx_id})",
        ]
        if price and price > advance:
            lines.append(f"Pay at the ground: {_taka(price - advance)}")
        if settings.booking_rules_text and "TODO" not in settings.booking_rules_text:
            lines += ["", "Rules:", settings.booking_rules_text.strip()]
        lines += ["", "The advance is not refunded if you cancel.", "", f"See you on the pitch. {contact}"]
        return f"Your {name} booking is confirmed ({booking.booking_code})", "\n".join(lines)

    lines = [
        f"Hi {booking.customer_name},",
        "",
        f"Your {name} booking {booking.booking_code} for {when} is not going ahead.",
    ]
    if booking.admin_note:
        lines.append(f"Reason: {booking.admin_note}")
    else:
        lines.append(f"We couldn't confirm your bKash payment (TrxID {booking.trx_id}).")
    lines += [
        "",
        f"If you think this is a mistake, please contact us with your TrxID: {contact}",
    ]
    return f"Your {name} booking {booking.booking_code} is not going ahead", "\n".join(lines)


def send_booking_email(booking: Booking) -> bool:
    """Email the customer about a CONFIRMED or REJECTED booking. Never raises.

    Returns True (and stamps email_sent_at) when the email went out.
    """
    if booking.status not in (Booking.CONFIRMED, Booking.REJECTED) or not booking.customer_email:
        return False
    if not mail_configured():
        return False
    subject, body = booking_email(booking, TurfSettings.current_or_default())
    try:
        send_email(booking.customer_email, subject, body)
    except Exception as exc:  # any provider/network failure; never undo the owner's action
        current_app.logger.warning("Booking email for %s failed: %s", booking.booking_code, type(exc).__name__)
        return False
    booking.email_sent_at = utcnow()
    db.session.commit()
    return True
