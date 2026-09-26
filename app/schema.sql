-- Coach Tia Fitness — core schema
-- SQLite. Kept deliberately close to a normal relational model so a later
-- migration to Postgres (via SQLAlchemy/Prisma) is a straight port, not a
-- redesign.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    password_salt   TEXT NOT NULL,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'admin')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The catalog of purchasable/ownable products. FitBox, Resistance Bar,
-- Glute Growth, Glute Growth Academy, Coach Tia+, Virtual Coaching,
-- Train with Tia all live here as rows, not hardcoded pages.
CREATE TABLE IF NOT EXISTS programs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL, -- fitbox | resistance_bar | glute_growth | glute_growth_academy | coach_tia_plus | virtual_coaching | train_with_tia
    tagline         TEXT,
    description     TEXT,
    is_sequential   INTEGER NOT NULL DEFAULT 1, -- 1 = workouts unlock in order
    is_membership   INTEGER NOT NULL DEFAULT 0, -- 1 = recurring access (e.g. Coach Tia+)
    price_cents     INTEGER,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workouts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id      INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    order_index     INTEGER NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    video_url       TEXT,
    duration_minutes INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(program_id, order_index)
);

-- Reusable exercise library, independent of any one workout, per the
-- "reusable exercise library" requirement in the brief.
CREATE TABLE IF NOT EXISTS exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT,
    video_url       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workout_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id      INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id     INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    order_index     INTEGER NOT NULL DEFAULT 0,
    sets            INTEGER,
    reps            TEXT, -- text so it can hold "12" or "30 sec" or "AMRAP"
    notes           TEXT
);

-- Who owns access to what. A user can own multiple programs at once; the
-- member dashboard is a query over this table, never hardcoded per-user.
CREATE TABLE IF NOT EXISTS product_access (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_id      INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    source          TEXT NOT NULL DEFAULT 'admin_grant', -- activation_code | purchase | admin_grant
    granted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT, -- null = lifetime/no expiry; used for memberships later
    UNIQUE(user_id, program_id)
);

-- FitBox / Resistance Bar physical-product activation codes.
CREATE TABLE IF NOT EXISTS activation_codes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    program_id      INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    is_redeemed     INTEGER NOT NULL DEFAULT 0,
    redeemed_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    redeemed_at     TEXT,
    batch_note      TEXT, -- e.g. "Sept 2026 print run"
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Per-workout completion, which is what progress %, streaks and sequential
-- unlocking are all computed from.
CREATE TABLE IF NOT EXISTS workout_completions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workout_id      INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    completed_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, workout_id)
);

CREATE INDEX IF NOT EXISTS idx_workouts_program ON workouts(program_id, order_index);
CREATE INDEX IF NOT EXISTS idx_product_access_user ON product_access(user_id);
CREATE INDEX IF NOT EXISTS idx_completions_user ON workout_completions(user_id);

-- Top-of-funnel email capture. A lead is not a user account — it's the
-- record of someone who opted in for a free lead magnet before ever
-- creating a login. GHL webhook calls fire from wherever a lead row is
-- inserted or updated (see app/blueprints/public/routes.py).
CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    name            TEXT,
    source          TEXT NOT NULL DEFAULT 'kickstart', -- kickstart | tripwire | other
    converted_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

-- High-ticket programs (Train With Tia, Virtual Coaching) don't self-checkout
-- — signing up captures a questionnaire and auto-books a consultation slot
-- instead. Tia closes the actual sale on the call; this table is her
-- calendar + the lead context she needs going into it.
CREATE TABLE IF NOT EXISTS consultations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_id      INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    phone           TEXT,
    goal            TEXT,
    experience_level TEXT,
    scheduled_at    TEXT NOT NULL, -- ISO datetime of the booked slot
    status          TEXT NOT NULL DEFAULT 'scheduled', -- scheduled | completed | canceled
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_consultations_scheduled ON consultations(scheduled_at);
