"""`Inventory Refresh`: rebuild the Intune-derived tables and clean up in-use laptops.

Approved 2026-11-28:
  1. tblIntuneDevices        rebuilt from Intune (Notes and other hand-written columns kept by serial)
  2. tblAutopilotNotInIntune rebuilt (Autopilot records with no Intune record; hand-written columns kept)
  3. tblDecommissioning      rows REMOVED only when the laptop is in use by SOMEONE OTHER than its
                             "Last user" (re-deployed); still with its last user = kept (fix 2026-11-28)
  4. tblStock                rows REMOVED when the laptop is in use
  5. tblChangeLog            one row per removal + a summary row per rebuilt table
"In use" = in Intune, has a primary user, last check-in within IN_USE_DAYS days.
These two removals are the ONLY deletions the bot ever makes; always previewed and confirmed.

Column data follows scripts/local/devices/Export-DeviceInventory.ps1 (same Graph reads).
Columns that hold formulas keep their formulas (translated to each row).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone

IN_USE_DAYS = 30
T_INTUNE, T_AP, T_STOCK, T_DECOM, T_UNACC = (
    "tblIntuneDevices", "tblAutopilotNotInIntune", "tblStock", "tblDecommissioning", "tblUnaccounted")
CHANGELOG_SHEET, T_LOG = "Change Log", "tblChangeLog"
LOG_HEADERS = ["When (UTC)", "Who", "Table", "Serial", "Column", "Old value", "New value"]


class RefreshBlocked(Exception):
    """The workbook layout doesn't allow a safe refresh. Nothing is saved."""


# ---------------------------------------------------------------- Graph reads

async def gather(graph) -> dict:
    md = await graph.get_all(
        "beta/deviceManagement/managedDevices?$select=id,deviceName,lastSyncDateTime,enrolledDateTime,osVersion,"
        "serialNumber,manufacturer,model,deviceCategoryDisplayName,userPrincipalName,userDisplayName,"
        "complianceState,managedDeviceOwnerType,isEncrypted", limit=5000)
    ap = await graph.get_all("beta/deviceManagement/windowsAutopilotDeviceIdentities", limit=5000)
    ent = await graph.get_all(
        "v1.0/devices?$select=deviceId,displayName,accountEnabled,isManaged,operatingSystem,"
        "approximateLastSignInDateTime", limit=10000)
    users = await graph.get_all("v1.0/users?$select=userPrincipalName,displayName,accountEnabled,jobTitle",
                                limit=10000)
    return {"intune": md, "autopilot": ap, "entra": ent, "users": users}


# ---------------------------------------------------------------- helpers

