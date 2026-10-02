# FactLens

Fact-checking and hate speech detection platform, FYP at FAST-NUCES.

## Repository structure

```
factlens/
├── backend/          Python backend: retrieval, decomposition, verification,
│                     hate speech classification, coreference resolution, API
│   ├── app/          One folder per module, matches Work Division ownership
│   ├── tests/        pytest test suite, run automatically by CI on every push
│   └── requirements.txt
├── frontend/         The clickable prototype goes here, and later becomes
│                     the real product frontend as Iteration 1+ replaces
│                     the mocked data with real API calls
└── .github/
    └── workflows/
        └── ci.yml    Runs the backend test suite automatically on every push
                       and pull request, see the CI/CD section below
```

## Where the prototype goes

The React prototype built for the proposal defense PoC belongs in
`frontend/`. It's real, working frontend code, not throwaway, the plan has
always been for it to carry forward into Iteration 1's actual frontend, so
it should live in this repo alongside the backend, not sit separately.

To add it: copy `factlens_prototype.jsx` into `frontend/src/`, along with
a proper `package.json` once you set it up as a real Vite project (see the
earlier setup steps for `npm create vite@latest`). Commit it on its own
branch, e.g. `feature/prototype-import`, same as any other piece of work,
then open a pull request into `develop`.

## Branching model

- `main`, always working, nothing is pushed here directly
- `develop`, integration branch, finished features land here first
- `feature/<name>`, one branch per piece of work, merged into `develop`
  via pull request once CI passes

## Running tests locally

```
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m pytest tests/ -v
```

## CI/CD

Every push and pull request automatically installs dependencies and runs
the full test suite via GitHub Actions (`.github/workflows/ci.yml`). A
pull request should not be merged into `develop` unless this check passes.
