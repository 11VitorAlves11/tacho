# README screenshots

The README images are real Chromium captures of the application with synthetic household
records and original demonstration recipe text. No personal recipes or photographs are
included. Recipes use the application's built-in image placeholder.

Desktop captures use 1440 × 1000; mobile captures use 390 × 844 with touch and mobile
emulation. The interface is European Portuguese. Images are saved without editing in
`docs/images/`.

## Use a disposable installation

The capture script **creates an account, recipes, pantry items, a weekly meal plan and a
shopping list**. It refuses to run if initial account setup has already been completed.
Always point it at a fresh, isolated installation; never reset a household database to
refresh documentation.

For example, from the repository root, start a separate Compose project and web port:

```bash
TACHO_PORT=18080 docker compose --env-file .env.example -p tacho-readme up -d --wait
```

This uses separate named volumes and the published image selected by `TACHO_VERSION`.
To capture unpublished interface changes, build the current checkout and use that image
in the disposable stack instead. The README captures were made with the current frontend
production build and backend source, against a fresh database.

## Capture

Install screenshot tooling outside the project so the app's dependencies stay unchanged:

```bash
npm install --prefix /tmp/tacho-readme-tools @playwright/test@1.62.1
/tmp/tacho-readme-tools/node_modules/.bin/playwright install --with-deps chromium
PLAYWRIGHT_MODULE=/tmp/tacho-readme-tools/node_modules/@playwright/test \
  SCREENSHOT_BASE_URL=http://localhost:18080 \
  node scripts/readme-screenshots.cjs
```

The script uses the known credentials `demo@example.com` / `TachoDemo2026!` only in this
disposable instance. It seeds the current week, captures the home screen and weekly plan,
then the mobile recipe list, shopping list, cooking mode and dark home screen.

If the host lacks browser libraries, run the script in
`mcr.microsoft.com/playwright:v1.62.1-noble`. Mount the repository at `/work` and the tooling's
`node_modules` at `/tooling/node_modules`, join the disposable stack's Docker network,
and set `PLAYWRIGHT_MODULE=/tooling/node_modules/@playwright/test` and
`SCREENSHOT_BASE_URL=http://web:8000`.

Review all six images before committing: loaded data, readable text, correct themes and no
personal information. The script also reports browser exceptions and server errors.

## Clean up

If you created the example `tacho-readme` project above, remove only that disposable stack
and its demo volumes when finished:

```bash
docker compose --env-file .env.example -p tacho-readme down -v
```

A subsequent capture requires another fresh disposable database. Never use the cleanup
command with your normal installation's project name.
