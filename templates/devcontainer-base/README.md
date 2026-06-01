# Reusable Devcontainer Template

A minimal, composable devcontainer template for use across projects.

## What's Included

- Ubuntu base image with essential build tools
- **Claude Code extension** (`anthropic.claude-code`) for immediate Claude AI integration
- **GitHub CLI** for git/PR workflows
- Basic docker-compose and Dockerfile setup

## Quick Start

### 1. Copy to Your Project

```bash
cp -r ~/.claude/templates/devcontainer-base/.devcontainer /path/to/your/project/
```

### 2. Customize for Your Project

Edit `.devcontainer/devcontainer.json` to add language features and extensions specific to your needs.

### 3. Open in Devcontainer

In VS Code:
- Open the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
- Select **"Dev Containers: Reopen in Container"**
- Wait for the container to build and start

## Customization Examples

### Node.js Project

Add Node 20 to `features` in `devcontainer.json`:

```json
"features": {
  "ghcr.io/devcontainers/features/github-cli:1": {},
  "ghcr.io/devcontainers/features/node:1": {
    "version": "20"
  }
}
```

Add Node extensions:

```json
"extensions": [
  "anthropic.claude-code",
  "dbaeumer.vscode-eslint",
  "esbenp.prettier-vscode"
]
```

### Python Project

Add Python 3.12 to `features`:

```json
"features": {
  "ghcr.io/devcontainers/features/github-cli:1": {},
  "ghcr.io/devcontainers/features/python:1": {
    "version": "3.12"
  }
}
```

Add Python extensions:

```json
"extensions": [
  "anthropic.claude-code",
  "ms-python.python",
  "ms-python.vscode-pylance",
  "charliermarsh.ruff"
]
```

### Polyglot Project (Node + Python + Postgres)

```json
"features": {
  "ghcr.io/devcontainers/features/github-cli:1": {},
  "ghcr.io/devcontainers/features/node:1": {
    "version": "20"
  },
  "ghcr.io/devcontainers/features/python:1": {
    "version": "3.12"
  }
},
"forwardPorts": [3000, 8000, 5432]
```

And update `docker-compose.yml` to include a Postgres service:

```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: dev-container
    container_name: app
    mounts:
      - /var/run/docker.sock:/var/run/docker.sock
    volumes:
      - /workspace
    command: sleep infinity
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/myapp_dev
    depends_on:
      - db

  db:
    image: postgres:16
    container_name: db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myapp_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Available Features

Full list of devcontainer features available at: https://github.com/devcontainers/features

Common ones:
- `ghcr.io/devcontainers/features/node:1` — Node.js
- `ghcr.io/devcontainers/features/python:1` — Python
- `ghcr.io/devcontainers/features/go:1` — Go
- `ghcr.io/devcontainers/features/rust:1` — Rust
- `ghcr.io/devcontainers/features/github-cli:1` — GitHub CLI (included by default)

## Verification

Once your container starts:

1. **Verify Claude Code extension:**
   - Check the Extensions panel — `anthropic.claude-code` should be installed
   - Open the Claude Code panel to confirm it works

2. **Verify GitHub CLI:**
   ```bash
   gh --version
   ```

3. **Verify language tools** (if added):
   ```bash
   node -v      # if Node feature added
   python -v    # if Python feature added
   ```

## Troubleshooting

### Extension won't install

Make sure the extension ID is correct: `anthropic.claude-code` (not `anthropic.claude`)

### Container build fails

1. Check Docker is running
2. Look at the build output in the VS Code terminal
3. Try rebuilding: **Dev Containers: Rebuild Container**

### Port conflicts

If a forwarded port is already in use, change it in `devcontainer.json`:

```json
"forwardPorts": [3001, 8001]  // change 3000 → 3001, etc.
```

## Notes

- The `postCreateCommand` installs/upgrades npm and pip if Node/Python are present
- Customize environment variables in `docker-compose.yml` under `environment:`
- Add project-specific settings to the `settings` object in devcontainer.json
