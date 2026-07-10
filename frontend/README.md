# Fuel Contract Tracker — Frontend (React 19 + Vite + MUI)

## Run
```bash
cd frontend
cp .env.example .env        # leave AUTH0 blank to run without login in dev
npm install
npm run dev                 # http://localhost:5173  (proxies /api -> :8000)
```
Start the backend (`uvicorn app.main:app --reload`) so `/api` resolves.

## Pages
- **Dashboard** — at-risk tiles + $ GP at risk (`/api/dashboard/summary`).
- **Workbench** — bid-line grid + search (`/api/bid-lines`).
- **Mapping** — LIFT→contract grid with confirm / unmap (`/api/mappings/...`).

## Stack
React 19 · Vite · TypeScript · MUI + MUI X Data Grid · TanStack Query · @auth0/auth0-react ·
axios. `src/api.ts` attaches the Auth0 token when configured; otherwise runs open against the
backend's dev user.
