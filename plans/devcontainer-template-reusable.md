# Reusable Devcontainer Template

## Context

Goal: Create a generic, minimal devcontainer template that can be used as a starting point for **any new project**. The template should include:
- **Claude VSCode extension** (`anthropic.claude-code`) — so Claude Code is immediately available for development
- **GitHub CLI** — for git/PR workflows
- Minimal, composable base configuration that can be extended for specific project types (Node, Python, polyglot, etc.)

This avoids manual re-setup of these tools for every new project and ensures consistency across all development environments.

## Approach

Create a **minimal base devcontainer** stored in `~/.claude/templates/devcontainer-base/` that includes:
1. Ubuntu base image
2. Claude VSCode extension (mandatory for all projects)
3. GitHub CLI feature (mandatory for all projects)
4. Minimal Dockerfile with just curl + build-essential
5. Basic devcontainer.json with extensible `features: {}` section
6. Basic docker-compose.yml
7. README.md with usage instructions and examples

Users can copy this template to new projects and customize by:
- Adding language features (Node 20, Python 3.12, etc.) via the `features` section
- Adding project-specific extensions (Tailwind, Ruff, etc.)
- Customizing ports and environment variables
- Adjusting the docker-compose.yml as needed

## Files to Create

### 1. `~/.claude/templates/devcontainer-base/.devcontainer/devcontainer.json`

```json
{
  "name": "Development Container",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  "remoteUser": "vscode",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "anthropic.claude-code"
      ],
      "settings": {}
    }
  },
  "postCreateCommand": "npm install --global npm 2>/dev/null || true; python -m pip install --upgrade pip 2>/dev/null || true"
}
```

### 2. `~/.claude/templates/devcontainer-base/.devcontainer/Dockerfile`

```dockerfile
FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
```

### 3. `~/.claude/templates/devcontainer-base/.devcontainer/docker-compose.yml`

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
```

### 4. `~/.claude/templates/devcontainer-base/README.md`

Documentation explaining:
- How to copy the template to a new project
- How to add language features (Node 20, Python 3.12, Go, Rust, etc.)
- How to add project-specific VSCode extensions
- How to customize ports and environment variables
- Example configurations for Node-only, Python-only, polyglot, and Go projects

## Implementation Steps

1. Create directory: `~/.claude/templates/devcontainer-base/`
2. Create `.devcontainer/` subfolder with the 3 files above
3. Create README.md with usage guide
4. Test the template by:
   - Creating a temporary test project
   - Copying `.devcontainer/` to it
   - Opening in VS Code devcontainer
   - Verifying Claude extension loads and GitHub CLI is available

## Verification

1. **Create test project:**
   ```bash
   mkdir ~/test-devcontainer-template
   cd ~/test-devcontainer-template
   git init
   cp -r ~/.claude/templates/devcontainer-base/.devcontainer .
   ```

2. **Open in devcontainer** — Use "Reopen in Container" from VSCode command palette

3. **Verify Claude extension:**
   - Check Extensions panel — `anthropic.claude-code` should be installed and enabled
   - Verify it works (can open Claude Code panel)

4. **Verify GitHub CLI:**
   - Open terminal in devcontainer
   - Run `gh --version` — should succeed

5. **Test extension/customization:**
   - Add Node 20 feature to devcontainer.json:
     ```json
     "ghcr.io/devcontainers/features/node:1": {
       "version": "20"
     }
     ```
   - Rebuild container
   - Run `node -v` — should show Node 20

6. **Clean up test project:**
   ```bash
   cd ~
   rm -rf test-devcontainer-template
   ```
