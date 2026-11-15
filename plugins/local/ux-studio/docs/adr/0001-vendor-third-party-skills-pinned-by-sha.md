# Vendor third-party skills, pinned by SHA

The three upstream skills are copied into `skills/` and pinned to a commit SHA in
`vendor.lock` (`VENDOR.md` is generated from it), refreshed only by
`scripts/sync-vendor.sh` as a reviewable diff. They
are not installed on demand. The agents must find their skills in fresh cloud
sessions without an install step, and Impeccable ships executable JS we want to
read before it runs. Exceptions: Taste's 38 MB `assets/` folder (CSS, components and media the skill
relies on) is an On-demand folder: git-ignored, never touched by sync, and fetched at the
pinned SHA on first use by `scripts/fetch-on-demand.sh`, and
awesome-design-md (84 files, 3.2 MB) is reached through an index skill that fetches
one reference at a time. The existing `impeccable` entry in `skills-install` stays:
it serves project repos, not these agents.
