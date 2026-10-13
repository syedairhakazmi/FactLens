# FactLens

![CI](https://github.com/syedairhakazmi/FactLens/actions/workflows/ci.yml/badge.svg?branch=develop)
![Deploy](https://github.com/syedairhakazmi/FactLens/actions/workflows/cd.yml/badge.svg?branch=main)

A fact-checking system built as a Final Year Project at FAST-NUCES Islamabad. You give it a claim - in English or Urdu - and it runs it through an NLP pipeline to return a verdict, a confidence score, and the evidence it used.

---

## What it does

1. **Detects the input language** - auto-detects Urdu using Unicode ranges, translates to English for processing
2. **Resolves coreferences** - replaces pronouns with the nouns they refer to (e.g. "He said it" → "Elon Musk said the tweet")
3. **Classifies claims** - separates facts, opinions, questions, and non-checkable fragments
4. **Decomposes compound claims** - splits multi-part sentences into individual checkable claims
5. **Retrieves evidence** - hybrid search using BM25 (keyword) + dense embeddings (semantic) over the knowledge corpus
6. **Verifies each claim** - a DeBERTa-v3 NLI cross-encoder decides Supported / Refuted / Not Enough Evidence
7. **Aggregates verdict** - combines results from all sub-claims into one overall verdict
8. **Returns bilingual output** - if the input was Urdu, verdicts and reasons are shown in Urdu too

---

## Modules

| Module | Folder | What it does |
|---|---|---|
| API | `backend/app/api/` | FastAPI server - handles requests and runs the full pipeline |
| Claims Detector | `backend/app/claims/` | Classifies each sentence as Fact, Opinion, Question, or Non-Checkable |
| Coreference Resolver | `backend/app/coreference/` | Links pronouns to their referents using LingMessCoref |
| Claim Decomposer | `backend/app/decomposition/` | Splits compound sentences into atomic claims |
| Retriever | `backend/app/retrieval/` | BM25Plus + BAAI/bge-base dense embeddings for hybrid evidence search |
| Verifier | `backend/app/verification/` | DeBERTa-v3-large NLI model - gives Supported / Refuted / Not Enough Evidence |
| Translator | `backend/app/translation/` | Detects Urdu script, translates via MyMemory API, maps verdicts to Urdu |

---

## Verdicts

| English | Urdu |
|---|---|
| Supported | تصدیق شدہ |
| Refuted | مسترد شدہ |
| Not Enough Evidence | ناکافی شواہد |
| Mixed | ملا جلا |
| Opinion | رائے |
| Non-Checkable | ناقابل تصدیق |

---

## Project structure

```
factlens/
├── backend/
│   ├── app/
│   │   ├── api/            FastAPI routes and pipeline orchestration
│   │   ├── claims/         Fact vs opinion detector
│   │   ├── coreference/    Coreference resolution
│   │   ├── decomposition/  Claim decomposer
│   │   ├── retrieval/      Hybrid BM25 + embedding search
│   │   ├── verification/   NLI-based claim verifier
│   │   └── translation/    Urdu detection and translation
│   ├── tests/              pytest test suite (107 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── App.jsx         Full React UI with bilingual support and RTL layout
│   └── package.json
└── .github/
    └── workflows/
        ├── ci.yml          Runs backend tests + frontend build on every push/PR
        └── cd.yml          Auto-deploys to GitHub Pages when main is updated
```

---

## Running locally

### Backend
```bash
cd backend
pip install -r requirements.txt
pip install pytest
python -m spacy download en_core_web_sm
uvicorn app.api.main:app --reload   # starts the API at http://localhost:8000
```

### Run tests
```bash
cd backend
python -m pytest tests/ -v          # runs all 107 tests
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # starts UI at http://localhost:5173
npm run build     # production build
npm run lint      # check for code issues
```

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Check if the server is running |
| `/api/analyze` | POST | Run the full fact-check pipeline on a claim |

**Example request:**
```json
POST /api/analyze
{ "text": "The Eiffel Tower was built in 1889." }
```

**Example Urdu request:**
```json
POST /api/analyze
{ "text": "ایفل ٹاور 1889 میں تعمیر کیا گیا تھا۔" }
```

---

## Branches

- `main` - stable, production-ready code
- `develop` - features go here first before going to main
- `feature/<name>` - one branch per feature, merged into develop via PR

---

## CI/CD

Every push or PR to `main` or `develop` runs two checks automatically:

- **Backend Tests** - runs all 107 pytest tests
- **Frontend Build** - runs ESLint and builds the Vite project

Both checks must pass before a PR can be merged.

When code is merged into `main`, the frontend is auto-deployed to GitHub Pages.


## Project structure

```
factlens/
├── backend/          Python backend (API, retrieval, verification, NLP)
│   ├── app/          One folder per module
│   ├── tests/        pytest tests - run by CI on every push
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

- `main` - stable, production-ready code
- `develop` - features go here first before going to main
- `feature/<name>` - one branch per feature, merged into develop via PR

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

- **Backend Tests** - runs all pytest tests
- **Frontend Build** - runs ESLint and builds the Vite project

Both checks must pass before a PR can be merged.

When code is merged into `main`, the frontend is auto-deployed to GitHub Pages.
