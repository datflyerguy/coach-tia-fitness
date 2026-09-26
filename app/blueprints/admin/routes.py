from flask import Blueprint, render_template, request, redirect, url_for

from ...db import get_db
from ...auth import admin_required
from ...models.programs import get_all_programs, get_program_by_id, get_workouts_for_program, create_program, create_workout
from ...models.access import generate_activation_code
from ...models.leads import get_recovery_segments
from ...models.consultations import list_upcoming

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@admin_required
def dashboard():
    db = get_db()
    programs = get_all_programs(db, active_only=False)
    member_count = db.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'member'").fetchone()["c"]
    workout_count = db.execute("SELECT COUNT(*) AS c FROM workouts").fetchone()["c"]
    recent_members = db.execute(
        "SELECT * FROM users WHERE role = 'member' ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    return render_template(
        "admin/dashboard.html",
        programs=programs,
        member_count=member_count,
        workout_count=workout_count,
        recent_members=recent_members,
    )


@admin_bp.route("/programs/new", methods=["GET", "POST"])
@admin_required
def new_program():
    error = None
    if request.method == "POST":
        db = get_db()
        slug = request.form.get("slug", "").strip().lower()
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        tagline = request.form.get("tagline", "").strip()
        description = request.form.get("description", "").strip()
        is_sequential = 1 if request.form.get("is_sequential") == "on" else 0
        is_membership = 1 if request.form.get("is_membership") == "on" else 0
        price = request.form.get("price_dollars", "").strip()
        price_cents = int(float(price) * 100) if price else None

        if not slug or not name or not category:
            error = "Slug, name, and category are all required."
        else:
            existing = db.execute("SELECT 1 FROM programs WHERE slug = ?", (slug,)).fetchone()
            if existing:
                error = f'A program with the slug "{slug}" already exists.'
            else:
                program_id = create_program(
                    db, slug, name, category, tagline, description, is_sequential, is_membership, price_cents
                )
                return redirect(url_for("admin.program_detail", program_id=program_id))
    return render_template("admin/program_form.html", error=error)


@admin_bp.route("/programs/<int:program_id>")
@admin_required
def program_detail(program_id):
    db = get_db()
    program = get_program_by_id(db, program_id)
    workouts = get_workouts_for_program(db, program_id)
    codes = db.execute(
        "SELECT * FROM activation_codes WHERE program_id = ? ORDER BY created_at DESC", (program_id,)
    ).fetchall()
    return render_template("admin/program_detail.html", program=program, workouts=workouts, codes=codes)


@admin_bp.route("/programs/<int:program_id>/workouts", methods=["POST"])
@admin_required
def add_workout(program_id):
    db = get_db()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    video_url = request.form.get("video_url", "").strip()
    duration = request.form.get("duration_minutes", "").strip()
    duration_minutes = int(duration) if duration else None

    existing = get_workouts_for_program(db, program_id)
    next_order = (max((w["order_index"] for w in existing), default=0)) + 1

    if title:
        create_workout(db, program_id, next_order, title, description, video_url, duration_minutes)
    return redirect(url_for("admin.program_detail", program_id=program_id))


@admin_bp.route("/programs/<int:program_id>/codes", methods=["POST"])
@admin_required
def create_codes(program_id):
    db = get_db()
    count = int(request.form.get("count", "1") or 1)
    batch_note = request.form.get("batch_note", "").strip()
    count = max(1, min(count, 200))
    for _ in range(count):
        generate_activation_code(db, program_id, batch_note)
    return redirect(url_for("admin.program_detail", program_id=program_id))


@admin_bp.route("/members")
@admin_required
def members():
    db = get_db()
    all_members = db.execute(
        "SELECT * FROM users WHERE role = 'member' ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin/members.html", members=all_members)


@admin_bp.route("/recovery")
@admin_required
def recovery():
    db = get_db()
    segments = get_recovery_segments(db)
    return render_template("admin/recovery.html", segments=segments)


@admin_bp.route("/consultations")
@admin_required
def consultations():
    db = get_db()
    upcoming = list_upcoming(db)
    return render_template("admin/consultations.html", upcoming=upcoming)
