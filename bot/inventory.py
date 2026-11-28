"""Inventory workbook on the Device Support site (option A: download -> edit -> upload).

Step 5e-0 (this file so far): find, download, summarise and round-trip the
TEST copy, to prove the approach before any real edit. Safety rules enforced
here, on top of graph.py's allow-list:
  - uploads only into the "Device Inventory" folder, only .xlsx files
  - while in 5e-0, uploads only to files whose name starts with "TEST - "
  - replacing a file always sends its eTag (If-Match) so a file changed by
    someone else in the meantime is never overwritten
"""
from __future__ import annotations

import asyncio
import io
import zipfile
from collections import Counter
from urllib.parse import quote

from .graph import INVENTORY_SITE_ID

FOLDER = "Device Inventory"
TEST_FILE = "TEST - Agilify_Asset_Inventory.xlsx"
ROUNDTRIP_FILE = "TEST - roundtrip.xlsx"
TEST_PREFIX = "TEST - "
# The workbook the bot edits. Until step 5f this is the TEST copy (replace() also refuses
# any file not starting with "TEST - "), then it switches to the real one.
TARGET_FILE = TEST_FILE


class InventoryRefused(Exception):
    """An upload that breaks the inventory safety rules. Never sent."""


def _p(rest: str) -> str:
    return f"v1.0/sites/{INVENTORY_SITE_ID}/drive/{rest}"


def _in_folder(item: dict) -> bool:
    return str(item.get("parentReference", {}).get("path", "")).rstrip("/").endswith("/" + FOLDER)


class InventoryStore:
    def __init__(self, graph):
        self.graph = graph

    async def find(self, name: str) -> dict | None:
        """Find a file by exact name inside the Device Inventory folder."""
        try:
            hits = await self.graph.get_all(_p(f"root/search(q='{name.replace(chr(39), chr(39) * 2)}')"), limit=50)
        except Exception:
            hits = []
        for h in hits:
            if h.get("name") == name and "file" in h and _in_folder(h):
                return h
        # Fallback: walk down from the library root (max 3 folder levels).
        folders = [i for i in await self.graph.get_all(_p("root/children")) if "folder" in i]
        for _ in range(3):
            nxt = []
            for f in folders:
                children = await self.graph.get_all(_p(f"items/{f['id']}/children"))
                if f.get("name") == FOLDER:
                    for c in children:
                        if c.get("name") == name and "file" in c:
                            return c
                nxt += [c for c in children if "folder" in c]
            folders = nxt
        return None

    async def item(self, item_id: str) -> dict:
        return await self.graph.get(_p(f"items/{item_id}"))

    async def download(self, item_id: str) -> bytes:
        return await self.graph.get_bytes(_p(f"items/{item_id}/content"))

    async def versions(self, item_id: str) -> int:
        return len(await self.graph.get_all(_p(f"items/{item_id}/versions")))

    async def upload_new(self, parent_id: str, name: str, data: bytes) -> tuple[int, dict]:
        parent = await self.item(parent_id)
        if parent.get("name") != FOLDER or "folder" not in parent:
            raise InventoryRefused(f"uploads only into '{FOLDER}'")
        if not name.endswith(".xlsx") or not name.startswith(TEST_PREFIX):
            raise InventoryRefused("5e-0: only new 'TEST - *.xlsx' files may be created")
        return await self.graph.put_bytes(_p(f"items/{parent_id}:/{quote(name)}:/content"), data)

    async def replace(self, item_id: str, data: bytes, etag: str) -> tuple[int, dict]:
        if not etag:
            raise InventoryRefused("an eTag is required: never overwrite blindly")
        meta = await self.item(item_id)
        if not _in_folder(meta) or not str(meta.get("name", "")).endswith(".xlsx"):
            raise InventoryRefused(f"replace only .xlsx files in '{FOLDER}'")
        if not str(meta.get("name", "")).startswith(TEST_PREFIX):
            raise InventoryRefused("5e-0: only 'TEST - *.xlsx' files may be replaced")
        return await self.graph.put_bytes(_p(f"items/{item_id}/content"), data, if_match=etag)


# ---------- workbook inspection (runs in a worker thread: openpyxl is CPU work)

_PART_KINDS = ("media", "drawings", "charts", "pivotTables", "pivotCache", "comments",
               "threadedComments", "externalLinks", "tables")


