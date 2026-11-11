# Backup and restore

A complete backup contains PostgreSQL, uploaded images and the generated
secrets. `scripts/backup.sh` creates a timestamped directory under `backups/`.

```bash
./scripts/backup.sh
```

Copy backups away from the Docker host and protect them: the database contains
account information and the secrets archive can unlock it.

## Restore

Restoring replaces the current database and images. Stop normal application
traffic first and choose an explicit backup directory:

```bash
docker compose stop web worker
./scripts/restore.sh backups/2026-08-25T120000Z
docker compose up -d --wait
```

Test restore procedures on a disposable installation. A backup that has never
been restored is not yet a verified backup.


## Recipe export and import

The **Export** button on the home page (`GET /recipes/export`) downloads the
household's recipes as versioned JSON: `{"format": "tacho.recipe-export",
"version": 1, "recipes": [...]}`. It is a functional export for moving recipes
between installations or workspaces, not a backup: it carries no accounts,
pantry, meal plans, shopping list or photographs.

**Import** (`POST /recipes/import-file`, JSON body, at most 500 recipes per
file) reads that document back into the current workspace:

- Imported per recipe: title, description, servings, times, source URL, notes,
  nutrition, estimated cost, rating, ingredients (including section headers)
  and steps (including durations). Categories and tags are matched by name
  (ignoring case, accents and extra spaces) within the workspace and created
  when missing.
- Not imported: photographs (image files are not inside the JSON; the response
  reports how many imported recipes had them), favourites (per user),
  comments, cook history and cook notes, share links, ids and the "copied from"
  link. Cookbooks are not part of the export.
- A recipe is a **duplicate** when the workspace already has one with the same
  normalised title and either the same source URL or the same set of
  ingredient names. Duplicates are skipped by default; `?mode=duplicate`
  imports them anyway as new recipes. Recipes repeated inside the same file
  are imported once in either mode. Recipes in other workspaces are never
  compared.
- A malformed recipe entry (for example a missing title or an out-of-range
  value) is reported as skipped with reason `invalid` and does not stop the
  rest of the file. The whole file is written in one transaction, so an
  unexpected error saves nothing. A wrong `format` or `version` is rejected
  with HTTP 422.

The response lists `imported`, `skipped`, `created_categories`,
`created_tags`, `images_not_imported` and one `items` entry per recipe
(`title`, `status`, optional `reason`/`detail`, and `recipe_id` when imported).
Importing a file exported from the same workspace therefore imports nothing.