def _dt(value) -> datetime | None:
    if not value or str(value).startswith("0001-"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _key(serial) -> str:
    return str(serial or "").strip().upper()


def _find_table(wb, name):
    for ws in wb.worksheets:
        if name in ws.tables:
            return ws, ws.tables[name]
    raise RefreshBlocked(f"table {name} not found in the workbook")


def _bounds(ref: str):
    from openpyxl.utils.cell import range_boundaries
    return range_boundaries(ref)  # min_col, min_row, max_col, max_row


def read_table(wb, name) -> tuple[list[str], list[dict]]:
    ws, t = _find_table(wb, name)
    c1, r1, c2, r2 = _bounds(t.ref)
    headers = [ws.cell(r1, c).value for c in range(c1, c2 + 1)]
    rows = []
    for r in range(r1 + 1, r2 + 1 - (t.totalsRowCount or 0)):
        vals = [ws.cell(r, c).value for c in range(c1, c2 + 1)]
        if any(v not in (None, "") for v in vals):
            rows.append(dict(zip(headers, vals)))
    return headers, rows


# ---------------------------------------------------------------- the plan

@dataclass
class Plan:
    intune_rows: list[dict] = field(default_factory=list)
    autopilot_rows: list[dict] = field(default_factory=list)
    remove: dict[str, list[dict]] = field(default_factory=dict)  # table -> [{serial, why}]
    kept: dict[str, list[dict]] = field(default_factory=dict)    # in use but deliberately kept (shown in preview)
    old_counts: dict[str, int] = field(default_factory=dict)
    new_serials: dict[str, list[str]] = field(default_factory=dict)
    gone_serials: dict[str, list[str]] = field(default_factory=dict)


def plan_refresh(data: bytes, src: dict, now: datetime | None = None) -> Plan:
    from openpyxl import load_workbook

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    wb = load_workbook(io.BytesIO(data))
    users = {str(u.get("userPrincipalName", "")).lower(): u for u in src["users"]}
    ap_by = {_key(a.get("serialNumber")): a for a in src["autopilot"]}
    ent_by = {str(e.get("deviceId", "")).lower(): e for e in src["entra"]}
    md = [m for m in src["intune"] if m.get("serialNumber")]
    md_by = {_key(m["serialNumber"]): m for m in md}
    per_user: dict[str, int] = {}
    for m in md:
        upn = str(m.get("userPrincipalName") or "").lower()
        if upn:
            per_user[upn] = per_user.get(upn, 0) + 1

    def account(upn):
        if not upn:
            return ""
        u = users.get(str(upn).lower())
        return "Not found" if u is None else ("Enabled" if u.get("accountEnabled") else "Disabled")

    plan = Plan()

    # 1. Intune devices (hand-written columns kept by serial)
    _, old_in = read_table(wb, T_INTUNE)
    old_in_by = {_key(r.get("Serial")): r for r in old_in}
    plan.old_counts[T_INTUNE] = len(old_in)
    for m in sorted(md, key=lambda m: str(m.get("deviceName") or "").lower()):
        s = _key(m["serialNumber"])
        last = _dt(m.get("lastSyncDateTime"))
        days = (now - last).days if last else None
        a = ap_by.get(s)
        ap_user = (a or {}).get("userPrincipalName") or ""
        upn = m.get("userPrincipalName") or ""
        row = {
            "Device name": m.get("deviceName"), "Serial": s, "Manufacturer": m.get("manufacturer"),
            "Model": m.get("model"), "Category": m.get("deviceCategoryDisplayName") or "",
            "Primary user UPN": upn, "Primary user": m.get("userDisplayName") or "",
            "User account": account(upn), "Devices for user": per_user.get(upn.lower(), 0) if upn else "",
            "Compliance": m.get("complianceState"), "OS version": m.get("osVersion"),
            "Encrypted": bool(m.get("isEncrypted")), "Enrolled": _dt(m.get("enrolledDateTime")),
            "Last check-in": last, "Days since check-in": days,
            "Stale 90+ days": (days is not None and days >= 90),
            "Autopilot user": ap_user,
            "Autopilot user matches": ("" if a is None else bool(ap_user) and ap_user.lower() == upn.lower()),
        }
        row["_keep"] = old_in_by.get(s, {})
        plan.intune_rows.append(row)
    new_in = {_key(r["Serial"]) for r in plan.intune_rows}
    plan.new_serials[T_INTUNE] = sorted(new_in - set(old_in_by))
    plan.gone_serials[T_INTUNE] = sorted(set(old_in_by) - new_in)

    # Where is a laptop according to the workbook (for new Autopilot-not-in-Intune rows)
    where: dict[str, str] = {}
    for tname, fmt in ((T_UNACC, "Unaccounted: {Location}"), (T_DECOM, "Decommissioning: {Reason}"),
                       (T_STOCK, "Stock: {Status}, {Location}")):
        try:
            _, rows = read_table(wb, tname)
        except RefreshBlocked:
            continue
        for r in rows:
            vals = {k: (v if v not in (None, "") else "?") for k, v in r.items() if isinstance(k, str)}
            try:
                where[_key(r.get("Serial"))] = fmt.format(**vals)
            except KeyError:
                where[_key(r.get("Serial"))] = tname

    # 2. Autopilot not in Intune
    _, old_ap = read_table(wb, T_AP)
    old_ap_by = {_key(r.get("Serial")): r for r in old_ap}
    plan.old_counts[T_AP] = len(old_ap)
    for s, a in sorted(ap_by.items()):
        if not s or s in md_by:
            continue
        e = ent_by.get(str(a.get("azureActiveDirectoryDeviceId") or "").lower())
        row = {
            "Serial": s, "Model": a.get("model"), "Autopilot user": a.get("userPrincipalName") or "",
            "User account": account(a.get("userPrincipalName")), "Autopilot state": a.get("enrollmentState"),
            "Entra device": (e or {}).get("displayName") or ("" if e else "Not found"),
            "Entra last sign-in": _dt((e or {}).get("approximateLastSignInDateTime")),
            "Entra says managed": ("" if e is None else bool(e.get("isManaged"))),
        }
        keep = dict(old_ap_by.get(s, {}))
        if not keep.get("Where is it (from workbook)") and s in where:
            keep["Where is it (from workbook)"] = where[s]
        row["_keep"] = keep
        plan.autopilot_rows.append(row)
    new_ap = {r["Serial"] for r in plan.autopilot_rows}
    plan.new_serials[T_AP] = sorted(new_ap - set(old_ap_by))
    plan.gone_serials[T_AP] = sorted(set(old_ap_by) - new_ap)

    # 3 + 4. In-use laptops leave Stock. In Decommissioning a laptop is normally still with its
    # last user until it's shipped back, so it leaves only when SOMEONE ELSE uses it (re-deployed).
    def in_use(s):
        m = md_by.get(s)
        if not m or not m.get("userPrincipalName"):
            return None
        last = _dt(m.get("lastSyncDateTime"))
        if not last or (now - last).days > IN_USE_DAYS:
            return None
        return m, f"in use by {m.get('userDisplayName') or m['userPrincipalName']}, last check-in {last:%Y-%m-%d}"

    _, stock = read_table(wb, T_STOCK)
    plan.old_counts[T_STOCK] = len(stock)
    plan.remove[T_STOCK] = [{"serial": _key(r.get("Serial")), "why": u[1]}
                            for r in stock if (u := in_use(_key(r.get("Serial"))))]

    _, decom = read_table(wb, T_DECOM)
    plan.old_counts[T_DECOM] = len(decom)
    plan.remove[T_DECOM], plan.kept[T_DECOM] = [], []
    for r in decom:
        s = _key(r.get("Serial"))
        u = in_use(s)
        if not u:
            continue
        m, why = u
        if same_person(r.get("Last user"), m.get("userPrincipalName"), m.get("userDisplayName")):
            plan.kept[T_DECOM].append({"serial": s, "why": f"still with {m.get('userDisplayName') or m['userPrincipalName']}"
                                                         " (its last user, not yet returned)"})
        elif not str(r.get("Last user") or "").strip():
            plan.kept[T_DECOM].append({"serial": s, "why": f"{why}; 'Last user' is empty, so I can't tell "
                                                         "whether it was re-deployed: please check"})
        else:
            plan.remove[T_DECOM].append({"serial": s, "why": f"re-deployed: {why} (last user was {r.get('Last user')})"})
    return plan


def _norm(text) -> str:
    return " ".join(str(text or "").lower().replace(".", " ").replace("_", " ").replace("-", " ").split())


def same_person(last_user, upn, display) -> bool:
    """Does the workbook's 'Last user' (name, email or alias, typed by hand) mean this Intune user?"""
    lu = _norm(str(last_user or "").split("@")[0] if "@" in str(last_user or "") else last_user)
    if not lu:
        return False
    names = {_norm(display), _norm(str(upn or "").split("@")[0])} - {""}
    if lu in names:
        return True
    for n in names:  # e.g. "Adrienne" or "Adrienne Streater (Sales)" vs "Adrienne Streater"
        tokens = n.split()
        if tokens and all(t in lu.split() for t in tokens):
            return True
        if lu and set(lu.split()) <= set(tokens):
            return True
    return False


def preview(plan: Plan) -> str:
    def chg(t, label):
        n_old, n_new = plan.old_counts.get(t, 0), len(plan.intune_rows if t == T_INTUNE else plan.autopilot_rows)
        add, gone = plan.new_serials.get(t, []), plan.gone_serials.get(t, [])
        extra = "; ".join(x for x in (
            f"new: {', '.join(add[:10])}{'…' if len(add) > 10 else ''}" if add else "",
            f"gone: {', '.join(gone[:10])}{'…' if len(gone) > 10 else ''}" if gone else "") if x)
        return f"• **{label}**: {n_new} rows (was {n_old})" + (f" ({extra})" if extra else "")

    lines = ["**Inventory Refresh: preview**", chg(T_INTUNE, "Intune Devices (rebuilt)"),
             chg(T_AP, "Autopilot Not in Intune (rebuilt)")]
    for t, label in ((T_STOCK, "Remove from Stock"), (T_DECOM, "Remove from Decommissioning")):
        rem = plan.remove.get(t, [])
        lines.append(f"• **{label}**: " + ("none" if not rem else
                     "; ".join(f"{r['serial']} ({r['why']})" for r in rem)))
        kept = plan.kept.get(t, [])
        if kept:
            lines.append(f"• **Kept in Decommissioning**: " + "; ".join(f"{r['serial']} ({r['why']})" for r in kept))
    lines.append("Notes and other hand-written columns are kept. Every change goes into the Change Log, "
                 "and SharePoint keeps the previous version.")
    return "\n\n".join(lines)


# ---------------------------------------------------------------- applying

def _coerce(value, samples: list):
    if isinstance(value, bool):
        if any(isinstance(s, bool) for s in samples):
            return value
        low = {str(s).strip().lower() for s in samples if isinstance(s, str) and s.strip()}
        if low and low <= {"true", "false"}:
            return "TRUE" if value else "FALSE"
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        if samples and not any(isinstance(s, datetime) for s in samples) and \
                any(isinstance(s, str) for s in samples):
            return value.strftime("%Y-%m-%d %H:%M")
        return value
    return value


def write_table(wb, name: str, rows: list[dict]) -> None:
    """Replace a table's data rows. Formula columns keep their (translated) formulas,
    styles come from the first data row, the table range is resized."""
    from copy import copy

    from openpyxl.formula.translate import Translator
    from openpyxl.utils import get_column_letter

    ws, t = _find_table(wb, name)
    if t.totalsRowCount:
        raise RefreshBlocked(f"{name} has a totals row; refresh not supported")
    c1, r1, c2, r2 = _bounds(t.ref)
    headers = [ws.cell(r1, c).value for c in range(c1, c2 + 1)]
    first = r1 + 1
    templ = {c: ws.cell(first, c) for c in range(c1, c2 + 1)}
    formula = {c: templ[c].value for c in templ if templ[c].data_type == "f"}
    samples = {c: [ws.cell(r, c).value for r in range(first, r2 + 1) if ws.cell(r, c).value is not None]
               for c in range(c1, c2 + 1)}
    styles = {c: copy(templ[c]._style) for c in templ}
    n_new = max(len(rows), 1)
    new_last = r1 + n_new
    if new_last > r2:  # growing: the cells below the table must be empty
        for r in range(r2 + 1, new_last + 1):
            for c in range(c1, c2 + 1):
                if ws.cell(r, c).value not in (None, ""):
                    raise RefreshBlocked(f"{name} would overwrite {ws.cell(r, c).coordinate} on '{ws.title}'")
    for i in range(n_new):
        r = first + i
        row = rows[i] if i < len(rows) else {}
        keep = row.get("_keep", {})
        for c, h in zip(range(c1, c2 + 1), headers):
            cell = ws.cell(r, c)
            if c in formula:
                cell.value = Translator(formula[c], origin=templ[c].coordinate).translate_formula(cell.coordinate) \
                    if r != first else formula[c]
            elif h in row:
                cell.value = _coerce(row[h], samples[c])
            else:
                cell.value = keep.get(h)
            cell._style = copy(styles[c])
    from .inventory import clear_cell
    for r in range(new_last + 1, r2 + 1):  # shrinking: clear what's left (value AND formatting)
        for c in range(c1, c2 + 1):
            clear_cell(ws.cell(r, c))
    ref = f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{new_last}"
    t.ref = ref
    if t.autoFilter is not None:
        t.autoFilter.ref = ref


def remove_rows(wb, name: str, serials: set[str]) -> list[str]:
    """Remove the table rows whose Serial is in `serials`. Remaining rows move up and keep
    their own values, formulas (translated) and formatting; the table range shrinks."""
    from copy import copy

    from openpyxl.formula.translate import Translator
    from openpyxl.utils import get_column_letter

    ws, t = _find_table(wb, name)
    if t.totalsRowCount:
        raise RefreshBlocked(f"{name} has a totals row; refresh not supported")
    c1, r1, c2, r2 = _bounds(t.ref)
    headers = [ws.cell(r1, c).value for c in range(c1, c2 + 1)]
    if "Serial" not in headers:
        raise RefreshBlocked(f"{name} has no Serial column")
    sc = c1 + headers.index("Serial")
    keep_rows = [r for r in range(r1 + 1, r2 + 1) if _key(ws.cell(r, sc).value) not in serials]
    removed = [_key(ws.cell(r, sc).value) for r in range(r1 + 1, r2 + 1) if _key(ws.cell(r, sc).value) in serials]
    if not removed:
        return []
    snapshot = {r: [(ws.cell(r, c).value, ws.cell(r, c).data_type, copy(ws.cell(r, c)._style))
                    for c in range(c1, c2 + 1)] for r in keep_rows}
    for i, src_r in enumerate(keep_rows):
        dst_r = r1 + 1 + i
        for j, c in enumerate(range(c1, c2 + 1)):
            value, dtype, style = snapshot[src_r][j]
            if dtype == "f" and dst_r != src_r:
                value = Translator(value, origin=f"{get_column_letter(c)}{src_r}").translate_formula(
                    f"{get_column_letter(c)}{dst_r}")
            cell = ws.cell(dst_r, c)
            cell.value = value
            cell._style = style
    new_last = r1 + max(len(keep_rows), 1)
    from .inventory import clear_cell
    for r in range(r1 + 1 + len(keep_rows), r2 + 1):  # rows left over: value AND formatting cleared
        for c in range(c1, c2 + 1):
            clear_cell(ws.cell(r, c))
    ref = f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{new_last}"
    t.ref = ref
    if t.autoFilter is not None:
        t.autoFilter.ref = ref
    return removed


def append_log(wb, entries: list[list]) -> None:
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    try:
        ws, t = _find_table(wb, T_LOG)
    except RefreshBlocked:
        ws = wb[CHANGELOG_SHEET] if CHANGELOG_SHEET in wb.sheetnames else wb.create_sheet(CHANGELOG_SHEET)
        for i, h in enumerate(LOG_HEADERS, start=1):
            ws.cell(1, i).value = h
        t = Table(displayName=T_LOG, ref=f"A1:{get_column_letter(len(LOG_HEADERS))}2",
                  tableStyleInfo=TableStyleInfo(name="TableStyleMedium2", showRowStripes=True))
        ws.add_table(t)
        start = 2
    else:
        c1, r1, c2, r2 = _bounds(t.ref)
        last_used = max((r for r in range(r1 + 1, r2 + 1)
                         if any(ws.cell(r, c).value not in (None, "") for c in range(c1, c2 + 1))), default=r1)
        start = last_used + 1
    for i, e in enumerate(entries):
        for j, v in enumerate(e, start=1):
            ws.cell(start + i, j).value = v
    c1, r1, c2, _ = _bounds(t.ref)
    end = max(start + len(entries) - 1, r1 + 1)
    t.ref = f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{end}"
    if t.autoFilter is not None:
        t.autoFilter.ref = t.ref


def apply_plan(data: bytes, plan: Plan, who: str, now: datetime | None = None) -> tuple[bytes, str]:
    from openpyxl import load_workbook

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    when = now.strftime("%Y-%m-%d %H:%M")
    wb = load_workbook(io.BytesIO(data))
    log = []
    write_table(wb, T_INTUNE, plan.intune_rows)
    write_table(wb, T_AP, plan.autopilot_rows)
    for t, rows in ((T_INTUNE, plan.intune_rows), (T_AP, plan.autopilot_rows)):
        log.append([when, who, t, "", "(refresh)", f"{plan.old_counts.get(t, 0)} rows", f"{len(rows)} rows"])
    removed = 0
    for t in (T_DECOM, T_STOCK):
        gone = {r["serial"]: r["why"] for r in plan.remove.get(t, [])}
        if not gone:
            continue
        for s in remove_rows(wb, t, set(gone)):
            log.append([when, who, t, s, "(row removed)", gone[s], ""])
            removed += 1
    append_log(wb, log)
    from .inventory import autosize_columns
    autosize_columns(wb)  # last step before every save: columns wide enough for their text
    out = io.BytesIO()
    wb.save(out)
    summary = (f"✅ Inventory refreshed: Intune Devices {len(plan.intune_rows)} rows, "
               f"Autopilot Not in Intune {len(plan.autopilot_rows)} rows, {removed} in-use laptop(s) removed "
               f"from Stock/Decommissioning. {len(log)} Change Log row(s) added.")
    return out.getvalue(), summary
