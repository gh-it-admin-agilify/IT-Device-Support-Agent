"""5e-1a: Inventory Refresh (plan, preview, apply), the 'yes' flow, and the typing loop."""
import asyncio
import io
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.table import Table

from bot import refresh
from bot.agent import ItBot
from bot.app import keep_typing
from bot.identity import IdentityResolver
from bot.tests.fakes import FakeGraph

NOW = datetime(2026, 11, 28, 12, 0)
H_IN = ["Device name", "Serial", "Manufacturer", "Model", "Category", "Primary user UPN", "Primary user",
        "User account", "Devices for user", "Compliance", "OS version", "Encrypted", "Enrolled", "Last check-in",
        "Days since check-in", "Stale 90+ days", "Autopilot user", "Autopilot user matches", "Notes"]
H_AP = ["Serial", "Model", "Autopilot user", "User account", "Autopilot state", "Entra device", "Entra last sign-in",
        "Entra says managed", "Where is it (from workbook)", "Assessment / next step"]
H_ST = ["Serial", "Type", "Make", "Model", "CPU", "RAM", "Disk", "Specs source", "Location", "New/Used",
        "Confirmed", "Status", "Intune now", "Autopilot user now", "Original note"]
H_DE = ["Serial", "Make", "Model", "Reason", "Last user", "Confirmed", "In Autopilot", "In Intune", "In Entra",
        "Next steps"]
H_UN = ["Serial", "Model", "Location"]
RED = PatternFill("solid", fgColor="FFC7CE")


def _sheet(wb, title, name, headers, rows, first=False):
    ws = wb.active if first else wb.create_sheet(title)
    ws.title = title
    ws.append(headers)
    for r in rows:
        ws.append(r)
    end = 1 + max(len(rows), 1)
    from openpyxl.utils import get_column_letter
    ws.add_table(Table(displayName=name, ref=f"A1:{get_column_letter(len(headers))}{end}"))
    return ws


def make_workbook() -> bytes:
    wb = Workbook()
    s1 = ["AGY-U-S1", "S1"] + [""] * 12 + ["=TODAY()-N2"] + ["", "", "", "note S1"]
    _sheet(wb, "Intune Devices", "tblIntuneDevices", H_IN, [s1], first=True)
    _sheet(wb, "Autopilot Not in Intune", "tblAutopilotNotInIntune", H_AP,
           [["AP1", "Inspiron", "", "", "notContacted", "", None, "", "", "check with HR"]])
    st = _sheet(wb, "Stock", "tblStock", H_ST,
                [["S1"] + [""] * 10 + ["Assigned", "", "", ""], ["ST2"] + [""] * 10 + ["Available", "", "", "red"]])
    for c in range(1, 16):
        st.cell(3, c).fill = RED
    _sheet(wb, "Decommissioning", "tblDecommissioning", H_DE, [["D1", "Dell", "Vostro", "old"] + [""] * 6])
    _sheet(wb, "Unaccounted Laptops", "tblUnaccounted", H_UN, [["AP2", "Vostro", "Houston office"]])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


SRC = {
    "intune": [
        {"deviceName": "AGY-U-S1", "serialNumber": "S1", "manufacturer": "Dell", "model": "Inspiron",
         "userPrincipalName": "a@x.com", "userDisplayName": "User A", "complianceState": "compliant",
         "isEncrypted": True, "lastSyncDateTime": "2026-11-26T10:00:00Z", "enrolledDateTime": "2026-11-25T21:30:00Z"},
        {"deviceName": "AGY-U-S2", "serialNumber": "S2", "manufacturer": "Dell", "model": "Pro 16",
         "userPrincipalName": "", "complianceState": "noncompliant", "isEncrypted": False,
         "lastSyncDateTime": "2026-11-27T10:00:00Z"},
    ],
    "autopilot": [{"serialNumber": "S1", "userPrincipalName": "a@x.com"},
                  {"serialNumber": "AP1", "model": "Inspiron", "enrollmentState": "notContacted",
                   "azureActiveDirectoryDeviceId": "e-ap1"},
                  {"serialNumber": "AP2", "model": "Vostro", "enrollmentState": "notContacted"}],
    "entra": [{"deviceId": "e-ap1", "displayName": "AGY-U-AP1", "isManaged": False}],
    "users": [{"userPrincipalName": "a@x.com", "accountEnabled": True}],
}


