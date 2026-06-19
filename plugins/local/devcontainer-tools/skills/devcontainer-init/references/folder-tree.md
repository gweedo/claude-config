# Default folder tree

`devcontainer-init` writes `devcontainer.json` regardless of stack, plus an optional
`gitconfig` when the user opts into global git config:

```
.devcontainer/
├── devcontainer.json
└── gitconfig          (optional — only when git config is initialized)
```

- The `devcontainer.json` content comes verbatim from
  `references/templates/<stack>.devcontainer.json` (see `references/defaults.json` for the
  stack → template mapping).
- `gitconfig` is rendered from `references/templates/gitconfig.template` with the
  committer identity substituted, and is wired into the container via
  `git config --global include.path` in `postCreateCommand` (see `gitConfig` in
  `references/defaults.json`). It is stack-independent.
- No `Dockerfile` or `docker-compose.yml` is created — all three stacks use a prebuilt
  `image` directly.
- If a project later needs a multi-service setup (e.g. app + Postgres), start from
  `~/.claude/templates/devcontainer-base/` instead, which includes a `Dockerfile` and
  `docker-compose.yml`.
