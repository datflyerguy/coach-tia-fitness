import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
# Overridable so a host with a persistent disk (e.g. Render's paid Disk
# add-on, mounted at /var/data) can point the DB there instead of the
# app's own ephemeral container filesystem, which resets on every deploy.
DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(INSTANCE_DIR, "coach_tia.sqlite3")

# In production, set SECRET_KEY and JWT_SECRET as real environment variables.
# Falling back to a per-process random secret in dev so sessions still work,
# but this means sessions/tokens won't survive a restart until real secrets
# are configured on whatever host this gets deployed to.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
JWT_SECRET = os.environ.get("JWT_SECRET") or SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_SECONDS = 60 * 60 * 24 * 30  # 30 days, for native-app-style long-lived sessions

BRAND_NAME = "Coach Tia Fitness"

# GHL (GoHighLevel) inbound webhook URL. Every funnel/behavior event in this
# app (lead captured, tripwire purchased, upsell accepted/declined, program
# 50%/100% complete) POSTs a small JSON payload here — that's the hook point
# for the email/SMS sequences from the funnel strategy doc. Leave unset in
# dev: events are logged instead of sent, so nothing breaks with no URL
# configured. Set the real GHL "Inbound Webhook" URL as an env var once
# that's ready.
GHL_WEBHOOK_URL = os.environ.get("GHL_WEBHOOK_URL", "")
