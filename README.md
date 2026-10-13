# FactLens — Multi-Stage Fact Verification & Contextual Harm Detection Platform

[![CI](https://github.com/syedairhakazmi/FactLens/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/syedairhakazmi/FactLens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61dafb.svg)](https://react.dev/)

> **Final Year Project (FYP) — FAST-NUCES**  
> A dual-lens verification platform integrating multi-stage natural language processing, hybrid evidence retrieval over unified benchmark corpora, cross-encoder natural language inference, sentence decomposition, and cross-lingual Urdu support.

---

## 📌 System Architecture

```text
                                  User Input
                         (English or Urdu Script)
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        [English Pipeline]                      [Urdu Translation]
                 │                                       │ (Neural MT)
                 └───────────────────┬───────────────────┘
                                     ▼
                     [1. Coreference Resolution]
                     (LingMessCoref / Longformer)
                                     │
                                     ▼
               [2. Claim Extraction & Checkability Filter]
                 ├── Factual Assertions ────────┐
                 ├── Subjective Opinions        │
                 └── Non-Checkable Fragments    │
                                                ▼
                                [3. Sentence Decomposition]
                                (spaCy Dependency Rules)
                                                │
                                                ▼
                                [4. Hybrid Evidence Retrieval]
                                 ├── BM25Plus Lexical Match
                                 └── BAAI/bge-base Dense Embeddings
                                                │
                                                ▼
                                [5. Multi-Benchmark Corpus]
                                 ├── SciFact (Biomedical & Clinical)
                                 ├── FEVER 2018 & FEVER 2.0 (General Facts)
                                 ├── FEVEROUS (Structured Tables & Text)
                                 └── AVeriTeC (Real-World Web Claims)
                                                │
                                                ▼
                               [6. Claim Verification Engine]
                                (DeBERTa-v3 NLI Cross-Encoder)
                                                │
                                                ▼
                               [7. Verdict Aggregation]
                        Supported | Refuted | Inconclusive | Mixed
                                                │
                                                ▼
                                    Interactive UI
                      (Bilingual Display, Confidence Dial, RTL)
```

---

## 🚀 Key Modules & Capabilities (FYP-1 Scope)

### 1. Cross-Lingual Urdu Support (`app/translation`)
- **Automatic Script Detection**: Scans Unicode ranges (`0x0600–0x06FF`, `0xFB50–0xFDFF`) to detect Urdu text.
- **Cross-Lingual Verification**: Translates Urdu statements to English for dense retrieval across large-scale English benchmark corpora.
- **Bilingual Response Mapping**: Translates evidence passages, verdicts (*تصدیق شدہ*, *مسترد شدہ*, *ناکافی شواہد*, *ملا جلا*), and reasoning back into Urdu with RTL UI rendering.

### 2. Contextual Pronoun Resolution (`app/coreference`)
- Resolves cross-sentence pronoun chains (e.g., *"The COVID-19 vaccine received authorization. It was tested..."* $\to$ *"The COVID-19 vaccine was tested..."*) using `LingMessCoref` (Longformer architecture).

### 3. Claim Extraction & Classification (`app/claims`)
- Differentiates:
  - **Factual Claims**: Verifiable assertions sent for retrieval.
  - **Subjective Opinions**: Statements with first-person belief markers or copula adjectives (*"I believe..."*, *"in my opinion..."*).
  - **Non-Checkable Fragments**: Questions, single-word inputs, numbers, and predicate-less fragments with explanatory rationale.

### 4. Sentence Decomposition (`app/decomposition`)
- Implements the Phase 1 Iteration 1 rule-based dependency baseline.
- Decomposes compound and conjoined sentences into atomic, independently checkable sub-claims so each fact is verified separately.

### 5. Hybrid Evidence Retrieval (`app/retrieval`)
- **Lexical Search**: BM25Plus with custom stopword removal and tokenization.
- **Dense Semantic Retrieval**: Sentence-transformer embeddings (`BAAI/bge-base-en-v1.5`).
- **Unified Corpus**: Aggregates passages across 5 major fact-checking benchmarks:
  - **SciFact**: Biomedical and scientific publications.
  - **FEVER 2018 & 2.0**: General-domain Wikipedia facts and adversarial examples.
  - **FEVEROUS**: Tabular and unstructured evidence.
  - **AVeriTeC**: Complex, multi-source web claims.

### 6. Verification Engine (`app/verification`)
- Fine-tuned `cross-encoder/nli-deberta-v3-small` NLI model.
- Classifies premise-hypothesis pairs into entailment, contradiction, and neutral with calibrated confidence percentages.
- Features bounded retry when evidence margins are narrow.

### 7. Multi-Claim Verdict Aggregation (`app/api`)
- Computes comprehensive overall verdicts:
  - **Supported**: All factual sub-claims verified.
  - **Refuted**: At least one contradicted sub-claim present.
  - **Mixed**: Combination of supported and refuted claims in a compound sentence.
  - **Not Enough Evidence**: Corpus lacks sufficient corroborating evidence.

### 8. Contextual Harm & Hate Speech (Roadmap — Iteration 3 / FYP-2)
- Formally scheduled for FYP-2 in accordance with the proposal defense roadmap.
- UI transparently documents the planned *HateXplain* contextual transformer and *HateCheck* diagnostic evaluation suite to ensure academic honesty.

---

## 📂 Repository Structure

```text
FactLens/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints & Pydantic response models
│   │   ├── claims/          # spaCy claim detection & opinion filtering
│   │   ├── coreference/     # LingMessCoref pronoun resolution
│   │   ├── decomposition/   # Dependency-rule atomic claim decomposer
│   │   ├── retrieval/       # BM25 + BGE embedding hybrid search & multi-corpus loader
│   │   ├── translation/     # Urdu Unicode detection & cross-lingual translation
│   │   ├── verification/    # DeBERTa-v3 NLI cross-encoder verifier
│   │   └── pipeline.py      # End-to-end orchestration pipeline
│   ├── tests/               # 100+ pytest unit and integration test suite
│   └── requirements.txt     # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Interactive React UI with RTL & bilingual inspection
│   │   └── main.jsx         # Vite entry point
│   ├── package.json
│   └── vite.config.js
└── .github/
    └── workflows/
        ├── ci.yml           # Runs pytest test battery + npm lint + npm build
        └── cd.yml           # Automated deployment workflow
```

---

## 🛠️ Local Setup & Running

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start FastAPI server:
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Verification

Run the comprehensive backend test battery:
```bash
cd backend
pytest tests/ -v
```
*(All 107 test cases pass across coreference, detector, decomposition, retrieval, verifier, translation, and API integration).*

Run frontend quality checks:
```bash
cd frontend
npm run lint    # ESLint verification
npm run build   # Production bundle validation
```

---

## 🎯 Evaluator Demo Scenarios

During evaluation, test the following key capabilities:

1. **Medical Claim Match (SciFact)**:
   > *"Water boils at 100 degrees Celsius at standard atmospheric pressure."* $\to$ **Supported (89%+)**
2. **Refuted Health Disinformation**:
   > *"The COVID-19 vaccine causes infertility in most patients."* $\to$ **Refuted (94%)**
3. **Coreference Resolution**:
   > *"The COVID-19 vaccine received official authorization. It was evaluated in randomized clinical trials."* $\to$ Resolves pronoun **It** to **The COVID-19 vaccine**.
4. **Subjective Opinion Filter**:
   > *"I think this is the most wonderful restaurant in the city."* $\to$ Detected as **Opinion** (excluded from retrieval).
5. **Non-Checkable Fragment**:
   > *"i"* or *"what is this?"* $\to$ Detected as **Non-Checkable** with descriptive rationale.
6. **Compound Sentence Decomposition (Mixed Verdict)**:
   > *"The Eiffel Tower was completed in 1889, and it was constructed entirely out of solid titanium."* $\to$ Split into 2 sub-claims (**Claim 1: Supported**, **Claim 2: Refuted**), yielding an aggregated **Mixed** verdict.
7. **Cross-Lingual Urdu Input**:
   > *"پیرس فرانس کا دارالحکومت ہے۔"* $\to$ Detects Urdu, performs cross-lingual retrieval, and displays verdict in Urdu (**تصدیق شدہ**).

---

## 👥 Authors & Academic Context

- **Department of Computer Science**, FAST-NUCES
- **Course**: Final Year Project (FYP-1 & FYP-2)
- **Advisor / Supervisors**: FAST-NUCES Faculty
