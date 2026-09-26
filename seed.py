"""One-off seed script: creates the seven ecosystem programs, a handful of
sample workouts for FitBox, and a coach (admin) login.

Run standalone with: python3 seed.py
Also called automatically by app/__init__.py on first boot (fresh DB, e.g.
a brand-new deploy) — in that case `run()` is called from inside an
app context that already exists, so this module must NOT create its own
app at import time (that would recurse into create_app()).
"""
from app.db import get_db
from app.auth import create_user, get_user_by_email
from app.models.programs import create_program, create_workout

PROGRAMS = [
    ("kickstart", "5-Day Kickstart", "lead_magnet", "Free — no card required.",
     "Five days of Coach Tia's actual warm-up-to-finisher structure, free, so you can feel the difference before you buy anything.", 1, 0, 0),
    ("recipe-guide", "Protein Power Recipes", "tripwire", "Coach Tia's fitness recipes, ready in minutes.",
     "The exact high-protein recipes Coach Tia uses with her own clients — quick, simple, built around real training.", 0, 0, 2700),
    ("meal-prep-companion", "Meal Prep Companion", "addon", "Printable shopping lists & prep schedule.",
     "The order-bump add-on to Protein Power Recipes — shopping lists and a prep schedule for every recipe.", 0, 0, 1000),
    ("fitbox", "Coach Tia FitBox", "fitbox", "Your gym. Your program. Your results.",
     "A complete at-home gym in a box, paired with 20 guided workouts that take you from day one to a real routine.", 1, 0, 24900),
    ("resistance-bar", "Resistance Bar System", "resistance_bar", "Strength training, anywhere.",
     "A four-phase resistance bar progression with 20 guided digital workouts.", 1, 0, 12900),
    ("glute-growth", "Glute Growth", "glute_growth", "A structured glute transformation program.",
     "Progressive glute-focused programming built for visible results.", 1, 0, 9900),
    ("glute-growth-academy", "Glute Growth Academy", "glute_growth_academy", "Premium coaching. Real accountability.",
     "The Academy adds live coaching and accountability check-ins on top of the Glute Growth program.", 1, 1, 19900),
    ("coach-tia-plus", "Coach Tia+", "coach_tia_plus", "Your full training library, every month.",
     "A recurring digital membership: the full workout library plus new drops every month.", 0, 1, 2900),
    ("virtual-coaching", "Virtual Coaching", "virtual_coaching", "High-touch remote coaching.",
     "One-on-one virtual coaching with programming built around your goals.", 0, 1, 29900),
    ("train-with-tia", "Train With Tia", "train_with_tia", "Premium in-person coaching.",
     "Work with Coach Tia in person for fully personalized training.", 0, 0, 39700),
]


def run():
    """Assumes it's called inside an active Flask app context already
    (either by app/__init__.py on first boot, or by __main__ below)."""
    db = get_db()
    for slug, name, category, tagline, description, seq, membership, price in PROGRAMS:
        existing = db.execute("SELECT id FROM programs WHERE slug = ?", (slug,)).fetchone()
        if existing:
            print(f"skip (exists): {slug}")
            continue
        pid = create_program(db, slug, name, category, tagline, description, seq, membership, price)
        print(f"created program: {slug} (id={pid})")
        if slug == "fitbox":
            for i in range(1, 21):
                create_workout(
                    db, pid, i, f"Workout {i:02d}",
                    description="Full-body FitBox session.",
                    video_url="", duration_minutes=30,
                )
            print("  + 20 FitBox workouts")
        if slug == "kickstart":
            titles = [
                "Day 1 — Warm-Up & Movement Foundations",
                "Day 2 — Full-Body Strength Basics",
                "Day 3 — Core & Conditioning",
                "Day 4 — Mobility & Recovery",
                "Day 5 — Putting It Together",
            ]
            for i, title in enumerate(titles, start=1):
                create_workout(
                    db, pid, i, title,
                    description="Free preview day from Coach Tia's 5-Day Kickstart.",
                    video_url="", duration_minutes=20,
                )
            print("  + 5 Kickstart days")

    if not get_user_by_email("coach@coachtiafitness.com"):
        create_user("coach@coachtiafitness.com", "changeme123", "Coach Tia", role="admin")
        print("created admin login: coach@coachtiafitness.com / changeme123  <-- CHANGE THIS PASSWORD")
    else:
        print("admin login already exists")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run()
