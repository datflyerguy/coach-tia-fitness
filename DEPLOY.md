# Getting Coach Tia Fitness live on Render

This app is ready to deploy as-is. Here's exactly what to do.

## What you'll need to do yourself (about 5 minutes)

1. Go to **render.com** and sign up for a free account (Google sign-in is the fastest way).
2. Once you're in, click **New +** → **Web Service**.
3. Render will ask to connect a code repository (GitHub). If you don't already
   have a GitHub account, create one free at **github.com** — this is where
   the app's code will live so Render can pull it and deploy it.
4. Tell me once you've got both accounts and are logged into Render — from
   there I can push the code up and walk you through the rest of the Render
   dashboard (service name, environment variables) with you.

## What's already done (so this goes fast once you're signed up)

- `requirements.txt` — every package the app needs
- `Procfile` — tells Render how to run the app in production (`gunicorn`,
  not the dev server)
- The database auto-creates itself and loads all 10 programs + a coach
  login the very first time the app boots on a fresh host — no manual setup
  step needed after deploy.

## Environment variables to set in Render's dashboard

| Key | Value | Why |
|---|---|---|
| `SECRET_KEY` | any long random string | keeps login sessions stable across restarts |
| `GHL_WEBHOOK_URL` | (leave blank for now) | set this once your GoHighLevel inbound webhook is ready — every funnel event is already wired to fire here |

## One honest caveat: the database will reset on redeploys

Render's free web service tier doesn't include persistent storage — every
time new code is deployed, it starts from a clean disk, so the database
(SQLite file) resets back to the seeded catalog and any purchases/leads
made in between are lost. For a real go-live, the fix is either:

- Render's paid **Disk** add-on (a few dollars/month, mounted storage that
  survives redeploys), or
- moving to a real hosted database (Postgres) — a bigger but more
  future-proof step, especially once real payments are wired in.

Neither is needed to get you a working, clickable, live link today — just
flagging it so there's no surprise later if a demo purchase seems to
"disappear" after I ship a code update.

## Also still simulated, not yet live

- Payments (no live Stripe key configured anywhere)
- GHL webhook delivery (fires and logs correctly, just needs the real
  webhook URL once your GHL automation is ready)

Both are prepped and easy to flip on for real — they just need accounts/
keys only you can create.
