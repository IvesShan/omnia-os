# Omnia IDE Bridge

Sends active file and cursor context to the Omnia Persona Daemon.

## Install

1. Open VS Code → Extensions (Ctrl+Shift+X)
2. Click `...` (More Actions) → `Install from VSIX...`
3. Select `omnia-ide-bridge-0.1.0.vsix`
4. Make sure the Omnia daemon is running (`./omnia status`)

## What it does

Whenever you switch tabs or move your cursor, the extension posts:
- active file path
- language ID
- cursor line & column
- selected text (truncated to 200 chars)

to `http://127.0.0.1:6789/ide-context`, where the Omnia daemon listens.
