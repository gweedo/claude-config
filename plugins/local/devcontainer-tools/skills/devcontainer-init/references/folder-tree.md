# Default folder tree

`devcontainer-init` writes a single file, regardless of stack:

```
.devcontainer/
└── devcontainer.json
```

- The file content comes verbatim from `references/templates/<stack>.devcontainer.json`
  (see `references/defaults.json` for the stack → template mapping).
- No `Dockerfile` or `docker-compose.yml` is created — all three stacks use a prebuilt
  `image` directly.
- If a project later needs a multi-service setup (e.g. app + Postgres), start from
  `~/.claude/templates/devcontainer-base/` instead, which includes a `Dockerfile` and
  `docker-compose.yml`.
