---
name: devcontainer-init
description: |
  Use this skill when the user invokes "/devcontainer-init", or asks to
  "initialize a devcontainer", "set up a dev container", "scaffold a .devcontainer folder",
  "create a devcontainer.json", "configure a development container", or wants to set up a
  VS Code devcontainer for Node.js, Python, or a generic Ubuntu project.
version: 1.1.0
argument-hint: [node|python|generic]
allowed-tools: [Read, Glob, Write, AskUserQuestion]
---

# Devcontainer Init

Scaffold a `.devcontainer` folder with a ready-to-use `devcontainer.json` for the current project.

All stack data — base image, ports, `postCreateCommand`, extensions, settings, and
prerequisite checks — lives in `references/defaults.json`. The actual file content to
write for each stack lives in `references/templates/<stack>.devcontainer.json`. The
resulting folder layout is documented in `references/folder-tree.md`.

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
- If `$ARGUMENTS` is empty, unrecognised, or any other value, read
  `references/defaults.json` and use AskUserQuestion with one option per key under
  `stacks`, using each stack's `label` as the option description:

  ```
  question: "Which stack should I generate the devcontainer for?"
  options:
    - node    — <stacks.node.label>
    - python  — <stacks.python.label>
    - generic — <stacks.generic.label>
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

Read `references/defaults.json` and look up `stacks.<stack>.prerequisiteFile` and
`stacks.<stack>.prerequisiteWarning` for the chosen stack.

- If `prerequisiteFile` is non-null, use Glob for that file in the project root.
- If it is not found, note the corresponding `prerequisiteWarning` to repeat in Step 5.
- If `prerequisiteFile` is `null` (the `generic` stack), no validation is needed.

---

## Step 4 — Write the files

1. Read `references/templates/<stack>.devcontainer.json` (the chosen stack's template).
2. Write its contents verbatim to `.devcontainer/devcontainer.json`.

The templates already include the baseline extensions described in
`references/default-extensions.md` — no merging is required.

---

## Step 5 — Report results

After writing the file, output a summary, for example:

```
Created:
  .devcontainer/devcontainer.json  (Node.js preset)

Next steps:
  • Open this folder in VS Code and select "Reopen in Container" to start the devcontainer.
  • Adjust forwardPorts or extensions in .devcontainer/devcontainer.json as needed.
```

If a prerequisite warning was noted in Step 3, repeat it here as a reminder.
