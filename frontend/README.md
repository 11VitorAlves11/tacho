# Tacho frontend

React and TypeScript client for Tacho. Vite provides the development server
and production build; the production assets are served by the FastAPI image.

From this directory:

```bash
npm ci
npm run dev
npm run lint
npm test
npm run build
```

`VITE_API_URL` selects the API during development. Production builds use the
same origin as the backend. Repository-wide setup and conventions are in
[`docs/development.md`](../docs/development.md).
