"""JSON REST API — the same backend the web member-app could call, and the
one a future native iOS/Android app would call too, against the same user
accounts and data. Kept intentionally separate from the server-rendered
blueprints above: nothing here depends on HTML templates."""
from flask import Blueprint, request, jsonify

from ...db import get_db
from ...auth import (
    create_user,
    get_user_by_email,
    verify_password,
    issue_jwt,
    current_user,
    login_required,
)
from ...models.programs import get_all_programs, get_program_by_id
from ...models.access import (
    get_user_programs,
    redeem_activation_code,
    mark_workout_complete,
    get_current_streak,
    get_completed_workout_ids,
)

api_bp = Blueprint("api", __name__)


def _user_json(user):
    return {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}


@api_bp.route("/auth/signup", methods=["POST"])
def api_signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not name or not email or len(password) < 8:
        return jsonify({"error": "name, email, and a password of at least 8 characters are required"}), 400
    db = get_db()
    if get_user_by_email(email):
        return jsonify({"error": "an account with that email already exists"}), 409
    user = create_user(email, password, name)
    return jsonify({"token": issue_jwt(user), "user": _user_json(user)}), 201


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"], user["password_salt"]):
        return jsonify({"error": "invalid email or password"}), 401
    return jsonify({"token": issue_jwt(user), "user": _user_json(user)})


@api_bp.route("/me")
@login_required
def api_me():
    user = current_user()
    db = get_db()
    return jsonify(
        {
            "user": _user_json(user),
            "streak": get_current_streak(db, user["id"]),
            "programs": get_user_programs(db, user["id"]),
        }
    )


@api_bp.route("/programs")
def api_programs():
    db = get_db()
    programs = [dict(p) for p in get_all_programs(db)]
    return jsonify({"programs": programs})


@api_bp.route("/activate", methods=["POST"])
@login_required
def api_activate():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return jsonify({"error": "code is required"}), 400
    db = get_db()
    user = current_user()
    result = redeem_activation_code(db, code, user["id"])
    if not result["ok"]:
        return jsonify({"error": result["error"]}), 400
    return jsonify({"ok": True, "program": dict(result["program"])})


@api_bp.route("/workouts/<int:workout_id>/complete", methods=["POST"])
@login_required
def api_complete_workout(workout_id):
    db = get_db()
    user = current_user()
    mark_workout_complete(db, user["id"], workout_id)
    return jsonify({"ok": True})
