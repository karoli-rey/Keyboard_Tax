import sys
from types import SimpleNamespace

import pytest

from keyboard_tax.data import load_flores


def test_load_flores_aligns_by_id_and_normalizes_unicode(monkeypatch):
    rows = {
        "por_Latn": [
            {"id": "2", "text": "cafe\u0301"},
            {"id": "1", "text": "não"},
        ],
        "eng_Latn": [
            {"id": "1", "text": "no"},
            {"id": "2", "text": "coffee"},
        ],
    }
    calls = []

    def fake_load_dataset(dataset, language, split):
        calls.append((dataset, language, split))
        return rows[language]

    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(load_dataset=fake_load_dataset))
    result = load_flores("por_Latn", "eng_Latn", "dev")

    assert result.to_dict("records") == [
        {"sent_id": 0, "pt": "café", "en": "coffee"},
        {"sent_id": 1, "pt": "não", "en": "no"},
    ]
    assert calls == [
        ("openlanguagedata/flores_plus", "por_Latn", "dev"),
        ("openlanguagedata/flores_plus", "eng_Latn", "dev"),
    ]


def test_load_flores_requires_a_decided_split():
    with pytest.raises(ValueError, match="split in config.yaml"):
        load_flores("por_Latn", "eng_Latn", "TODO")