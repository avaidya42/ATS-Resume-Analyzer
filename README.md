# Resume Intelligence Platform

Full-stack app that parses PDF resumes, scores them for ATS compatibility, and
(next milestone) matches them against job descriptions using an LLM.

## Stack
- **Backend:** FastAPI, Pydantic, PyMuPDF (PDF text extraction), rule-based NLP parsing
- **Frontend:** React + Vite, Tailwind CSS, Axios

## Run locally

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY later for AI features
uvicorn app.main:app --reload
```
Runs on http://localhost:8000 — docs at `/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Runs on http://localhost:5173, proxying `/api` to the backend.

## What's implemented (Milestone 1)
- PDF upload with type/size validation
- Text extraction (PyMuPDF)
- Regex + section-heuristic resume parser → structured JSON
  (contact, education, experience, projects, skills, certifications, achievements, languages)
- Rule-based ATS scorer with an 8-factor weighted breakdown
- Dashboard UI: upload, parsed resume view, ATS score ring + breakdown, JSON export

## Architecture notes
- `app/services/pdf_parser.py` — raw text extraction only
- `app/services/resume_extractor.py` — text → structured `ParsedResume`
- `app/services/ats_scorer.py` — `ParsedResume` → `ATSResult`
- Resumes are kept in an in-memory store keyed by `resume_id` (swap for a DB
  repository when persistence is needed — schema is already Pydantic-typed)

## Next milestones
AI resume review (Anthropic API), job description matching, PDF report export,
Docker, tests, deployment.
