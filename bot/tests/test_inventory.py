"""5e-0: inventory safety rules and the self-test, with a fake SharePoint drive.
Every fake call is also checked against graph.py's allow-list."""
import io

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.table import Table

from bot.agent import ItBot
from bot.graph import INVENTORY_SITE_ID, GraphRefused, check_allowed
from bot.identity import IdentityResolver
from bot.inventory import (FOLDER, ROUNDTRIP_FILE, TEST_FILE, InventoryRefused, InventoryStore,
                           roundtrip, selftest, summarise)

S = f"v1.0/sites/{INVENTORY_SITE_ID}/drive"


def make_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock"
    ws.append(["Serial", "Model", "Status", "Notes"])
    ws.append(["SERIAL1", "Inspiron 15 3530", "Available", ""])
    ws.append(["SERIAL2", "Inspiron 15 3530", "Assigned", "User A"])
    ws["F1"] = "=COUNTA(A2:A3)"
    ws.add_table(Table(displayName="tblStock", ref="A1:D3"))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


PARENT_PATH = f"/drives/b!x/root:/Device Support/{FOLDER}"


class FakeDrive:
    def __init__(self, data: bytes, honour_if_match: bool = True):
        self.files = {"f1": {"id": "f1", "name": TEST_FILE, "size": len(data), "file": {}, "eTag": '"{f1},1"',
                             "parentReference": {"id": "folder1", "path": PARENT_PATH}}}
        self.content = {"f1": data}
        self.folder = {"id": "folder1", "name": FOLDER, "folder": {},
                       "parentReference": {"path": "/drives/b!x/root:/Device Support"}}
        self.honour_if_match = honour_if_match
        self.puts = []

    async def get_all(self, path, limit=500):
        check_allowed("GET", path)
        if "/search(" in path:
            return [f for f in self.files.values()]
        if path.endswith("/versions"):
            fid = path.split("/items/")[1].split("/")[0]
            return [{"id": str(i)} for i in range(self.files[fid].get("_v", 1))]
        return []

    async def get(self, path):
        check_allowed("GET", path)
        iid = path.split("/items/")[1]
        return self.folder if iid == "folder1" else self.files[iid]

    async def get_bytes(self, path):
        check_allowed("GET", path)
        return self.content[path.split("/items/")[1].split("/")[0]]

    async def put_bytes(self, path, data, if_match=None):
        check_allowed("PUT", path)
        self.puts.append((path, if_match))
        if ":/" in path:  # new file
            name = path.split(":/")[1].replace("%20", " ")
            self.files["rt"] = {"id": "rt", "name": name, "file": {}, "eTag": '"{rt},1"', "_v": 1,
                                "parentReference": {"id": "folder1", "path": PARENT_PATH}}
            self.content["rt"] = data
            return 201, self.files["rt"]
        fid = path.split("/items/")[1].split("/")[0]
        if self.honour_if_match and if_match != self.files[fid]["eTag"]:
            return 412, {"error": {"code": "resourceModified"}}
        self.files[fid]["_v"] = self.files[fid].get("_v", 1) + 1
        self.content[fid] = data
        return 200, self.files[fid]


def test_allow_list_inventory_paths():
    check_allowed("GET", f"{S}/root/search(q='TEST - Agilify_Asset_Inventory.xlsx')")
    check_allowed("GET", f"{S}/items/abc/content")
    check_allowed("PUT", f"{S}/items/abc/content")
    check_allowed("PUT", f"{S}/items/abc:/TEST%20-%20roundtrip.xlsx:/content")
    for method, path in [
        ("PUT", "v1.0/sites/other.sharepoint.com,1,2/drive/items/abc/content"),   # other site
        ("PUT", f"{S}/items/abc:/script.ps1:/content"),                           # not .xlsx
        ("DELETE", f"{S}/items/abc"),
        ("POST", f"{S}/items/abc/children"),
        ("PATCH", f"{S}/items/abc"),
        ("PUT", "v1.0/devices/abc"),
    ]:
        with pytest.raises(GraphRefused):
            check_allowed(method, path)


def test_roundtrip_keeps_table_and_formula():
    data = make_xlsx()
    before, after = summarise(data), summarise(roundtrip(data))
    assert before["sheets"][0]["tables"] == after["sheets"][0]["tables"]
    assert before["sheets"][0]["tables"][0]["headers"] == ["Serial", "Model", "Status", "Notes"]
    assert after["sheets"][0]["formulas"] == 1


async def test_selftest_all_green():
    drive = FakeDrive(make_xlsx())
    report = await selftest(InventoryStore(drive))
    assert "❌" not in report, report
    assert "tblStock" in report and "HTTP 412" in report
    assert drive.content["f1"] == make_xlsx() or drive.files["f1"].get("_v", 1) == 1  # test copy untouched
    assert all("/items/f1/" not in p for p, _ in drive.puts)                          # never written


async def test_selftest_flags_missing_version_check():
    report = await selftest(InventoryStore(FakeDrive(make_xlsx(), honour_if_match=False)))
    assert "NOT rejected" in report


async def test_upload_rules():
    drive = FakeDrive(make_xlsx())
    store = InventoryStore(drive)
    with pytest.raises(InventoryRefused):
        await store.upload_new("folder1", "Agilify_Asset_Inventory.xlsx", b"x")   # real name in 5e-0
    with pytest.raises(InventoryRefused):
        await store.replace("f1", b"x", "")                                       # no eTag
    drive.files["real"] = {"id": "real", "name": "Agilify_Asset_Inventory.xlsx", "file": {},
                           "parentReference": {"path": PARENT_PATH}}
    with pytest.raises(InventoryRefused):
        await store.replace("real", b"x", '"{real},1"')                            # real file in 5e-0
    assert drive.puts == []


async def test_selftest_command_is_approver_only():
    from bot.tests.fakes import FakeGraph

    graph = FakeGraph({"transitiveMemberOf": [{"id": "s"}]})
    bot = ItBot(graph, IdentityResolver(graph, "a", "s"), None, "dep", inventory=object())
    assert "approvers only" in await bot.handle("u", "selftest inventory", "c")
