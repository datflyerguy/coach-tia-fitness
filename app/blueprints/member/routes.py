from flask import Blueprint, render_template, request, redirect, url_for, flash

from ...db import get_db
from ...auth import login_required, current_user
from ...models.programs import get_program_by_slug, get_workouts_for_program, get_exercises_for_workout
from ...models.access import (
    get_user_programs,
    user_has_access,
    redeem_activation_code,
    get_completed_workout_ids,
    mark_workout_complete,
    get_current_streak,
)
from ...ghl import send_event
from ...models.consultations import get_upcoming_for_user

member_bp = Blueprint("member", __name__)


@member_bp.route("/")
@login_required
def dashboard():
    db = get_db()
    user = current_user()
    programs = get_user_programs(db, user["id"])
    streak = get_current_streak(db, user["id"])
    upcoming_consultations = get_upcoming_for_user(db, user["id"])
    return render_template(
        "member/dashboard.html", programs=programs, streak=streak,
        upcoming_consultations=upcoming_consultations,
    )


@member_bp.route("/activate", methods=["GET", "POST"])
def activate():
    """FitBox / Resistance Bar QR activation. Reachable logged-out (per the
    brief's flow: scan QR -> log in or create account -> enter code), so it
    redirects through login/signup with ?next= back here if needed."""
    user = current_user()
    result = None
    if request.method == "POST":
        if not user:
            return redirect(url_for("public.login", next=url_for("member.activate")))
        db = get_db()
        code = request.form.get("code", "")
        result = redeem_activation_code(db, code, user["id"])
    return render_template("member/activate.html", result=result, user=user)


@member_bp.route("/programs/<slug>")
@login_required
def program_player(slug):
    db = get_db()
    user = current_user()
    program = get_program_by_slug(db, slug)
    if program is None or not user_has_access(db, user["id"], program["id"]):
        return render_template("member/no_access.html", slug=slug), 403

    workouts = get_workouts_for_program(db, program["id"])
    completed_ids = get_completed_workout_ids(db, user["id"], program["id"])

    unlocked_reached = not program["is_sequential"]
    workout_rows = []
    for w in workouts:
        is_done = w["id"] in completed_ids
        is_unlocked = True if not program["is_sequential"] else (unlocked_reached or is_done)
        workout_rows.append({"workout": w, "done": is_done, "unlocked": is_unlocked})
        if program["is_sequential"] and not is_done:
            unlocked_reached = False

    total = len(workouts)
    done_count = len(completed_ids)
    percent = round((done_count / total) * 100) if total else 0

    return render_template(
        "member/program_player.html",
        program=program,
        workout_rows=workout_rows,
        percent=percent,
        done_count=done_count,
        total=total,
    )


@member_bp.route("/workouts/<int:workout_id>/detail")
@login_required
def workout_detail(workout_id):
    db = get_db()
    user = current_user()
    from ...models.programs import get_workout_by_id

    workout = get_workout_by_id(db, workout_id)
    if workout is None:
        return render_template("member/no_access.html", slug=""), 404
    from ...models.programs import get_program_by_id

    program = get_program_by_id(db, workout["program_id"])
    if not user_has_access(db, user["id"], program["id"]):
        return render_template("member/no_access.html", slug=program["slug"]), 403

    exercises = get_exercises_for_workout(db, workout_id)
    completed_ids = get_completed_workout_ids(db, user["id"], program["id"])
    is_done = workout_id in completed_ids
    return render_template(
        "member/workout_detail.html", workout=workout, program=program, exercises=exercises, is_done=is_done
    )


@member_bp.route("/workouts/<int:workout_id>/complete", methods=["POST"])
@login_required
def complete_workout(workout_id):
    db = get_db()
    user = current_user()
    from ...models.programs import get_workout_by_id, get_program_by_id

    workout = get_workout_by_id(db, workout_id)
    program = get_program_by_id(db, workout["program_id"]) if workout else None

    # Snapshot percent-complete BEFORE marking done, so we can tell whether
    # this exact workout is what crossed the 50%/100% threshold — fires the
    # continuity/backend-offer GHL events from the funnel doc exactly once,
    # not on every workout after the threshold.
    before_pct = None
    if program:
        total = len(get_workouts_for_program(db, program["id"]))
        done_before = len(get_completed_workout_ids(db, user["id"], program["id"]))
        before_pct = round((done_before / total) * 100) if total else 0

    mark_workout_complete(db, user["id"], workout_id)

    if program and before_pct is not None:
        total = len(get_workouts_for_program(db, program["id"]))
        done_after = len(get_completed_workout_ids(db, user["id"], program["id"]))
        after_pct = round((done_after / total) * 100) if total else 0
        if before_pct < 50 <= after_pct:
            send_event("program_50_percent", user["email"], user["name"], program=program["slug"])
        if before_pct < 100 <= after_pct:
            send_event("program_100_percent", user["email"], user["name"], program=program["slug"])

    if program:
        return redirect(url_for("member.program_player", slug=program["slug"]))
    return redirect(url_for("member.dashboard"))
