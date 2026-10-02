# FactLens

![CI](https://github.com/syedairhakazmi/FactLens/actions/workflows/ci.yml/badge.svg?branch=develop)
![Deploy](https://github.com/syedairhakazmi/FactLens/actions/workflows/cd.yml/badge.svg?branch=main)

Fact-checking and hate speech detection platform, FYP at FAST-NUCES.

## Repository structure

```
factlens/
├── backend/          Python backend: retrieval, decomposition, verification,
│                     hate speech classification, coreference resolution, API
│   ├── app/          One folder per module, matches Work Division ownership
│   ├── tests/        pytest test suite, run automatically by CI on every push
│   └── requirements.txt
├── frontend/         React + Vite prototype — becomes the real product
│   ├── src/          React components (App.jsx is the main UI)
│   ├── public/       Static assets (favicon, icons)
│   └── package.json
└── .github/
    └── workflows/
        ├── ci.yml    CI — runs backend tests + frontend build on push & PR
        └── cd.yml    CD — auto-deploys frontend to GitHub Pages on merge to main
```

## Branching model

- `main` — always working, nothing is pushed here directly
- `develop` — integration branch, finished features land here first
- `feature/<name>` — one branch per piece of work, merged into `develop`
  via pull request once CI passes

## Running tests locally

### Backend
```bash
cd backend
pip install -r requirements.txt
pip install pytest
python -m spacy download en_core_web_sm
python -m pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev     # start dev server
npm run build   # production build
npm run lint    # check code quality
```

## CI/CD

### Continuous Integration (CI)
Every push and pull request to `main` or `develop` triggers two parallel jobs:
1. **Backend Tests** — installs Python deps, downloads spaCy model, runs pytest
2. **Frontend Build** — installs Node deps, runs ESLint, builds the Vite project

A pull request should not be merged unless both checks pass.

### Continuous Deployment (CD)
When code is merged into `main`, the frontend is automatically built and
deployed to **GitHub Pages**. This gives us a live, always-updated demo URL
that the evaluators can access at any time.
