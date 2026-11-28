"""L0: SharePoint list rows - allow-list, safety rules and the self-test, with a fake list.
Every fake call is also checked against graph.py's allow-list."""
import pytest

from bot.agent import ItBot
from bot.graph import INVENTORY_SITE_ID, GraphRefused, check_allowed
from bot.identity import IdentityResolver
from bot.lists import TEST_LIST, ListRefused, ListStore, selftest
from bot.tests.fakes import FakeGraph

S = f"v1.0/sites/{INVENTORY_SITE_ID}"


def test_allow_list_list_items_only():
    check_allowed("GET", f"{S}/lists?$select=id,displayName,list")
    check_allowed("GET", f"{S}/lists/L1/items/5?$expand=fields")
    check_allowed("POST", f"{S}/lists/L1/items")
    check_allowed("PATCH", f"{S}/lists/L1/items/5/fields")
    check_allowed("DELETE", f"{S}/lists/L1/items/5")
    for method, path in [
        ("POST", f"{S}/lists"),                        # create a list: not allowed
        ("POST", f"{S}/lists/L1/columns"),             # add a column: not allowed
        ("DELETE", f"{S}/lists/L1"),                   # delete a list: not allowed
        ("PATCH", f"{S}/lists/L1/items/5"),            # only /fields may be patched
        ("POST", f"{S}/permissions"),                  # permissions: never
        ("POST", "v1.0/sites/other.sharepoint.com,1,2/lists/L1/items"),  # other site
    ]:
        with pytest.raises(GraphRefused):
            check_allowed(method, path)


class FakeList:
    def __init__(self, name=TEST_LIST, honour_if_match=True):
        self.meta = {"id": "L1", "displayName": name}
        self.items, self.versions, self.calls = {}, {}, []
        self.honour = honour_if_match

    async def get_all(self, path, limit=500):
        check_allowed("GET", path)
        if path.endswith("/versions"):
            return [{}] * self.versions[path.split("/items/")[1].split("/")[0]]
        return [self.meta]

    async def get(self, path):
        check_allowed("GET", path)
        iid = path.split("/items/")[1].split("?")[0]
        return self.items[iid]

    async def send_json(self, method, path, body=None, if_match=None):
        check_allowed(method, path)
        self.calls.append((method, if_match))
        if method == "POST":
            self.items["5"] = {"id": "5", "eTag": '"e,1"', "fields": dict(body["fields"])}
            self.versions["5"] = 1
            return 201, self.items["5"]
        iid = path.split("/items/")[1].split("/")[0]
        if self.honour and if_match != self.items[iid]["eTag"]:
            return 412, {"error": {"code": "resourceModified"}}
        if method == "PATCH":
            self.items[iid]["fields"].update(body)
            self.versions[iid] += 1
            self.items[iid]["eTag"] = f'"e,{self.versions[iid]}"'
            return 200, self.items[iid]["fields"]
        del self.items[iid]
        return 204, {}


async def test_selftest_all_green_and_row_removed():
    fake = FakeList()
    report = await selftest(ListStore(fake))
    assert "❌" not in report, report
    assert "HTTP 412" in report and fake.items == {}


async def test_selftest_flags_missing_version_check():
    report = await selftest(ListStore(FakeList(honour_if_match=False)))
    assert "NOT rejected" in report


async def test_real_lists_refused_and_etag_required():
    store = ListStore(FakeList(name="Stock"))
    lst = {"id": "L1", "displayName": "Stock"}
    with pytest.raises(ListRefused):
        await store.add(lst, {"Title": "x"})
    test_lst = {"id": "L1", "displayName": TEST_LIST}
    with pytest.raises(ListRefused):
        await store.update(test_lst, "5", {"Title": "x"}, "")


async def test_yes_with_nothing_pending_gets_clear_reply_not_claude():
    g = FakeGraph({"transitiveMemberOf": [{"id": "s"}]})
    bot = ItBot(g, IdentityResolver(g, "a", "s"), None, "dep")  # claude=None: would crash if called
    assert "nothing waiting for a **yes**" in await bot.handle("u", "yes", "c")


async def test_selftest_lists_is_approver_only():
    g = FakeGraph({"transitiveMemberOf": [{"id": "s"}]})
    bot = ItBot(g, IdentityResolver(g, "a", "s"), None, "dep", lists=object())
    assert "approvers only" in await bot.handle("u", "selftest lists", "c")
