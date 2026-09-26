"""Top-of-funnel pages: free lead magnet, tripwire checkout, post-purchase
upsell. Kept as its own blueprint (not mixed into `public`) because these
pages have a different job — one action per page, no nav out — and because
this is exactly where GHL webhook calls belong once that integration is
wired in (each TODO below marks the spot).

Payments here are simulated: there's no live Stripe key configured in this
environment, so "purchase" just grants access directly. Swap the body of
each POST handler for a real charge (Stripe Checkout / PaymentIntent) when
this goes live — the funnel structure and DB writes around it don't change.

GHL webhooks ARE wired for real (app/ghl.send_event) at every point the
funnel doc calls for one — they just no-op-and-log until GHL_WEBHOOK_URL is
set as an env var, so this is safe to ship ahead of that being ready.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from ...db import get_db
from ...auth import create_user, get_user_by_email, current_user
from ...models.programs import get_program_by_slug, get_workouts_for_program
from ...models.access import grant_access, user_has_access
from ...models.leads import upsert_lead, mark_lead_converted
from ...models.consultations import get_available_slots, book_consultation
from ...ghl import send_event

# Programs that are a consultative sale, not a self-checkout: signing up
# captures a questionnaire and auto-books a consultation instead of taking a
# card. Add a slug here to route it through /consultation/<slug> instead of
# the generic /signup form.
CONSULTATION_PROGRAM_SLUGS = {"train-with-tia", "virtual-coaching"}

funnel_bp = Blueprint("funnel", __name__)


def _get_or_create_account(email, name):
    """Used by both the free opt-in and the tripwire checkout: find the
    existing account for this email, or create a lightweight one so the
    person has somewhere to log back in later. No password is collected at
    this stage on purpose — every extra field here is funnel friction, so
    checkout only ever asks for name + email. A real deploy should follow up
    with a "set your password" email; skipped here since there's no email
    provider configured yet.
    """
    user = get_user_by_email(email)
    if user:
        return user
    import secrets

    return create_user(email, secrets.token_hex(16), name)


@funnel_bp.route("/free-kickstart", methods=["GET", "POST"])
def kickstart():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if not name or not email or "@" not in email:
            flash("Enter your name and a valid email to unlock the Kickstart.")
            return redirect(url_for("funnel.kickstart"))

        db = get_db()
        upsert_lead(db, email, name, source="kickstart")
        send_event("lead_captured", email, name, source="kickstart")

        user = _get_or_create_account(email, name)
        program = get_program_by_slug(db, "kickstart")
        if program:
            grant_access(db, user["id"], program["id"], source="lead_magnet")
        mark_lead_converted(db, email, user["id"])

        session.clear()
        session["user_id"] = user["id"]
        flash("You're in — your 5-Day Kickstart is unlocked below.")
        return redirect(url_for("funnel.tripwire"))

    return render_template("funnel/kickstart.html")


@funnel_bp.route("/offers/tripwire", methods=["GET", "POST"])
def tripwire():
    db = get_db()
    program = get_program_by_slug(db, "recipe-guide")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        order_bump = request.form.get("order_bump") == "on"
        if not name or not email or "@" not in email:
            flash("Enter your name and a valid email to complete checkout.")
            return redirect(url_for("funnel.tripwire"))

        upsert_lead(db, email, name, source="tripwire")
        user = _get_or_create_account(email, name)
        if program:
            grant_access(db, user["id"], program["id"], source="purchase")
        if order_bump:
            addon = get_program_by_slug(db, "meal-prep-companion")
            if addon:
                grant_access(db, user["id"], addon["id"], source="order_bump")
        mark_lead_converted(db, email, user["id"])
        send_event("tripwire_purchased", email, name, program="recipe-guide", price_cents=2700)
        if order_bump:
            send_event("order_bump_added", email, name, program="meal-prep-companion", price_cents=1000)

        session.clear()
        session["user_id"] = user["id"]
        session["order_bump"] = order_bump
        return redirect(url_for("funnel.fitbox_upsell"))

    prefill_name = request.form.get("name", "")
    u = current_user()
    prefill_email = u["email"] if u else ""
    prefill_name = u["name"] if u else prefill_name
    return render_template(
        "funnel/tripwire.html", program=program,
        prefill_name=prefill_name, prefill_email=prefill_email,
    )


@funnel_bp.route("/consultation/<slug>", methods=["GET", "POST"])
def consultation(slug):
    db = get_db()
    program = get_program_by_slug(db, slug)
    if program is None or slug not in CONSULTATION_PROGRAM_SLUGS:
        return render_template("public/program_not_found.html", slug=slug), 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        goal = request.form.get("goal", "").strip()
        experience_level = request.form.get("experience_level", "")
        slot_iso = request.form.get("slot", "")

        available = {s.isoformat() for s in get_available_slots(db, count=8)}
        if not name or not email or "@" not in email or not phone or not goal or slot_iso not in available:
            flash("Please fill in every field and pick an open time — that slot may have just been taken.")
            return redirect(url_for("funnel.consultation", slug=slug))

        upsert_lead(db, email, name, source="consultation")
        user = _get_or_create_account(email, name)
        mark_lead_converted(db, email, user["id"])
        book_consultation(db, user["id"], program["id"], phone, goal, experience_level, slot_iso)
        send_event(
            "consultation_booked", email, name,
            program=slug, phone=phone, goal=goal, experience_level=experience_level,
            scheduled_at=slot_iso,
        )

        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("funnel.consultation_confirmed", slug=slug))

    slots = get_available_slots(db, count=8)
    u = current_user()
    return render_template(
        "funnel/consultation.html", program=program, slots=slots,
        prefill_name=u["name"] if u else "", prefill_email=u["email"] if u else "",
    )


@funnel_bp.route("/consultation/<slug>/confirmed")
def consultation_confirmed(slug):
    db = get_db()
    program = get_program_by_slug(db, slug)
    u = current_user()
    booking = None
    if u and program:
        from ...models.consultations import get_upcoming_for_user
        for c in get_upcoming_for_user(db, u["id"]):
            if c["program_slug"] == slug:
                booking = c
                break
    return render_template("funnel/consultation_confirmed.html", program=program, booking=booking)


@funnel_bp.route("/checkout/<slug>", methods=["GET", "POST"])
def checkout(slug):
    """Generic self-checkout for every program that isn't a dedicated funnel
    page (free kickstart, tripwire recipes) and isn't a consultation-booked
    program (Train With Tia, Virtual Coaching). Covers FitBox, Resistance
    Bar, Glute Growth, Glute Growth Academy, and Coach Tia+.

    Payment is simulated, same as the tripwire checkout — see the note at
    the top of this file. A membership program (is_membership=1) grants
    access with no expiry here (real recurring billing needs Stripe
    Billing/Subscriptions wired in later; the DB already has an
    expires_at column on product_access ready for that).
    """
    if slug in CONSULTATION_PROGRAM_SLUGS or slug in ("kickstart", "recipe-guide"):
        return redirect(url_for("public.program_detail", slug=slug))

    db = get_db()
    program = get_program_by_slug(db, slug)
    if program is None:
        return render_template("public/program_not_found.html", slug=slug), 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if not name or not email or "@" not in email:
            flash("Enter your name and a valid email to complete checkout.")
            return redirect(url_for("funnel.checkout", slug=slug))

        upsert_lead(db, email, name, source="checkout")
        user = _get_or_create_account(email, name)
        grant_access(db, user["id"], program["id"], source="purchase")
        mark_lead_converted(db, email, user["id"])
        send_event(
            "purchase", email, name,
            program=slug, price_cents=program["price_cents"], recurring=bool(program["is_membership"]),
        )

        session.clear()
        session["user_id"] = user["id"]
        flash(f"You're in — {program['name']} is unlocked below.")
        return redirect(url_for("member.dashboard"))

    u = current_user()
    return render_template(
        "funnel/checkout.html", program=program,
        prefill_name=u["name"] if u else "", prefill_email=u["email"] if u else "",
    )


@funnel_bp.route("/offers/fitbox-upsell")
def fitbox_upsell():
    db = get_db()
    fitbox = get_program_by_slug(db, "fitbox")
    u = current_user()
    already_owns = bool(u and fitbox and user_has_access(db, u["id"], fitbox["id"]))
    return render_template("funnel/fitbox_upsell.html", fitbox=fitbox, already_owns=already_owns)


@funnel_bp.route("/offers/fitbox-upsell/accept", methods=["POST"])
def fitbox_upsell_accept():
    u = current_user()
    if not u:
        return redirect(url_for("funnel.tripwire"))
    db = get_db()
    fitbox = get_program_by_slug(db, "fitbox")
    if fitbox:
        grant_access(db, u["id"], fitbox["id"], source="purchase")
    send_event("upsell_accepted", u["email"], u["name"], program="fitbox", price_cents=14900)
    flash("FitBox is unlocked — welcome in.")
    return redirect(url_for("member.dashboard"))


@funnel_bp.route("/offers/fitbox-upsell/decline")
def fitbox_upsell_decline():
    u = current_user()
    if u:
        send_event("upsell_declined", u["email"], u["name"], program="fitbox")
    return redirect(url_for("member.dashboard"))
