# Add Claude Code + Docker files to devcontainer

## Context
The current `.devcontainer/devcontainer.json` uses the prebuilt `mcr.microsoft.com/devcontainers/javascript-node:20` image directly. The user wants:
1. The Claude Code VS Code extension and CLI available in the container.
2. Explicit Docker files (`Dockerfile` + `docker-compose.yml`) so the container build is fully owned by the repo and easy to extend with sidecar services later.

## Changes

### 1. `.devcontainer/Dockerfile` (new)
Base off the same Node 20 devcontainer image, install Claude Code globally, leave the default `node` user in place:

```dockerfile
FROM mcr.microsoft.com/devcontainers/javascript-node:20

# Install Claude Code CLI globally so it's on PATH for the `node` user.
RUN npm install -g @anthropic-ai/claude-code

USER node
```

### 2. `.devcontainer/docker-compose.yml` (new)
Single `app` service that builds from the Dockerfile, mounts the workspace, and keeps the container alive for VS Code to attach:

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - ..:/workspaces/CV:cached
    command: sleep infinity
    ports:
      - "5173:5173"
      - "4173:4173"
```

### 3. `.devcontainer/devcontainer.json` (edit)
Replace the `image` field with a compose-based config and add the Claude extension. Final shape:

```jsonc
{
  "name": "CV — Node 20",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspaces/CV",
  "forwardPorts": [5173, 4173],
  "portsAttributes": {
    "5173": { "label": "Vite dev server", "onAutoForward": "openBrowser" },
    "4173": { "label": "Vite preview",    "onAutoForward": "notify" }
  },
  "postCreateCommand": "npm install",
  "customizations": {
    "vscode": {
      "extensions": [
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "bradlc.vscode-tailwindcss",
        "Vue.volar",
        "anthropic.claude-code"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "typescript.tsdk": "node_modules/typescript/lib"
      }
    }
  },
  "remoteUser": "node"
}
```

Note: `image` and the old single-image port forwarding stay the same semantically — compose exposes the same ports, and `forwardPorts` keeps the VS Code UX.

## Files
- `.devcontainer/Dockerfile` — new
- `.devcontainer/docker-compose.yml` — new
- [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) — edit (switch from `image` to compose, add `anthropic.claude-code`)

## Verification
1. `Dev Containers: Rebuild Container` in VS Code — build should succeed using the new Dockerfile + compose.
2. In the container terminal, run `claude --version` to confirm the CLI is installed and on PATH.
3. Confirm the `anthropic.claude-code` extension is listed in the container's Extensions view.
4. Run `npm run dev` and confirm Vite is reachable on `localhost:5173` from the host.
