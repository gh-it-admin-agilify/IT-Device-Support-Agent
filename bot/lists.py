"""SharePoint lists (migration step L0): prove the bot can create, update and delete list ROWS
with its one-site permission, and that the per-row version check (If-Match -> 412) works.

Safety rules on top of graph.py's allow-list (which already limits the bot to list ITEMS on
the Device Support site - never lists, columns or permissions):
  - during L0 the bot only touches lists whose name starts with "TEST - "
  - updates and deletes always send the row's eTag, so a row someone else changed is never overwritten
"""
from __future__ import annotations

from datetime import datetime, timezone

from .graph import INVENTORY_SITE_ID

TEST_LIST = "TEST - Lists"
TEST_PREFIX = "TEST - "


class ListRefused(Exception):
    """A list change that breaks the safety rules. Never sent."""


def _p(rest: str) -> str:
    return f"v1.0/sites/{INVENTORY_SITE_ID}/{rest}"


class ListStore:
    def __init__(self, graph):
        self.graph = graph

    async def find_list(self, name: str) -> dict | None:
        for lst in await self.graph.get_all(_p("lists?$select=id,displayName,list"), limit=2000):
            if lst.get("displayName") == name:
                return lst
        return None

    def _check(self, lst: dict) -> None:
        if not str(lst.get("displayName", "")).startswith(TEST_PREFIX):
            raise ListRefused("L0: only lists named 'TEST - …' may be changed")

    async def get_item(self, lst: dict, item_id: str) -> dict:
        return await self.graph.get(_p(f"lists/{lst['id']}/items/{item_id}?$expand=fields"))

    async def add(self, lst: dict, fields: dict) -> tuple[int, dict]:
        self._check(lst)
        return await self.graph.send_json("POST", _p(f"lists/{lst['id']}/items"), {"fields": fields})

    async def update(self, lst: dict, item_id: str, fields: dict, etag: str) -> tuple[int, dict]:
        self._check(lst)
        if not etag:
            raise ListRefused("an eTag is required: never overwrite a row blindly")
        return await self.graph.send_json("PATCH", _p(f"lists/{lst['id']}/items/{item_id}/fields"),
                                          fields, if_match=etag)

    async def delete(self, lst: dict, item_id: str, etag: str) -> tuple[int, dict]:
        self._check(lst)
        if not etag:
            raise ListRefused("an eTag is required: never delete a row blindly")
        return await self.graph.send_json("DELETE", _p(f"lists/{lst['id']}/items/{item_id}"), if_match=etag)

    async def versions(self, lst: dict, item_id: str) -> int:
        return len(await self.graph.get_all(_p(f"lists/{lst['id']}/items/{item_id}/versions")))


async def selftest(store: ListStore) -> str:
    lines = [f"**List self-test (L0)**: only the list '{TEST_LIST}' is touched; one test row is "
             "created, changed and deleted again."]

    def ok(flag: bool, text: str) -> None:
        lines.append(("✅ " if flag else "❌ ") + text)

    def err(body: dict) -> str:
        return str(body.get("error", {}).get("code", "")) if isinstance(body, dict) else ""

    lst = await store.find_list(TEST_LIST)
    if not lst:
        ok(False, f"1. Find: no list called '{TEST_LIST}' on the Device Support site. Create it and try again.")
        return "\n\n".join(lines)
    ok(True, f"1. Find list '{TEST_LIST}'")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    status, item = await store.add(lst, {"Title": f"SELFTEST {stamp}"})
    ok(status in (200, 201), f"2. Create a row: HTTP {status} {err(item)}")
    if status not in (200, 201):
        return "\n\n".join(lines)
    item_id, etag1 = item.get("id"), item.get("eTag")

    status, body = await store.update(lst, item_id, {"Title": f"SELFTEST {stamp} (updated)"}, etag1)
    ok(status == 200, f"3. Update the row with its version tag: HTTP {status} {err(body)}")

    status, body = await store.update(lst, item_id, {"Title": "SHOULD NOT SAVE"}, etag1)  # etag1 is now stale
    ok(status == 412, f"4. Update with an out-of-date version tag → HTTP {status} "
                      + ("(rejected, as it should be)" if status == 412 else "(NOT rejected: needs a fallback)"))

    fresh = await store.get_item(lst, item_id)
    title = fresh.get("fields", {}).get("Title")
    ok(title == f"SELFTEST {stamp} (updated)", f"5. Read back: Title = '{title}'")
    n = await store.versions(lst, item_id)
    ok(n >= 2, f"6. Row version history: {n} versions")

    status, body = await store.delete(lst, item_id, fresh.get("eTag", ""))
    ok(status in (200, 204), f"7. Delete the test row with its version tag: HTTP {status} {err(body)}")
    lines.append("If all are ✅, SharePoint Lists work for the bot exactly as the migration plan needs.")
    return "\n\n".join(lines)
