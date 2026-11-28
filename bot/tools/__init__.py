"""Fixed tool list. Claude can ONLY act through these. One file per tool.

Each tool module defines:
  SPEC: the Claude tool definition (name, description, input_schema)
  async def run(graph, **kwargs) -> dict
"""
from __future__ import annotations

from types import ModuleType

from . import enrollment_readiness, laptop_status, not_enrolled, person_devices, runbook

TOOLS: dict[str, ModuleType] = {
    m.SPEC["name"]: m
    for m in (laptop_status, person_devices, enrollment_readiness, not_enrolled, runbook)
}


def specs() -> list[dict]:
    return [m.SPEC for m in TOOLS.values()]
