"""Compatibility exports for the email-composition skill implementation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_SKILL_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "email-composition"
    / "scripts"
    / "execute.py"
)
_SPEC = spec_from_file_location("email_composition_skill", _SKILL_SCRIPT)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

compose_email = _MODULE.compose_email
