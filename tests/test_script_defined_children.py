"""Isolated tests for script-defined child entries (spec: script-defined-children).

These exercise the pure logic of the child helpers without constructing the full
MainWindowForm (which needs a running GUI/GDB). We bind the real, unbound methods
onto a lightweight fake `self` that provides only what the helpers touch, and use
real (headless) QTreeWidgetItems so the tree behaviour is genuine.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt

import PINCE
from libpince import typedefs


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeMainWindow:
    """A minimal stand-in carrying the real child helpers as bound methods.

    Only the attributes/methods the helpers actually use are provided.
    """

    # Reuse the real, unbound helper implementations.
    _build_script_children = PINCE.MainForm._build_script_children
    _clear_script_children = PINCE.MainForm._clear_script_children
    _script_child_value_type = PINCE.MainForm._script_child_value_type
    read_address_table_recursively = PINCE.MainForm.read_address_table_recursively
    read_address_table_entries = PINCE.MainForm.read_address_table_entries
    get_script_entry = PINCE.MainForm.get_script_entry
    init_script_row = PINCE.MainForm.init_script_row
    script_entries_in = PINCE.MainForm.script_entries_in
    SCRIPT_CHILD_MAX_DEPTH = PINCE.MainForm.SCRIPT_CHILD_MAX_DEPTH

    def __init__(self):
        self.libpince_engine_window = None
        self.tree_changed_calls = 0

    def mark_address_tree_changed(self):
        self.tree_changed_calls += 1

    # change_address_table_entries in the real class touches the palette and
    # debugcore; for these logic tests we only need it to store desc/address/type
    # the same way the real one does for the columns the tests inspect.
    def change_address_table_entries(self, row, description="", address_expr="", vt=None):
        row.setText(PINCE.DESC_COL, description)
        row.setData(PINCE.ADDR_COL, Qt.ItemDataRole.UserRole, address_expr)
        row.setData(PINCE.TYPE_COL, Qt.ItemDataRole.UserRole, vt)


def make_script_row(script=""):
    row = QTreeWidgetItem()
    row.setCheckState(PINCE.FROZEN_COL, Qt.CheckState.Unchecked)
    entry = typedefs.ScriptEntry(script)
    FakeMainWindow.init_script_row(FakeMainWindow(), row, "God Mode", entry)
    return row, entry


def test_no_children_key_builds_nothing(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {}  # no "children"
    mw._build_script_children(row, entry)
    assert row.childCount() == 0


def test_children_not_a_list_is_ignored(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {"children": "nope"}
    mw._build_script_children(row, entry)
    assert row.childCount() == 0


def test_malformed_elements_are_skipped(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {"children": [
        "not a dict",
        {},                      # no name
        {"name": ""},            # empty name
        {"name": "LP"},          # valid
    ]}
    mw._build_script_children(row, entry)
    assert row.childCount() == 1
    assert row.child(0).text(PINCE.DESC_COL) == "LP"


def test_address_getter_is_stored_and_polled_value_used(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {"children": [{"name": "LP", "address": lambda: None, "size": 4}]}
    mw._build_script_children(row, entry)
    child = row.child(0)
    getter = child.data(PINCE.SCRIPT_CHILD_ADDR_GETTER_ROLE, Qt.ItemDataRole.UserRole)
    assert callable(getter)
    # Initially None -> address empty
    assert child.data(PINCE.ADDR_COL, Qt.ItemDataRole.UserRole) == ""


def test_size_maps_to_integer_value_type(qapp):
    mw = FakeMainWindow()
    vt = mw._script_child_value_type({"size": 8})
    assert isinstance(vt, typedefs.IntegerValueType)
    # default when invalid
    vt2 = mw._script_child_value_type({"size": 3})
    assert isinstance(vt2, typedefs.IntegerValueType)


def test_script_child_is_a_script_entry(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {"children": [{"name": "Sub", "script": "[ENABLE]\npass"}]}
    mw._build_script_children(row, entry)
    child = row.child(0)
    assert mw.get_script_entry(child) is not None


def test_clear_removes_only_marked_children(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    # a pre-existing non-marked child (as if user-added)
    plain = QTreeWidgetItem()
    plain.setData(PINCE.FROZEN_COL, Qt.ItemDataRole.UserRole, typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT))
    row.addChild(plain)
    entry.namespace = {"children": [{"name": "LP"}]}
    mw._build_script_children(row, entry)
    assert row.childCount() == 2
    mw._clear_script_children(row)
    # only the marked LP child is gone; the plain one remains
    assert row.childCount() == 1
    assert row.child(0) is plain


def test_ephemeral_children_not_serialized(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row("[ENABLE]\npass")
    entry.namespace = {"children": [{"name": "LP", "address": lambda: "0x1000"}]}
    mw._build_script_children(row, entry)
    assert row.childCount() == 1
    record = mw.read_address_table_recursively(row)
    # script row is length 5, children element is last and must be empty
    assert len(record) == 5
    assert record[4] == []


def test_depth_guard_stops_building(qapp):
    mw = FakeMainWindow()
    row, entry = make_script_row()
    entry.namespace = {"children": [{"name": "LP"}]}
    mw._build_script_children(row, entry, depth=mw.SCRIPT_CHILD_MAX_DEPTH)
    assert row.childCount() == 0
