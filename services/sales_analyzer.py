"""Compatibility exports for the sales-analysis skill implementation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SKILL_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "sales-analysis"
    / "scripts"
    / "execute.py"
)
_SPEC = spec_from_file_location("sales_analysis_skill", _SKILL_SCRIPT)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

load_sales_data = _MODULE.load_sales_data
validate_sales_data = _MODULE.validate_sales_data
analyze_sales_data = _MODULE.analyze_sales_data
