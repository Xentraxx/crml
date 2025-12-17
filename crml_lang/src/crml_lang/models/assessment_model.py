from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from .control_ref import ControlId, ControlStructuredRef
from .coverage_model import Coverage
from .crml_model import Meta


class Assessment(BaseModel):
    id: ControlId = Field(
        ..., description="Canonical unique control id in the form 'namespace:key' (no whitespace)."
    )
    ref: Optional[ControlStructuredRef] = Field(
        None,
        description=(
            "Optional structured locator for mapping to an external standard (e.g. CIS/ISO). "
            "This is metadata only; referencing should use the canonical 'id'."
        ),
    )

    implementation_effectiveness: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Organization-specific implementation strength for this control. "
            "Semantics: 0.0 = not implemented / no coverage, 1.0 = fully implemented. "
            "This represents vulnerability likelihood (susceptibility) posture used to mitigate a scenario's baseline threat frequency."
        ),
    )

    coverage: Optional[Coverage] = Field(
        None,
        description=(
            "Breadth of deployment/application across the organization. This contributes to vulnerability likelihood reduction "
            "when applying this control to a scenario."
        ),
    )

    reliability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Reliability/uptime of the control as a probability of being effective in a given period.",
    )

    affects: Optional[Literal["frequency", "severity", "both"]] = Field(
        "frequency",
        description=(
            "Which loss component this assessment affects. "
            "Default is 'frequency' (frequency-first). Note: the current reference engine primarily applies controls to frequency (lambda)."
        ),
    )

    question: Optional[str] = Field(
        None,
        description=(
            "Optional assessment prompt/question text for this control (tool/community-defined). "
            "Useful for questionnaires and evidence collection."
        ),
    )

    description: Optional[str] = Field(
        None,
        description=(
            "Optional additional description for this assessment entry (tool/community-defined). "
            "Avoid embedding copyrighted standard text unless you have rights."
        ),
    )

    notes: Optional[str] = Field(None, description="Free-form notes about this assessment entry.")


class AssessmentCataloge(BaseModel):
    id: Optional[str] = Field(
        None, description="Optional identifier for this assessment cataloge (organization-owned)."
    )
    framework: str = Field(
        ..., description="Free-form framework label for humans/tools (e.g. 'CISv8', 'ISO27001:2022')."
    )
    assessed_at: Optional[datetime] = Field(
        None,
        description=(
            "When this assessment cataloge was performed/recorded (ISO 8601 date-time). "
            "Example: '2025-12-17T10:15:30Z'."
        ),
    )
    assessments: List[Assessment] = Field(..., description="List of per-control assessment entries.")


class CRAssessmentSchema(BaseModel):
    crml_assessment: Literal["1.0"] = Field(
        ...,
        validation_alias=AliasChoices("crml_assessment", "crml_control_assessment"),
        serialization_alias="crml_assessment",
        description="Assessment document version identifier.",
    )
    meta: Meta = Field(..., description="Document metadata (name, description, tags, etc.).")
    assessment: AssessmentCataloge = Field(..., description="The assessment cataloge payload.")

    model_config: ConfigDict = ConfigDict(populate_by_name=True)


# Backwards-compatible aliases (deprecated naming)
ControlAssessment = Assessment
ControlAssessmentCataloge = AssessmentCataloge
CRControlAssessmentSchema = CRAssessmentSchema
