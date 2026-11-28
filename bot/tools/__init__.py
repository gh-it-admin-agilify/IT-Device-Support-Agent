"""Fixed tool list. Claude can ONLY act through these. One file per tool.

Each tool module defines:
  SPEC: the Claude tool definition (name, description, input_schema)
  async def run(graph, **kwargs) -> dict
"""
from __future__ import annotations

from types import ModuleType

from . import laptop_status

TOOLS: dict[str, ModuleType] = {
    laptop_status.SPEC["name"]: laptop_status,
}


def specs() -> list[dict]:
    return [m.SPEC for m in TOOLS.values()]