def test_plan_and_preview():
    plan = refresh.plan_refresh(make_workbook(), SRC, NOW)
    assert [r["Serial"] for r in plan.intune_rows] == ["S1", "S2"]
    assert plan.new_serials["tblIntuneDevices"] == ["S2"]
    assert [r["Serial"] for r in plan.autopilot_rows] == ["AP1", "AP2"]
    assert plan.remove["tblStock"] == [{"serial": "S1", "why": "in use by User A, last check-in 2026-11-26"}]
    assert plan.remove["tblDecommissioning"] == []
    text = refresh.preview(plan)
    assert "Intune Devices (rebuilt)**: 2 rows (was 1)" in text and "S1 (in use by User A" in text


def test_apply_keeps_notes_formulas_styles_and_logs():
    data = make_workbook()
    plan = refresh.plan_refresh(data, SRC, NOW)
    new, summary = refresh.apply_plan(data, plan, "Felix", NOW)
    wb = load_workbook(io.BytesIO(new))
    ws = wb["Intune Devices"]
    assert ws.tables["tblIntuneDevices"].ref == "A1:S3"
    assert ws["S2"].value == "note S1"                  # Notes kept by serial
    assert ws["O2"].value == "=TODAY()-N2" and ws["O3"].value == "=TODAY()-N3"  # formula translated
    assert ws["L2"].value == "Yes" and ws["H2"].value == "Enabled" and ws["I2"].value == 1
    ap = wb["Autopilot Not in Intune"]
    assert ap["J2"].value == "check with HR"            # assessment kept
    assert ap["I3"].value == "Unaccounted: Houston office"  # where-is-it for a new row
    assert ap["F2"].value == "AGY-U-AP1"
    st = wb["Stock"]
    assert st.tables["tblStock"].ref == "A1:O2"
    assert st["A2"].value == "ST2" and st["O2"].value == "red" and st["A2"].fill.fgColor.rgb.endswith("FFC7CE")
    assert st["A3"].value is None
    log = wb["Change Log"]
    rows = [[c.value for c in r] for r in log.iter_rows(min_row=2)]
    assert ["tblStock", "S1", "(row removed)"] == rows[-1][2:5]
    assert len(rows) == 3 and log.tables["tblChangeLog"].ref == "A1:G4"
    assert "1 in-use laptop(s) removed" in summary


def test_growing_into_used_cells_is_blocked():
    wb = load_workbook(io.BytesIO(make_workbook()))
    wb["Intune Devices"]["A5"] = "something below the table"
    out = io.BytesIO()
    wb.save(out)
    data = out.getvalue()
    src = dict(SRC, intune=SRC["intune"] + [dict(SRC["intune"][1], serialNumber=f"X{i}", deviceName=f"X{i}")
                                            for i in range(3)])
    plan = refresh.plan_refresh(data, src, NOW)
    try:
        refresh.apply_plan(data, plan, "Felix", NOW)
        assert False, "should have been blocked"
    except refresh.RefreshBlocked as exc:
        assert "A5" in str(exc)


def test_same_person_matching():
    sp = refresh.same_person
    assert sp("Adrienne Streater", "adrienne.streater@x.com", "Adrienne Streater")
    assert sp("adrienne.streater@x.com", "adrienne.streater@x.com", "Adrienne Streater")
    assert sp("adrienne.streater", "adrienne.streater@x.com", "Adrienne Streater")
    assert sp("Adrienne", "adrienne.streater@x.com", "Adrienne Streater")
    assert not sp("Sara Yates", "adrienne.streater@x.com", "Adrienne Streater")
    assert not sp("", "adrienne.streater@x.com", "Adrienne Streater")


