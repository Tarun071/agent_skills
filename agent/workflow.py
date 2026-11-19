from pathlib import Path
from typing import TypedDict
import importlib.util
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from config import get_settings


class BusinessState(TypedDict):
    request: str
    file_path: str | None
    selected_skills: dict[str, str]
    loaded_instructions: dict[str, str]
    sales_analysis: dict | None
    business_insights: list[str]
    pdf_path: str | None
    email_draft: dict | None
    execution_steps: list[str]
    errors: list[str]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = PROJECT_ROOT / "skills"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"


def discover_skills():
    """Find available skill folders and return their name and SKILL.md path."""
    discovered = {}

    if not SKILLS_ROOT.exists():
        return discovered

    for folder in sorted(SKILLS_ROOT.iterdir(), key=lambda item: item.name):
        skill_file = folder / "SKILL.md"
        if folder.is_dir() and skill_file.is_file():
            discovered[folder.name] = skill_file

    return discovered


def read_skill_metadata(skill_file):
    """Read the skill name and description from YAML frontmatter."""
    text = skill_file.read_text(encoding="utf-8")

    if not text.startswith("---"):
        return {"name": skill_file.parent.name, "description": ""}

    parts = text.split("---", 2)
    metadata = {}

    if len(parts) >= 3:
        for line in parts[1].strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

    metadata.setdefault("name", skill_file.parent.name)
    metadata.setdefault("description", "")
    return metadata


def create_gemini_model():
    """Create Gemini from the centralized application settings."""
    settings = get_settings()

    if not settings.google_api_key or settings.google_api_key.lower() in {
        "your_google_api_key_here",
    }:
        raise ValueError("GOOGLE_API_KEY is missing or invalid. Add it to your .env file.")

    if not settings.gemini_model:
        raise ValueError("GEMINI_MODEL is missing. Add it to your .env file.")

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    )


def extract_json_object(text):
    """Extract a JSON object from a string or list of Gemini content blocks."""
    if isinstance(text, str):
        cleaned = text
    elif isinstance(text, list):
        text_parts = []
        for block in text:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                block_text = block.get("text")
                if isinstance(block_text, str):
                    text_parts.append(block_text)
        cleaned = "".join(text_parts)
    else:
        cleaned = ""

    if not cleaned.strip():
        raise ValueError("Gemini response contained no usable text.")

    cleaned = cleaned.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Gemini did not return a JSON object.")

    return json.loads(cleaned[start:end + 1])


def select_skills(state: BusinessState) -> BusinessState:
    """Discover skills and use Gemini to select relevant skill names and reasons."""
    discovered = discover_skills()
    state.setdefault("selected_skills", {})
    state.setdefault("loaded_instructions", {})
    state.setdefault("execution_steps", [])
    state.setdefault("errors", [])

    request = str(state.get("request", "")).strip()
    if not request or not any(character.isalnum() for character in request):
        state["errors"].append("A meaningful request containing text is required.")
        return state

    if not discovered:
        state["errors"].append("Gemini skill selection failed: no Agent Skills were discovered.")
        return state

    available = []
    for skill_name, skill_file in discovered.items():
        metadata = read_skill_metadata(skill_file)
        available.append({
            "name": skill_name,
            "description": metadata["description"],
        })

    prompt = (
        "Select only the relevant Agent Skills for this user request.\n\n"
        f"Available skills: {json.dumps(available)}\n"
        f"User request: {state['request']}\n\n"
        "Return valid JSON only in this format:\n"
        '{"skills": [{"name": "skill-name", "reason": "short reason"}]}\n'
        "Use skill names exactly as listed. Do not include unknown names."
    )

    try:
        model = create_gemini_model()
        response = model.invoke(prompt)
        result = extract_json_object(response.content)
        returned_skills = result.get("skills", [])

        if not isinstance(returned_skills, list):
            raise ValueError("Gemini skill result must contain a skills list.")

        selected = {}
        for item in returned_skills:
            if not isinstance(item, dict):
                continue

            name = item.get("name")
            reason = item.get("reason")
            if name in discovered:
                selected[name] = str(reason or "Selected by Gemini.").strip()

    except Exception as error:
        state["errors"].append(f"Gemini skill selection failed: {error}")
        return state

    if not selected:
        state["errors"].append("Gemini skill selection returned no valid skills for the request.")
        return state

    # Preserve required execution dependencies, without replacing Gemini selections.
    if "report-generation" in selected:
        selected.setdefault(
            "sales-analysis",
            "Sales analysis is required to prepare data for the PDF report.",
        )

    if "email-composition" in selected:
        selected.setdefault(
            "sales-analysis",
            "Sales analysis is required to prepare the email summary.",
        )
        selected.setdefault(
            "report-generation",
            "The PDF report is required to compose the manager email draft.",
        )

    # Add dependencies declared in skill frontmatter.
    discovered = discover_skills()

    def add_dependencies(skill_name):
        if skill_name not in discovered:
            return
        metadata = read_skill_execution_metadata(discovered[skill_name])
        for dependency in metadata["requires"]:
            if dependency in discovered:
                selected.setdefault(dependency, f"Required dependency of {skill_name}.")
                add_dependencies(dependency)

    for skill_name in list(selected):
        add_dependencies(skill_name)

    state["selected_skills"] = selected
    return state


def load_skill_instructions(skill_name):
    """Read the full SKILL.md text for a selected skill."""
    skill_file = SKILLS_ROOT / skill_name / "SKILL.md"

    if not skill_file.is_file():
        raise FileNotFoundError(f"Skill instructions not found: {skill_name}")

    return skill_file.read_text(encoding="utf-8")


