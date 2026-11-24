# Contributing

Two people work on this repo. The rule that keeps us from breaking each other's work:
**spec first, failing test second, code third.**

## Set up once

```bash
git clone https://github.com/danikadelacroix/stallbreaker.git && cd stallbreaker
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cd frontend && npm install && cd ..
.venv/bin/python -m pytest -q          # expect: 27 passed
```

Run the app: see "Run the app" in the [README](README.md).

## The loop for every change

1. **Pick a spec** from [docs/specs](docs/specs/README.md). Put your name as owner and set the status to In progress, in the same pull request as your work. If there is no spec for what you want to do, copy [000-template.md](docs/specs/000-template.md) and write one first.
2. **Branch** from `main`: `spec/102-busy-day`, or `fix/short-description` for a bug.
3. **Write the failing test first.** Name it after the rule, in plain words, like the existing ones: `test_busy_day_is_repeatable`. Run it and see it fail for the right reason.
4. **Write the smallest code that makes it pass.** Then the next acceptance check.
5. **Run every check** before you push:
   ```bash
   .venv/bin/python -m pytest -q
   cd frontend && npx tsc -b && npx oxlint && npm run build
   ```
6. **Update the spec**: fill in the test names, tick the status to Built when every acceptance check passes. If you changed a rule, say so in the pull request.
7. **Open a pull request** to `main`. The other person reviews it. Do not merge your own pull request without a review, unless it only touches docs.

## Rules for the code

- **The engine (`shopcore.py`) is the riskiest file.** Any change to it needs an engine test in `tests/test_stallbreaker.py`, and `experiments/eval.py 200` must still pass its checks. Say in the pull request whether the benchmark numbers changed.
- **Every plan the app shows must pass `validate`.** Never skip it to save time.
- **Simulated stays labelled simulated.** Only part demand history is real. Do not write a number in the app or README that the code or an experiment did not produce.
- **Plain words on screen.** "Promise time", "jobs moved", "bay blocked". No solver terms in the UI.
- **No secrets in the repo.** API keys go in environment variables. `.db` files, `node_modules`, `dist` and `.venv` are already ignored.
- **No new dependency without a reason** in the pull request description.
- **Keep the demo day stable.** If you change `backend/seed.py`, the numbers in specs 003 and 004 may change. Re-check them and update the specs.

## Commit messages

Short first line in the imperative ("Add busy demo day"), then what and why if it is not
obvious. One feature per pull request.

## Where things are

| Path | What |
|---|---|
| `shopcore.py` | The engine (spec 001) |
| `backend/` | API and database (specs 002 to 005) |
| `frontend/src/` | The web app (spec 006) |
| `tests/` | Engine and API tests |
| `experiments/` | Benchmarks behind the README results |
| `docs/specs/` | Specs |