def package_parts(data: bytes) -> dict[str, int]:
    """Count the parts inside the .xlsx package (objective before/after comparison)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if not n.endswith(".rels")]
    counts = Counter()
    for n in names:
        for kind in _PART_KINDS:
            if f"/{kind}/" in n or n.startswith(f"xl/{kind}"):
                counts[kind] += 1
    return {k: counts.get(k, 0) for k in _PART_KINDS}


def summarise(data: bytes) -> dict:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data))
    sheets = []
    for ws in wb.worksheets:
        tables = []
        for t in ws.tables.values():
            first_row = ws[t.ref][0]
            tables.append({"name": t.name, "ref": t.ref, "headers": [c.value for c in first_row]})
        formulas = sum(1 for row in ws.iter_rows() for c in row if c.data_type == "f")
        sheets.append({"sheet": ws.title, "tables": tables, "formulas": formulas,
                       "data_validations": len(ws.data_validations.dataValidation),
                       "conditional_formats": sum(1 for _ in ws.conditional_formatting)})
    return {"sheets": sheets, "parts": package_parts(data)}


def roundtrip(data: bytes) -> bytes:
    """Open and save without changes (what every bot edit does around the actual change)."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ---------- 5e-0 self-test (approvers only): touches TEST files only

async def selftest(store: InventoryStore) -> str:
    lines = ["**Inventory self-test (5e-0)**: TEST files only; the real workbook is not touched."]

    def ok(flag: bool, text: str) -> None:
        lines.append(("✅ " if flag else "❌ ") + text)

    item = await store.find(TEST_FILE)
    if not item:
        ok(False, f"1. Find: '{TEST_FILE}' not found in the '{FOLDER}' folder. Upload it there and try again.")
        return "\n\n".join(lines)
    parent_id = item.get("parentReference", {}).get("id")
    ok(True, f"1. Find: {item.get('name')} ({item.get('size', 0) // 1024} KB) in "
             f"`{item.get('parentReference', {}).get('path', '?').split('root:')[-1]}`")

    data = await store.download(item["id"])
    ok(len(data) > 0, f"2. Download with the bot's identity: {len(data) // 1024} KB")

    before = await asyncio.to_thread(summarise, data)
    tables = [f"{t['name']} ({len(t['headers'])} cols)" for s in before["sheets"] for t in s["tables"]]
    ok(bool(tables), f"3. Read: {len(before['sheets'])} sheets, {len(tables)} tables: " + ", ".join(tables))
    for s in before["sheets"]:
        for t in s["tables"]:
            lines.append(f"   • {t['name']} on '{s['sheet']}': " + ", ".join(str(h) for h in t["headers"]))

    new = await asyncio.to_thread(roundtrip, data)
    after = await asyncio.to_thread(summarise, new)
    same_tables = [(t["name"], t["ref"], t["headers"]) for s in before["sheets"] for t in s["tables"]] == \
                  [(t["name"], t["ref"], t["headers"]) for s in after["sheets"] for t in s["tables"]]
    ok(same_tables, "4. Round-trip keeps every table, range and header" if same_tables
       else "4. Round-trip CHANGED tables/headers (see details)")
    lost = {k: (before["parts"][k], after["parts"][k]) for k in before["parts"]
            if before["parts"][k] != after["parts"][k]}
    formulas_b = sum(s["formulas"] for s in before["sheets"])
    formulas_a = sum(s["formulas"] for s in after["sheets"])
    dv_b = sum(s["data_validations"] for s in before["sheets"])
    dv_a = sum(s["data_validations"] for s in after["sheets"])
    cf_b = sum(s["conditional_formats"] for s in before["sheets"])
    cf_a = sum(s["conditional_formats"] for s in after["sheets"])
    ok(not lost and formulas_a == formulas_b and dv_a == dv_b and cf_a == cf_b,
       f"5. Round-trip content: formulas {formulas_b}→{formulas_a}, data validation {dv_b}→{dv_a}, "
       f"conditional formats {cf_b}→{cf_a}, package parts changed: {lost or 'none'}")

    status, body = await store.upload_new(parent_id, ROUNDTRIP_FILE, new)
    ok(status in (200, 201), f"6. Upload new file '{ROUNDTRIP_FILE}': HTTP {status}"
       + ("" if status in (200, 201) else f" {body.get('error', {}).get('code', '')}"))
    if status not in (200, 201):
        return "\n\n".join(lines)

    rt_id, rt_etag = body.get("id"), body.get("eTag")
    status2, body2 = await store.replace(rt_id, new, '"{00000000-0000-0000-0000-000000000000},1"')
    ok(status2 == 412, f"7. Version check: upload with an out-of-date version tag → HTTP {status2} "
                       + ("(rejected, as it should be)" if status2 == 412 else "(NOT rejected: needs a fallback)"))

    status3, body3 = await store.replace(rt_id, new, rt_etag)
    ok(status3 in (200, 201), f"8. Replace with the correct version tag: HTTP {status3}")
    n_versions = await store.versions(rt_id)
    ok(n_versions >= 2, f"9. Version history on '{ROUNDTRIP_FILE}': {n_versions} versions")

    lines.append(f"**Your check:** open '{ROUNDTRIP_FILE}' in Excel next to '{TEST_FILE}' and compare "
                 "(tables, filters, formatting, formulas). You can delete the round-trip file afterwards.")
    return "\n\n".join(lines)
