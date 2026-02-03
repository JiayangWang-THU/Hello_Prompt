# Usage

## CLI Quickstart
1. `hpa`
2. `/templates` to list modes
3. `/mode CODE EXTEND` (or other CODE modes)
4. Fill slots with `key: value`, `key=value`, JSON, or `/paste` multi-line input
5. Use `/export` to save the session JSON

## Commands
- `/help` Show all commands
- `/templates` Show available templates
- `/mode <CATEGORY> <SUBTYPE>` Select mode (required first)
- `/show` Show slot status and current values
- `/clear <slot>` Clear a slot (aliases supported, e.g. `env`)
- `/export` Export current session to `exports/session_<timestamp>.json`
- `/reset` Reset session
- `/paste` Enter multi-line paste mode (end with a single `.`)

## Input Formats
- JSON object (multi-slot)
  ```json
  {"goal":"...","runtime_env":"Ubuntu 22.04","new_features":"P0 ..."}
  ```
- Multi-line key/value
  ```text
  goal: ...
  runtime_env: ...
  new_features: ...
  ```
- Single line key/value
  ```text
  goal: ...
  ```
