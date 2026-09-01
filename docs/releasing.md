# Releasing

Tacho uses Semantic Versioning and Conventional Commits. Normal commits never
replace the stable image.

1. Ensure CI is green on `master`.
2. Update both `backend/pyproject.toml` and `frontend/package.json` to the same
   version and regenerate their lockfiles.
3. Merge the version PR.
4. Create an annotated tag: `git tag -a vX.Y.Z -m "Tacho vX.Y.Z"`.
5. Push that tag only after review.

The release workflow validates both metadata versions, builds one multi-arch
image and publishes `X.Y.Z`, `X.Y` and `latest`. Only after the image succeeds
does it create the GitHub Release with generated notes.

Tags are immutable. A failed release is fixed with a new patch version, never by
moving or deleting a published tag.

Commits on `master` may publish `edge` and `sha-<commit>` after CI succeeds. Those
tags are development artifacts and never aliases for a stable release.
