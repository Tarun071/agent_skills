import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from agent.workflow import discover_skills, read_skill_metadata, run_sales_workflow

app = FastAPI(title="AI-Powered Sales Reporting Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple response used to verify that the API is running."""
    return {"status": "ok"}


@app.get("/skills")
def list_skills() -> dict:
    """Return names and descriptions for the available Agent Skills."""
    skills = []

    for skill_name, skill_file in discover_skills().items():
        metadata = read_skill_metadata(skill_file)
        skills.append({
            "name": skill_name,
            "description": metadata["description"],
        })

    return {"skills": skills}


@app.post("/process")
async def process_sales_report(
    request: str = Form(...),
    file: UploadFile | None = File(default=None),
) -> dict:
    """Process an uploaded sales file using the existing LangGraph workflow."""
    request_text = request.strip()
    if not request_text or not any(character.isalnum() for character in request_text):
        raise HTTPException(
            status_code=400,
            detail="A meaningful user request containing text is required.",
        )

    temporary_path = None

    try:
        if file is None:
            raise HTTPException(status_code=400, detail="A CSV or XLSX sales file is required.")

        filename = file.filename or ""
        extension = Path(filename).suffix.lower()
        if extension not in (".csv", ".xlsx"):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file extension. Please upload a CSV or XLSX file.",
            )

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        unique_name = f"{uuid.uuid4().hex}{extension}"
        temporary_path = Path(tempfile.gettempdir()) / unique_name
        temporary_path.write_bytes(content)

        try:
            workflow_result = run_sales_workflow(request_text, str(temporary_path))
        except Exception as error:
            workflow_result = {
                "selected_skills": {},
                "execution_steps": [],
                "sales_analysis": None,
                "business_insights": [],
                "pdf_path": None,
                "email_draft": None,
                "errors": [f"Workflow execution failed: {error}"],
            }

        email_draft = workflow_result.get("email_draft")
        errors = workflow_result.get("errors", [])

        selected_skills = workflow_result.get("selected_skills", {})
        execution_steps = workflow_result.get("execution_steps", [])

        if not selected_skills or not execution_steps:
            response_status = "error"
        elif errors:
            response_status = "partial_success"
        else:
            response_status = "success"

        return {
            "status": response_status,
            "selected_skills": workflow_result.get("selected_skills", {}),
            "execution_steps": workflow_result.get("execution_steps", []),
            "sales_analysis": workflow_result.get("sales_analysis"),
            "business_insights": workflow_result.get("business_insights", []),
            "pdf_path": workflow_result.get("pdf_path"),
            "email_draft": {
                "subject": email_draft.get("subject") if email_draft else None,
                "body": email_draft.get("body") if email_draft else None,
                "attachment_path": email_draft.get("attachment_path") if email_draft else None,
            },
            "errors": errors,
        }

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
