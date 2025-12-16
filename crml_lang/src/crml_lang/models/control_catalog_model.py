from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from .control_ref import ControlId, ControlStructuredRef
from .crml_model import Meta


class ControlCatalogEntry(BaseModel):
    """Portable metadata about a control id.

    Important: do not embed copyrighted standard text here.
    Keep this to identifiers and tool-friendly metadata.
    """

    id: ControlId
    ref: Optional[ControlStructuredRef] = None
    title: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None


class ControlCatalogPack(BaseModel):
    id: Optional[str] = None
    # Free-form label for humans/tools (e.g. "CIS v8", "ISO 27001:2022").
    framework: str
    controls: List[ControlCatalogEntry]


class CRControlCatalogSchema(BaseModel):
    crml_control_catalog: Literal["1.0"]
    meta: Meta
    catalog: ControlCatalogPack

    model_config: ConfigDict = ConfigDict(populate_by_name=True)
