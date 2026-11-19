"""Compatibility exports for the report-generation skill implementation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SKILL_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "report-generation"
    / "scripts"
    / "execute.py"
)
_SPEC = spec_from_file_location("report_generation_skill", _SKILL_SCRIPT)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

generate_sales_report = _MODULE.generate_sales_report
