"""GHL (GoHighLevel) webhook dispatch.

Every place the funnel strategy doc calls for an automation trigger fires
one call to send_event() from right there in the route — see the callers
in app/blueprints/funnel/routes.py and app/blueprints/member/routes.py.

This never raises into the caller: a webhook failure (or no URL configured
yet) should never break the user-facing request it's attached to. With no
GHL_WEBHOOK_URL set, events are logged instead of sent, so this is safe to
call from day one and "goes live" the moment a real webhook URL is set —
no code changes needed at that point.
"""
import requests
from flask import current_app


def send_event(event, email, name=None, **extra):
    """Fire a funnel/behavior event at GHL.

    event: short event name, e.g. "lead_captured", "tripwire_purchased",
           "order_bump_added", "upsell_accepted", "upsell_declined",
           "program_50_percent", "program_100_percent".
    email/name: identifies the contact so GHL can match/create it.
    **extra: anything else worth passing (program slug, price, etc).
    """
    payload = {"event": event, "email": email, "name": name, **extra}
    url = current_app.config.get("GHL_WEBHOOK_URL")

    if not url:
        current_app.logger.info("[GHL webhook not configured, would send] %s", payload)
        return False

    try:
        requests.post(url, json=payload, timeout=3)
        current_app.logger.info("[GHL webhook sent] %s", payload)
        return True
    except requests.RequestException as exc:
        current_app.logger.warning("[GHL webhook FAILED: %s] %s", exc, payload)
        return False
