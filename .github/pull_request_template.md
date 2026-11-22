## What

Spec: docs/specs/NNN-... (rules or acceptance checks this covers)

## Checks

- [ ] Failing test written first, now passing
- [ ] `.venv/bin/python -m pytest -q` passes
- [ ] `cd frontend && npx tsc -b && npx oxlint && npm run build` passes
- [ ] Spec updated (test names, status, any rule changed)
- [ ] Engine changed? Engine test added and benchmark re-run
- [ ] No secrets, no personal data, no `.db` file
