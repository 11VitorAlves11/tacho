# Migration from `tacho_app`

Tacho 2.0 changes repository and image names but preserves the PostgreSQL schema
and image directory layout.

## Repository clone

After the GitHub repository is renamed manually:

```bash
git remote set-url origin https://github.com/11VitorAlves11/tacho.git
```

GitHub normally redirects the old URL, but updating the remote avoids depending
on that redirect.

## Existing installation

1. Keep the old Compose file and image tags available for rollback.
2. Back up the database, images and current `.env`.
3. Identify the existing PostgreSQL and image volume/bind-mount names.
4. Create a private override mapping those exact locations into the new stack.
5. Set `TACHO_VERSION=2.0.0` and start the migration service first.
6. Validate recipes and photographs before removing the old containers.

The old packages remain available. Version 2.0 is the single transition release
for the aliases `tacho_app-web` and `tacho_app-celery-worker`; later releases use
only `ghcr.io/11vitoralves11/tacho`.

## Branch rename

If `master` is renamed to `main`, existing clones update with:

```bash
git fetch origin
git branch -m master main
git branch --set-upstream-to=origin/main main
git remote set-head origin -a
```

Do not delete the remote `master` branch until every workflow, ruleset and
external automation has been verified against `main`.
