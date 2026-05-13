"""Pydantic models for cross-module handoff rows (Module B → Module C)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AllocationHandshakeRow(BaseModel):
    """Subset of allocation_output aligned with ``reports/module_b_module_c_handshake.md``."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    department: str
    channel: str
    week_index: int = Field(ge=1, le=60)
    iso_week: str
    budget_allocation_usd: float = Field(ge=0.0)
    expected_contacts: float
    persuasion_adjusted_contacts: float
    scenario_id: str
    reach_cap_population_proxy: float = Field(ge=0.0)
