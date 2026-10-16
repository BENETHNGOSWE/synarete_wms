# WMS development scripts

Run the static check from the repository root:

```bash
python3 scripts/validate_repo.py
```

Run the local Frappe smoke test from a WSL terminal after the app has been copied into the local bench apps directory:

```bash
bash scripts/local_smoke.sh
```

The smoke script is local-only. It does not contain production container names or production SSH commands.
