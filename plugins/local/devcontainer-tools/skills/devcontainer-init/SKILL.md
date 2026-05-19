---
name: devcontainer-init
description: |
  Use this skill when the user invokes "/devcontainer" or "/devcontainer-init", or asks to
  "initialize a devcontainer", "set up a dev container", "scaffold a .devcontainer folder",
  "create a devcontainer.json", "configure a development container", or wants to set up a
  VS Code devcontainer for Node.js, Python, or a generic Ubuntu project.
version: 1.0.0
argument-hint: [node|python|generic]
allowed-tools: [Read, Glob, Write, AskUserQuestion]
---

# Devcontainer Init

Scaffold a `.devcontainer` folder with a ready-to-use `devcontainer.json` for the current project.

## Supported Stacks

| Argument  | Base image                                              | Ports            | postCreateCommand                  |
|-----------|---------------------------------------------------------|------------------|------------------------------------|
| `node`    | `mcr.microsoft.com/devcontainers/javascript-node:20`   | 3000, 5173, 4173 | `npm install`                      |
| `python`  | `mcr.microsoft.com/devcontainers/python:3.12`          | 8000             | `pip install -r requirements.txt`  |
| `generic` | `mcr.microsoft.com/devcontainers/base:ubuntu`          | —                | —                                  |

---

## Step 1 — Determine the target stack

The user's argument is: `$ARGUMENTS`

- If `$ARGUMENTS` (lowercased) is `node`, `python`, or `generic`, use that stack.
- If `$ARGUMENTS` is empty, unrecognised, or any other value, use AskUserQuestion:

  ```
  question: "Which stack should I generate the devcontainer for?"
  options:
    - node    — Node.js 20 (npm install, ESLint, Prettier, Tailwind, Vue Volar)
    - python  — Python 3.12 (pip install -r requirements.txt, Black, Ruff, Pylance)
    - generic — Ubuntu base (minimal, no language tooling)
  ```

  Wait for the answer before continuing.

---

## Step 2 — Check for an existing `.devcontainer`

Use Glob with pattern `.devcontainer/**` in the current working directory.

- If results are returned, use AskUserQuestion:

  ```
  question: "A .devcontainer folder already exists. Overwrite its contents?"
  options:
    - Yes, overwrite
    - No, cancel
  ```

  If the user chooses "No, cancel" (or any non-affirmative), stop immediately and reply:
  > "Cancelled — no files were changed."

---

## Step 3 — Validate stack prerequisites (warn only, do not abort)

**node**: Use Glob for `package.json`. If absent, note:
> "No `package.json` found — `postCreateCommand: npm install` will fail until one exists."

**python**: Use Glob for `requirements.txt`. If absent, note:
> "No `requirements.txt` found — `postCreateCommand: pip install -r requirements.txt` will fail until one exists."

**generic**: No validation needed.

---

## Step 4 — Write the files

Create `.devcontainer/devcontainer.json` using the exact template for the chosen stack.

### Node.js template

```json
{
  "name": "Node.js",
  "image": "mcr.microsoft.com/devcontainers/javascript-node:20",
  "forwardPorts": [3000, 5173, 4173],
  "postCreateCommand": "npm install",
  "remoteUser": "node",
  "customizations": {
    "vscode": {
      "extensions": [
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "bradlc.vscode-tailwindcss",
        "Vue.volar"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode"
      }
    }
  }
}
```

### Python template

```json
{
  "name": "Python 3.12",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "forwardPorts": [8000],
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteUser": "vscode",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "charliermarsh.ruff"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "ms-python.black-formatter",
        "python.defaultInterpreterPath": "/usr/local/bin/python"
      }
    }
  }
}
```

### Generic/Ubuntu template

```json
{
  "name": "Ubuntu",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "remoteUser": "vscode",
  "customizations": {
    "vscode": {
      "extensions": [],
      "settings": {}
    }
  }
}
```

---

## Step 5 — Report results

After writing all files, output a summary, for example:

```
Created:
  .devcontainer/devcontainer.json  (Node.js preset)

Next steps:
  • Open this folder in VS Code and select "Reopen in Container" to start the devcontainer.
  • Adjust forwardPorts or extensions in .devcontainer/devcontainer.json as needed.
```

If any prerequisite warnings were issued in Step 3, repeat them here as a reminder.
