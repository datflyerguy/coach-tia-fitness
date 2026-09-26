"""Data access for programs, workouts and the reusable exercise library.
Deliberately plain functions over sqlite3 rows (no ORM available in this
environment) — but the shape mirrors what a Prisma/SQLAlchemy model layer
would look like, so porting later is mechanical, not a redesign.
"""
def get_all_programs(db, active_only=True):
    q = "SELECT * FROM programs"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY category, name"
    return db.execute(q).fetchall()


def get_program_by_slug(db, slug):
    return db.execute("SELECT * FROM programs WHERE slug = ?", (slug,)).fetchone()


def get_program_by_id(db, program_id):
    return db.execute("SELECT * FROM programs WHERE id = ?", (program_id,)).fetchone()


def get_workouts_for_program(db, program_id):
    return db.execute(
        "SELECT * FROM workouts WHERE program_id = ? ORDER BY order_index", (program_id,)
    ).fetchall()


def get_workout_by_id(db, workout_id):
    return db.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()


def get_exercises_for_workout(db, workout_id):
    return db.execute(
        """
        SELECT e.*, we.sets, we.reps, we.notes, we.order_index AS we_order
        FROM workout_exercises we
        JOIN exercises e ON e.id = we.exercise_id
        WHERE we.workout_id = ?
        ORDER BY we.order_index
        """,
        (workout_id,),
    ).fetchall()


def create_program(db, slug, name, category, tagline="", description="", is_sequential=1, is_membership=0, price_cents=None):
    cur = db.execute(
        """INSERT INTO programs (slug, name, category, tagline, description, is_sequential, is_membership, price_cents)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, name, category, tagline, description, is_sequential, is_membership, price_cents),
    )
    db.commit()
    return cur.lastrowid


def create_workout(db, program_id, order_index, title, description="", video_url="", duration_minutes=None):
    cur = db.execute(
        """INSERT INTO workouts (program_id, order_index, title, description, video_url, duration_minutes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (program_id, order_index, title, description, video_url, duration_minutes),
    )
    db.commit()
    return cur.lastrowid
