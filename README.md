# AI-Powered Sales Reporting Assistant

A beginner-friendly Python project that uploads sales CSV or Excel files, analyzes them with a LangGraph workflow, generates a PDF report, and prepares an email draft.

## Agent Skill Architecture

Sales functionality is organized into self-contained Agent Skills:

- `skills/sales-analysis/` — CSV/XLSX loading, validation, and sales calculations.
- `skills/report-generation/` — HTML/CSS templates and ReportLab PDF generation.
- `skills/email-composition/` — reusable email draft template and draft generation.

Each skill contains:

- `SKILL.md` — purpose, inputs, instructions, and dependencies.
- `scripts/execute.py` — Python implementation.
- `templates/` — reusable report and email templates.
- `references/` — data and formatting documentation.

The LangGraph workflow discovers skills dynamically and executes their scripts. The `services/` modules remain compatibility exports for existing imports.

## Phase 1

This foundation currently provides:

- A FastAPI application
- A `GET /health` endpoint
- Python dependency configuration for later LangGraph and reporting features

Agent Skills, LangGraph, Gemini calls, PDF generation, and sales analysis are intentionally not implemented in this phase.

## Setup

1. Install Python 3.12 or newer.
2. Install dependencies:

   ```powershell
   uv sync --dev
   ```

3. Copy `.env.example` to `.env` and add your Gemini API key.
4. Start the API:

   ```powershell
   uv run uvicorn main:app --reload
   ```

5. Open `http://127.0.0.1:8000/health` or view API documentation at `http://127.0.0.1:8000/docs`.

## Test

```powershell
uv run pytest
```
