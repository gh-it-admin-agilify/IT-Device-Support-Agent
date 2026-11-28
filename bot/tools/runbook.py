"""Tool: read Agilify's runbooks and knowledge files (repo runbooks/ and knowledge/).

At deploy they are copied into bot/knowledge/; when running from the repo
(tests) they are read from the repo root. Read-only, local files only.
"""
from __future__ import annotations

import re
from pathlib import Path

SPEC = {
    "name": "runbook",
    "description": (
        "Read Agilify's IT runbooks (step-by-step procedures: provision, reset-inspiron, ship, "
        "receive, decommission, re-enroll-lost-record) and knowledge files (glossary, fleet, "
        "tenant-setup, troubleshooting, decisions). Call with no name to list them, or with "
        "a name to get the full text. Use the runbook as the source of truth for procedures "
        "and walk the person through it ONE step at a time."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "e.g. 'reset-inspiron' or 'glossary'; omit to list"}},
    },
}

_NAME = re.compile(r"^[a-z0-9-]{1,40}$")


def _base() -> Path:
    deployed = Path(__file__).resolve().parents[1] / "knowledge"
    return deployed if deployed.is_dir() else Path(__file__).resolve().parents[2]


def _docs() -> dict[str, tuple[str, Path]]:
    docs: dict[str, tuple[str, Path]] = {}
    for kind in ("runbooks", "knowledge"):
        folder = _base() / kind
        if folder.is_dir():
            for f in sorted(folder.glob("*.md")):
                if f.stem.lower() != "readme":
                    docs[f.stem.lower()] = (kind, f)
    return docs


def _title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return path.stem


async def run(graph, name: str | None = None) -> dict:
    docs = _docs()
    if not name:
        return {kind: [{"name": n, "title": _title(p)} for n, (k, p) in docs.items() if k == kind]
                for kind in ("runbooks", "knowledge")}
    key = name.strip().lower().removesuffix(".md")
    if not _NAME.match(key) or key not in docs:
        return {"error": f"No runbook or knowledge file called '{name}'.", "available": sorted(docs)}
    kind, path = docs[key]
    return {"name": key, "kind": kind, "text": path.read_text(encoding="utf-8")[:40000]}
