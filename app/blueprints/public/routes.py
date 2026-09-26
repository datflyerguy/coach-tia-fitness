from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from ...db import get_db
from ...auth import create_user, get_user_by_email, verify_password, current_user
from ...models.programs import get_all_programs, get_program_by_slug, get_workouts_for_program

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    db = get_db()
    featured = get_all_programs(db)
    return render_template("public/home.html", featured=featured)


@public_bp.route("/programs")
def programs():
    db = get_db()
    all_programs = get_all_programs(db)
    return render_template("public/programs.html", programs=all_programs)


@public_bp.route("/programs/<slug>")
def program_detail(slug):
    db = get_db()
    program = get_program_by_slug(db, slug)
    if program is None:
        return render_template("public/program_not_found.html", slug=slug), 404
    workouts = get_workouts_for_program(db, program["id"])

    # Where the CTA button on this page actually goes — every program falls
    # into exactly one funnel path. Computed here, once, rather than
    # duplicated as template conditionals.
    if slug in ("train-with-tia", "virtual-coaching"):
        cta_label, cta_url = "Book a Consultation", url_for("funnel.consultation", slug=slug)
    elif slug == "kickstart":
        cta_label, cta_url = "Get It Free", url_for("funnel.kickstart")
    elif slug == "recipe-guide":
        cta_label, cta_url = "Buy Now — $27", url_for("funnel.tripwire")
    else:
        cta_label, cta_url = "Get Started", url_for("funnel.checkout", slug=slug)

    return render_template(
        "public/program_detail.html", program=program, workouts=workouts,
        cta_label=cta_label, cta_url=cta_url,
    )


@public_bp.route("/membership")
def membership():
    return render_template("public/membership.html")


@public_bp.route("/results")
def results():
    return render_template("public/results.html")


@public_bp.route("/shop")
def shop():
    return render_template("public/shop.html")


@public_bp.route("/about")
def about():
    return render_template("public/about.html")


@public_bp.route("/login", methods=["GET", "POST"])
def login():
    u = current_user()
    if u:
        return redirect(url_for("admin.dashboard") if u["role"] == "admin" else url_for("member.dashboard"))

    error = None
    if request.method == "POST":
        db = get_db()
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user and verify_password(password, user["password_hash"], user["password_salt"]):
            session.clear()
            session["user_id"] = user["id"]
            default_url = url_for("admin.dashboard") if user["role"] == "admin" else url_for("member.dashboard")
            next_url = request.args.get("next") or default_url
            return redirect(next_url)
        error = "That email and password don't match an account."
    return render_template("public/login.html", error=error)


@public_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user():
        return redirect(url_for("member.dashboard"))

    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            error = "Please enter your name, a valid email, and a password of at least 8 characters."
        else:
            db = get_db()
            if get_user_by_email(email):
                error = "An account with that email already exists — try logging in instead."
            else:
                user = create_user(email, password, name)
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("member.dashboard"))
    return render_template("public/signup.html", error=error)


@public_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("public.home"))
