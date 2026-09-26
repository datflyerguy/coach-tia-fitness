"""Consultation booking for high-ticket, consultative-sale programs (Train
With Tia, Virtual Coaching): no self-checkout, no price charged here — this
is the "capture the lead, get them on Tia's calendar automatically" flow.
There's no real calendar system connected, so slots are generated
deterministically (next weekdays, two fixed times a day) and a slot is
unavailable once booked. Swap this for a real calendar (GHL calendar,
Calendly, etc.) later without changing anything upstream of it.
"""
import datetime

SLOT_TIMES = [(10, 0), (14, 0)]  # 10:00 AM and 2:00 PM, in whatever timezone the server runs in
DAYS_AHEAD = 14


def get_available_slots(db, count=8):
    """Next `count` open weekday slots, skipping anything already booked."""
    taken = {
        row["scheduled_at"]
        for row in db.execute(
            "SELECT scheduled_at FROM consultations WHERE status = 'scheduled'"
        ).fetchall()
    }

    slots = []
    day = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    checked = 0
    while len(slots) < count and checked < DAYS_AHEAD:
        if day.weekday() < 5:  # Mon-Fri
            for hour, minute in SLOT_TIMES:
                dt = datetime.datetime.combine(day, datetime.time(hour, minute))
                iso = dt.isoformat()
                if iso not in taken:
                    slots.append(dt)
        day += datetime.timedelta(days=1)
        checked += 1
    return slots[:count]


def book_consultation(db, user_id, program_id, phone, goal, experience_level, scheduled_at_iso):
    cur = db.execute(
        """INSERT INTO consultations (user_id, program_id, phone, goal, experience_level, scheduled_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, program_id, phone, goal, experience_level, scheduled_at_iso),
    )
    db.commit()
    return cur.lastrowid


def get_upcoming_for_user(db, user_id):
    return db.execute(
        """
        SELECT c.*, p.name AS program_name, p.slug AS program_slug
        FROM consultations c
        JOIN programs p ON p.id = c.program_id
        WHERE c.user_id = ? AND c.status = 'scheduled' AND c.scheduled_at >= datetime('now')
        ORDER BY c.scheduled_at ASC
        """,
        (user_id,),
    ).fetchall()


def list_upcoming(db):
    return db.execute(
        """
        SELECT c.*, u.name AS user_name, u.email AS user_email, p.name AS program_name
        FROM consultations c
        JOIN users u ON u.id = c.user_id
        JOIN programs p ON p.id = c.program_id
        WHERE c.status = 'scheduled'
        ORDER BY c.scheduled_at ASC
        """
    ).fetchall()
