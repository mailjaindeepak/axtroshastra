# Loop Breaker

Personal self-improvement tracker for four parallel tracks (SQL, AI/ML, DSA, Gym),
styled as an anime/RPG character sheet.

## Status

Static Home/Profile page built for visual-direction approval. Backend
(Node/Express + SQLite + Anthropic critic route) and the remaining pages
(Episodes, Log Today, Tracker pages) are not built yet — pending go-ahead.

## Structure

- `client/` — React + Vite + TypeScript, Tailwind v4, Framer Motion,
  react-router-dom. Fonts: Cinzel/Marcellus (display), Inter (body),
  JetBrains Mono (stat numbers/dates).
- `server/` — not yet scaffolded. Will hold the Express API, SQLite
  persistence, and the `/api/critic` Anthropic route (key loaded from
  `.env`, never exposed client-side).

## Client dev

```bash
cd client
npm install
npm run dev
```

## Swapping cover art

Drop images into `client/public/portrait/`:
- `home.jpg` — Home page portrait
- `episodes.jpg` — Episodes page portrait (once that page is built)

Until a file exists, a placeholder gradient with the character's initial is shown.