def test_decommissioning_keeps_laptops_still_with_their_last_user():
    wb = load_workbook(io.BytesIO(make_workbook()))
    ws = wb["Decommissioning"]
    rows = [["OLD1", "Dell", "Vostro", "replaced", "Adrienne Streater"],   # still with Adrienne -> keep
            ["OLD2", "Dell", "Vostro", "replaced", "Sara Yates"],          # now used by Adrienne -> remove
            ["OLD3", "Dell", "Vostro", "replaced", ""]]                    # last user unknown -> keep, flag
    for i, r in enumerate(rows, start=3):
        for j, v in enumerate(r, start=1):
            ws.cell(i, j).value = v
    ws.tables["tblDecommissioning"].ref = "A1:J5"
    out = io.BytesIO()
    wb.save(out)
    adrienne = {"userPrincipalName": "adrienne.streater@x.com", "userDisplayName": "Adrienne Streater",
                "lastSyncDateTime": "2026-11-28T08:00:00Z", "deviceName": "x"}
    src = dict(SRC, intune=SRC["intune"] + [dict(adrienne, serialNumber=s) for s in ("OLD1", "OLD2", "OLD3")])
    plan = refresh.plan_refresh(out.getvalue(), src, NOW)
    assert [r["serial"] for r in plan.remove["tblDecommissioning"]] == ["OLD2"]
    assert "re-deployed" in plan.remove["tblDecommissioning"][0]["why"]
    kept = {r["serial"]: r["why"] for r in plan.kept["tblDecommissioning"]}
    assert "still with Adrienne Streater" in kept["OLD1"] and "please check" in kept["OLD3"]
    text = refresh.preview(plan)
    assert "Kept in Decommissioning" in text and "OLD2 (re-deployed" in text


# ---- the agent flow: preview -> "yes" -> save with eTag


class FakeStore:
    def __init__(self, data):
        self.data, self.etag, self.saved = data, '"{f},1"', []

    async def find(self, name):
        return {"id": "f", "name": name}

    async def item(self, _):
        return {"eTag": self.etag}

    async def download(self, _):
        return self.data

    async def replace(self, _, data, etag):
        if etag != self.etag:
            return 412, {}
        self.saved.append(data)
        self.data, self.etag = data, '"{f},2"'
        return 200, {}


class SrcGraph(FakeGraph):
    async def get_all(self, path, limit=500):
        await super().get_all(path, limit)  # allow-list check
        for key, val in (("transitiveMemberOf", [{"id": "s"}]), ("managedDevices", SRC["intune"]),
                         ("windowsAutopilot", SRC["autopilot"]), ("v1.0/devices", SRC["entra"]),
                         ("v1.0/users", SRC["users"])):
            if key in path:
                return val
        return []


def _bot():
    g = SrcGraph({})
    store = FakeStore(make_workbook())
    return ItBot(g, IdentityResolver(g, "a", "s"), None, "dep", inventory=store), store


async def test_refresh_needs_yes_and_saves_once():
    bot, store = _bot()
    notes = []

    async def notify(t):
        notes.append(t)

    preview = await bot.handle("u", "Inventory Refresh", "c", who="Tech", notify=notify)
    assert "preview" in preview and "Type **yes**" in preview and store.saved == []
    assert any("step 1 of 3" in n for n in notes)
    assert (await bot.handle("u", "yes", "c", who="Tech", notify=notify)).startswith("✅ Inventory refreshed")
    assert len(store.saved) == 1


async def test_anything_but_yes_cancels():
    bot, store = _bot()
    await bot.handle("u", "inventory refresh", "c")
    bot.claude = None
    reply = await bot.handle("u", "reset", "c")
    assert "cancelled" in reply and store.saved == []
    assert "Type **yes**" not in await bot.handle("u", "reset", "c")


async def test_keep_typing_sends_indicator_and_one_still_working():
    sent = []

    async def send(t):
        sent.append(t)

    done = asyncio.Event()
    task = asyncio.create_task(keep_typing(send, done, every=0.01, still_after=0.03))
    await asyncio.sleep(0.08)
    done.set()
    await task
    assert sent.count(None) >= 3 and sum(1 for s in sent if s) == 1
