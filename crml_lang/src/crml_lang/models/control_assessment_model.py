"""Legacy import path for the assessment model.

This module is kept for backwards compatibility. New code should import from
`crml_lang.models.assessment_model`.
"""

from .assessment_model import (  # noqa: F401
    Assessment,
    AssessmentCataloge,
    CRAssessmentSchema,
    ControlAssessment,
    ControlAssessmentCataloge,
    CRControlAssessmentSchema,
)
