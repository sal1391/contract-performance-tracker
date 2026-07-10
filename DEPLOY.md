# Deploying the Triton demo to Railway

One Railway service (API + UI in a single Docker image) + the Railway Postgres plugin.
On first boot the app creates its schema and seeds a full demo dataset automatically
(`DEMO_SEED=true`), so the deployed URL lands on a populated dashboard.

> ⚠️ **The deployed demo is unauthenticated and world-writable by design** (auth is off so the "Act as" switch works). Anyone with the URL can view, edit, and delete data, including via the open `/admin` UI. Don't put real data in it, treat the database as disposable, and avoid sharing the URL more widely than you need to. For a locked-down deployment, wire up Auth0 (`AUTH0_ENABLED=true`) and gate `/admin` — beyond this demo's scope.

## Steps (~5 minutes)

1. **Create the project** — [railway.app](https://railway.app) → New Project.
2. **Add Postgres** — "Create" → Database → **PostgreSQL**.
3. **Add the app service** — either:
   - **GitHub:** "Create" → GitHub Repo → pick this repo (Railway detects `railway.json`
     and builds the Dockerfile), or
   - **CLI:** `npm i -g @railway/cli`, then from the repo root:
     `railway login`, `railway link` (select the project you created in step 1), `railway up`.
4. **Set the app service variables** (service → Variables):

   | Variable | Value | Notes |
   |---|---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Reference to the plugin. The app rewrites the URL for its psycopg driver automatically. |
   | `DEMO_SEED` | `true` | Auto-seed schema + demo data on first boot. Optional (defaults to true). |

   Set `DEMO_SEED=false` if you repurpose this image for real data (it's a no-op on a non-empty DB, but explicit is clearer).

   `PORT` is injected by Railway; `STATIC_DIR` is baked into the image. Nothing else is needed —
   auth stays off (`AUTH0_ENABLED` defaults to false), which is what enables the demo
   "Act as" user switch.

   > `${{Postgres.DATABASE_URL}}` and `railway connect postgres` (below) assume the plugin service
   > is named **Postgres** (Railway's default from Create → Database → PostgreSQL); if you renamed it,
   > substitute your service's name.
5. **Expose it** — service → Settings → Networking → **Generate Domain**. Open the URL:
   the Dashboard should show populated risk tiles.

## Demo walkthrough

- **Dashboard** — at-risk tiles ($ GP at risk) across every status.
- **Bids** — 6 contracts / 12 bid lines; open one to see computed margin + GP.
- **Mapping** — pick QB-2201 · NAPLES/VLSFO and "Run auto-match" to live-match the
  unmapped `XL-…` lifts; `NM-…` lifts demonstrate near-misses you can map manually.
- **Act as** (top-right) — switch between Ivy (IC, sees Cruise Team only), Theo (NJ office),
  Rosa (NA region), Sam (segment), Lee (leadership, sees all) to demo org-subtree RLS.

## Resetting the demo data

The seeder is idempotent and never overwrites. To reset to a pristine demo:

```
railway connect postgres        # opens psql on the plugin
DROP SCHEMA public CASCADE; CREATE SCHEMA public;
\q
```

then redeploy (or restart) the app service — it reseeds on boot.

## Running the production image locally

```
docker build -t triton-demo .
docker run --rm -p 8080:8080 -e PORT=8080 \
  -e DATABASE_URL="postgresql://app:app@host.docker.internal:5432/contracts" triton-demo
```

Requires the local compose Postgres: `cd backend && docker compose up -d db`.
