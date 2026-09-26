"""
Auth shared by the web app (session cookie) and the API (JWT bearer token),
so the same user accounts and role checks work for both. This is the piece
that lets a future native iOS/Android app reuse this exact backend: it logs
in against /api/v1/auth/login, gets a JWT, and calls the same /api/v1/*
endpoints the web member-app JS uses.
"""
import hashlib
import hmac
import os
import time
from functools import wraps

import jwt
from flask import session, request, g, jsonify, redirect, url_for, current_app

from .db import get_db


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return digest.hex(), salt.hex()


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    salt = bytes.fromhex(password_salt)
    digest, _ = hash_password(password, salt)
    return hmac.compare_digest(digest, password_hash)


def create_user(email: str, password: str, name: str, role: str = "member"):
    db = get_db()
    password_hash, salt = hash_password(password)
    cur = db.execute(
        "INSERT INTO users (email, password_hash, password_salt, name, role) VALUES (?, ?, ?, ?, ?)",
        (email.strip().lower(), password_hash, salt, name.strip(), role),
    )
    db.commit()
    return get_user_by_id(cur.lastrowid)


def get_user_by_email(email: str):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()


def get_user_by_id(user_id: int):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def issue_jwt(user) -> str:
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "iat": int(time.time()),
        "exp": int(time.time()) + current_app.config["JWT_EXPIRES_SECONDS"],
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm=current_app.config["JWT_ALGORITHM"])


def decode_jwt(token: str):
    return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=[current_app.config["JWT_ALGORITHM"]])


def current_user():
    """Resolves the logged-in user from either a browser session cookie
    (web app) or an Authorization: Bearer <jwt> header (API/native app)."""
    if getattr(g, "_current_user_cache", "unset") != "unset":
        return g._current_user_cache

    user = None
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
    else:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]
            try:
                payload = decode_jwt(token)
                user = get_user_by_id(int(payload["sub"]))
            except jwt.PyJWTError:
                user = None

    g._current_user_cache = user
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("public.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("public.login", next=request.path))
        if user["role"] != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "forbidden"}), 403
            return redirect(url_for("member.dashboard"))
        return view(*args, **kwargs)

    return wrapped
