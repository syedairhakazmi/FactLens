# FactLens

![CI](https://github.com/syedairhakazmi/FactLens/actions/workflows/ci.yml/badge.svg?branch=develop)
![Deploy](https://github.com/syedairhakazmi/FactLens/actions/workflows/cd.yml/badge.svg?branch=main)

A fact-checking system built as an FYP at FAST-NUCES. It takes a claim in English or Urdu, checks it against a knowledge base, and returns a verdict with evidence.

## Project structure

```
factlens/
├── backend/          Python backend (API, retrieval, verification, NLP)
│   ├── app/          One folder per module
│   ├── tests/        pytest tests — run by CI on every push
│   └── requirements.txt
├── frontend/         React + Vite UI
│   ├── src/          Main UI lives in App.jsx
│   └── package.json
└── .github/
    └── workflows/
        ├── ci.yml    Runs tests + build on every push and PR
        └── cd.yml    Deploys frontend to GitHub Pages when main is updated
```

## Branches

- `main` — stable, production-ready code
- `develop` — features go here first before going to main
- `feature/<name>` — one branch per feature, merged into develop via PR

## Running locally

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

Every push or PR to `main` or `develop` runs two checks automatically:

- **Backend Tests** — runs all pytest tests
- **Frontend Build** — runs ESLint and builds the Vite project

Both checks must pass before a PR can be merged.

When code is merged into `main`, the frontend is auto-deployed to GitHub Pages.
