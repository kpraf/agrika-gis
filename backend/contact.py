"""
Public contact-form endpoint.

POST /api/contact stores an inquiry in contact_messages (always) and, when a
Resend API key is configured, also emails a notification to CONTACT_TO_EMAIL.
No auth: this backs the public Contact page. Email failures never fail the
request, since the message is already saved for an admin to read.
"""
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from extensions import db

contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")

# Field -> (required?, max length). Keeps the row sane and blunts abuse.
FIELDS = {
    "full_name": (True, 150),
    "organization": (False, 150),
    "phone": (True, 50),
    "subject": (True, 150),
    "message": (True, 4000),
}


def _clean(payload, key):
    raw = payload.get(key)
    if raw is None:
        # accept the frontend's camelCase too (fullName)
        alt = {"full_name": "fullName"}.get(key)
        raw = payload.get(alt) if alt else None
    return str(raw or "").strip()


def _send_email(row):
    """Best-effort Resend notification. Returns True if an email was sent."""
    key = current_app.config.get("RESEND_API_KEY")
    to = current_app.config.get("CONTACT_TO_EMAIL")
    if not key or not to:
        return False
    try:
        import resend
    except ImportError:
        current_app.logger.warning("resend package not installed; skipping contact email")
        return False

    resend.api_key = key
    body = {
        "from": current_app.config.get("CONTACT_FROM_EMAIL") or "onboarding@resend.dev",
        "to": [to],
        "subject": f"[AgriKA-GIS] Contact: {row['subject']}",
        "text": (
            f"New contact inquiry from AgriKA-GIS.\n\n"
            f"Name: {row['full_name']}\n"
            f"Organization: {row['organization'] or '(none)'}\n"
            f"Phone: {row['phone']}\n"
            f"Subject: {row['subject']}\n\n"
            f"Message:\n{row['message']}\n"
        ),
    }
    try:
        response = resend.Emails.send(body)
        current_app.logger.info("Resend email sent: %s", response)
        return True
    except Exception as exc:  # network/API error - message is already saved
        current_app.logger.warning("Resend email failed: %s", exc)
        return False


@contact_bp.post("")
def submit():
    payload = request.get_json(silent=True) or {}
    row, errors = {}, []
    for field, (required, maxlen) in FIELDS.items():
        val = _clean(payload, field)
        if required and not val:
            errors.append(field)
        row[field] = val[:maxlen]
    if errors:
        return jsonify({"error": "Please fill in all required fields.", "fields": errors}), 400

    db.session.execute(
        text(
            "INSERT INTO contact_messages (full_name, organization, phone, subject, message) "
            "VALUES (:full_name, :organization, :phone, :subject, :message)"
        ),
        row,
    )
    db.session.commit()

    emailed = _send_email(row)
    return jsonify({"ok": True, "emailed": emailed})
