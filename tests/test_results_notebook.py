"""results.ipynb must run from top to bottom with only results/ and the package."""

import json
import sys
import types

import pytest

from keyboard_tax.common import ROOT


def test_results_notebook_runs(monkeypatch):
    pytest.importorskip("matplotlib")
    shown = []
    display = types.ModuleType("IPython.display")
    display.display = shown.append
    display.Image = lambda filename=None, width=None: filename
    ipython = types.ModuleType("IPython")
    ipython.get_ipython = lambda: None
    ipython.version_info = (8, 0, 0)
    monkeypatch.setitem(sys.modules, "IPython", ipython)
    monkeypatch.setitem(sys.modules, "IPython.display", display)
    monkeypatch.chdir(ROOT)
    notebook = json.loads((ROOT / "results.ipynb").read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec("".join(cell["source"]), namespace)  # noqa: S102
    assert len(shown) >= 10  # the tables and the three charts
    assert set(namespace["hypotheses"]["hypothesis"].str[:2]) >= {"H1", "H2", "H3", "H4", "H5", "H6"}