def generate_business_insights(analysis):
    """Use Gemini for observations while all figures come from Python analysis."""
    fallback = [
        f"{analysis['highest_performing_product']} is the highest-performing product by revenue.",
        f"{analysis['lowest_performing_product']} is the lowest-performing product by revenue.",
    ]

    region_performance = analysis["region_performance"]
    if region_performance:
        strongest_region = max(region_performance, key=lambda name: region_performance[name]["revenue"])
        fallback.append(f"{strongest_region} is the strongest region by revenue.")

    context = json.dumps(analysis, ensure_ascii=False)
    prompt = (
        "Use only the following Python-generated sales analysis as factual context. "
        "Do not calculate, estimate, or invent sales figures.\n"
        f"Sales analysis JSON: {context}\n\n"
        "Write 4 to 7 short business insights covering:\n"
        "1. Key sales observations\n"
        "2. Top-performing products\n"
        "3. Low-performing products\n"
        "4. Regional observations\n"
        "5. Business recommendations\n\n"
        "Return valid JSON only: {\"insights\": [\"insight one\", \"insight two\"]}"
    )

    try:
        model = create_gemini_model()
        response = model.invoke(prompt)
        result = extract_json_object(response.content)
        insights = result.get("insights", [])

        if not isinstance(insights, list):
            raise ValueError("Gemini insights result must contain an insights list.")

        valid_insights = [str(item).strip() for item in insights if str(item).strip()]
        return valid_insights or fallback

    except Exception as error:
        # A Gemini failure must not break deterministic sales reporting.
        return fallback + [f"Gemini insight generation unavailable: {error}"]


def execute_skills(state: BusinessState) -> BusinessState:
    """Load selected skills and execute their scripts generically."""
    selected = state["selected_skills"]
    if not selected:
        if not state["errors"]:
            state["errors"].append("No valid skills were selected or executed.")
        return state

    loaded_instructions = {}
    discovered = discover_skills()

    for skill_name in get_skill_execution_order(discovered, selected):
        if skill_name not in selected:
            continue

        try:
            resources = load_skill_resources(skill_name)
            loaded_instructions[skill_name] = resources["instructions"]
            state["execution_steps"].append(f"Loaded instructions: {skill_name}")
        except Exception as error:
            state["errors"].append(f"Could not load {skill_name}: {error}")

    state["loaded_instructions"] = loaded_instructions

    for skill_name in get_skill_execution_order(discovered, selected):
        if skill_name not in selected:
            continue

        try:
            result = execute_skill_script(skill_name, state)
            if isinstance(result, dict):
                state.update(result)
            state["execution_steps"].append(f"Executed {skill_name}")
        except Exception as error:
            state["errors"].append(f"{skill_name} failed: {error}")

            if skill_name == "sales-analysis":
                break

    return state


def read_skill_execution_metadata(skill_file):
    """Read skill metadata including generic execution dependencies."""
    metadata = read_skill_metadata(skill_file)
    text = skill_file.read_text(encoding="utf-8")

    dependencies = []
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if line.strip().startswith("requires:"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        dependencies = [item.strip() for item in value.split(",")]
    metadata["requires"] = dependencies
    return metadata


def load_skill_resources(skill_name):
    """Load a skill's instructions and inventory its templates and references."""
    skill_root = SKILLS_ROOT / skill_name
    instructions = load_skill_instructions(skill_name)
    templates = sorted(
        str(path.relative_to(skill_root))
        for path in (skill_root / "templates").glob("*")
        if path.is_file()
    )
    references = sorted(
        str(path.relative_to(skill_root))
        for path in (skill_root / "references").glob("*")
        if path.is_file()
    )
    return {
        "instructions": instructions,
        "templates": templates,
        "references": references,
    }


def get_skill_execution_order(discovered, selected):
    """Order selected skills by their declared dependencies."""
    ordered = []
    visiting = set()

    def visit(skill_name):
        if skill_name in ordered or skill_name not in selected:
            return
        if skill_name in visiting:
            return
        visiting.add(skill_name)

        skill_file = discovered[skill_name]
        metadata = read_skill_execution_metadata(skill_file)
        for dependency in metadata["requires"]:
            if dependency in discovered:
                visit(dependency)

        visiting.remove(skill_name)
        ordered.append(skill_name)

    for skill_name in discovered:
        visit(skill_name)

    return ordered


def execute_skill_script(skill_name, state):
    """Load and execute scripts/execute.py from a discovered skill folder."""
    script_file = SKILLS_ROOT / skill_name / "scripts" / "execute.py"
    if not script_file.is_file():
        raise FileNotFoundError(f"Skill execution script not found: {script_file}")

    module_name = f"agent_skill_{skill_name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, script_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load skill execution script: {script_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "execute"):
        raise AttributeError(f"Skill execution script has no execute() function: {script_file}")

    context = {
        "output_dir": OUTPUT_ROOT,
        "generate_business_insights": generate_business_insights,
    }

    return module.execute(state, context)


# Build the graph with exactly two simple nodes.
builder = StateGraph(BusinessState)
builder.add_node("select_skills", select_skills)
builder.add_node("execute_skills", execute_skills)
builder.add_edge(START, "select_skills")
builder.add_edge("select_skills", "execute_skills")
builder.add_edge("execute_skills", END)

sales_workflow = builder.compile()


def run_sales_workflow(request, file_path=None):
    """Run the compiled sales workflow and return the final state."""
    initial_state: BusinessState = {
        "request": request,
        "file_path": str(file_path) if file_path else None,
        "selected_skills": {},
        "loaded_instructions": {},
        "sales_analysis": None,
        "business_insights": [],
        "pdf_path": None,
        "email_draft": None,
        "execution_steps": [],
        "errors": [],
    }
    return sales_workflow.invoke(initial_state)
