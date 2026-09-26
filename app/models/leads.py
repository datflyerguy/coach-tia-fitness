def upsert_lead(db, email, name, source="kickstart"):
    email = email.strip().lower()
    existing = db.execute("SELECT id FROM leads WHERE email = ?", (email,)).fetchone()
    if existing:
        db.execute("UPDATE leads SET name = ?, source = ? WHERE id = ?", (name, source, existing["id"]))
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO leads (email, name, source) VALUES (?, ?, ?)",
        (email, name, source),
    )
    db.commit()
    return cur.lastrowid


def mark_lead_converted(db, email, user_id):
    db.execute(
        "UPDATE leads SET converted_user_id = ? WHERE email = ?",
        (user_id, email.strip().lower()),
    )
    db.commit()


def get_lead_by_email(db, email):
    return db.execute("SELECT * FROM leads WHERE email = ?", (email.strip().lower(),)).fetchone()


def get_recovery_segments(db):
    """Two funnel drop-off segments, computed straight from leads +
    product_access (no separate "abandoned cart" tracking table needed):

    - opted_in_no_purchase: captured a free lead magnet, never bought the
      tripwire. This is exactly the "lead nurture -> tripwire" GHL sequence
      from the funnel doc.
    - bought_no_upgrade: bought the tripwire, never took the FitBox upsell.
      This is the "FitBox nurture" GHL sequence.

    Until GHL is wired in, this is the manual work-list a coach can act on
    directly (call, text, or hand-copy into an email tool).
    """
    opted_in_no_purchase = db.execute(
        """
        SELECT l.email, l.name, l.created_at
        FROM leads l
        WHERE l.converted_user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM product_access pa
              JOIN programs p ON p.id = pa.program_id
              WHERE pa.user_id = l.converted_user_id AND p.slug = 'recipe-guide'
          )
        ORDER BY l.created_at DESC
        """
    ).fetchall()

    bought_no_upgrade = db.execute(
        """
        SELECT u.email, u.name, u.created_at
        FROM users u
        JOIN product_access pa_bought ON pa_bought.user_id = u.id
        JOIN programs p_bought ON p_bought.id = pa_bought.program_id AND p_bought.slug = 'recipe-guide'
        WHERE NOT EXISTS (
            SELECT 1 FROM product_access pa_fb
            JOIN programs p_fb ON p_fb.id = pa_fb.program_id
            WHERE pa_fb.user_id = u.id AND p_fb.slug = 'fitbox'
        )
        ORDER BY u.created_at DESC
        """
    ).fetchall()

    return {"opted_in_no_purchase": opted_in_no_purchase, "bought_no_upgrade": bought_no_upgrade}
