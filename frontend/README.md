# ContractIQ Frontend (SRS FR-8)

Next.js + Tailwind dashboard for ContractIQ. Implements the six required views:
Upload, Summary, Clause Table, Risk Details, Chat, and Report Export.

## Run

```bash
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE at the backend
npm run dev                        # http://localhost:3000
```

The backend (FastAPI) must be running on the URL in `NEXT_PUBLIC_API_BASE`
(default `http://localhost:8000`). Requests go through Next.js rewrites at
`/api/*` to avoid CORS in the browser.

## Styling note

For zero-config local development, Tailwind is loaded from its CDN in
`app/layout.tsx`. For a production build, install the Tailwind PostCSS plugin
(`npm i -D tailwindcss @tailwindcss/postcss postcss`) and remove the CDN
`<Script>` so styles are compiled and tree-shaken.
