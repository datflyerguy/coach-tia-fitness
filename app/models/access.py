"""Product access, activation codes, and progress — the part of the data
model that makes the member dashboard dynamic instead of hardcoded per user.
"""
import secrets
import string


def get_user_programs(db, user_id):
    """Every program this user currently owns, with live progress stats."""
    programs = db.execute(
        """
        SELECT p.*, pa.granted_at, pa.source
        FROM product_access pa
        JOIN programs p ON p.id = pa.program_id
        WHERE pa.user_id = ?
        ORDER BY pa.granted_at DESC
        """,
        (user_id,),
    ).fetchall()

    result = []
    for p in programs:
        total = db.execute(
            "SELECT COUNT(*) AS c FROM workouts WHERE program_id = ?", (p["id"],)
        ).fetchone()["c"]
        done = db.execute(
            """
            SELECT COUNT(*) AS c FROM workout_completions wc
            JOIN workouts w ON w.id = wc.workout_id
            WHERE wc.user_id = ? AND w.program_id = ?
            """,
            (user_id, p["id"]),
        ).fetchone()["c"]
        pct = round((done / total) * 100) if total else 0
        d = dict(p)
        d["total_workouts"] = total
        d["completed_workouts"] = done
        d["percent_complete"] = pct
        result.append(d)
    return result


def user_has_access(db, user_id, program_id):
    row = db.execute(
        "SELECT 1 FROM product_access WHERE user_id = ? AND program_id = ?",
        (user_id, program_id),
    ).fetchone()
    return row is not None


def grant_access(db, user_id, program_id, source="admin_grant"):
    db.execute(
        """INSERT OR IGNORE INTO product_access (user_id, program_id, source)
           VALUES (?, ?, ?)""",
        (user_id, program_id, source),
    )
    db.commit()


def generate_activation_code(db, program_id, batch_note=""):
    alphabet = string.ascii_uppercase + string.digits
    # Human-friendly, hard-to-mistype code: XXXX-XXXX-XXXX
    while True:
        raw = "".join(secrets.choice(alphabet) for _ in range(12))
        code = f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"
        exists = db.execute("SELECT 1 FROM activation_codes WHERE code = ?", (code,)).fetchone()
        if not exists:
            break
    db.execute(
        "INSERT INTO activation_codes (code, program_id, batch_note) VALUES (?, ?, ?)",
        (code, program_id, batch_note),
    )
    db.commit()
    return code


def redeem_activation_code(db, code, user_id):
    row = db.execute(
        "SELECT * FROM activation_codes WHERE code = ?", (code.strip().upper(),)
    ).fetchone()
    if row is None:
        return {"ok": False, "error": "That activation code wasn't found. Double-check it and try again."}
    if row["is_redeemed"]:
        return {"ok": False, "error": "That activation code has already been used."}

    db.execute(
        "UPDATE activation_codes SET is_redeemed = 1, redeemed_by = ?, redeemed_at = datetime('now') WHERE id = ?",
        (user_id, row["id"]),
    )
    grant_access(db, user_id, row["program_id"], source="activation_code")
    db.commit()
    program = db.execute("SELECT * FROM programs WHERE id = ?", (row["program_id"],)).fetchone()
    return {"ok": True, "program": program}


def get_completed_workout_ids(db, user_id, program_id):
    rows = db.execute(
        """
        SELECT wc.workout_id FROM workout_completions wc
        JOIN workouts w ON w.id = wc.workout_id
        WHERE wc.user_id = ? AND w.program_id = ?
        """,
        (user_id, program_id),
    ).fetchall()
    return {r["workout_id"] for r in rows}


def mark_workout_complete(db, user_id, workout_id):
    db.execute(
        "INSERT OR IGNORE INTO workout_completions (user_id, workout_id) VALUES (?, ?)",
        (user_id, workout_id),
    )
    db.commit()


def get_current_streak(db, user_id):
    """Consecutive-day streak, counting any day with at least one completion."""
    rows = db.execute(
        """
        SELECT DISTINCT date(completed_at) AS d
        FROM workout_completions
        WHERE user_id = ?
        ORDER BY d DESC
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return 0

    import datetime

    dates = [datetime.date.fromisoformat(r["d"]) for r in rows]
    # SQLite's datetime('now') is UTC, so "today" for streak purposes must
    # be computed in UTC too, not local server time (they can disagree by a
    # day right around midnight in either direction).
    today = datetime.datetime.utcnow().date()
    streak = 0
    cursor = today
    date_set = set(dates)
    # Streak counts today-or-yesterday as the anchor so a rest day this
    # morning doesn't zero out yesterday's momentum.
    if cursor not in date_set:
        cursor = cursor - datetime.timedelta(days=1)
        if cursor not in date_set:
            return 0
    while cursor in date_set:
        streak += 1
        cursor -= datetime.timedelta(days=1)
    return streak
