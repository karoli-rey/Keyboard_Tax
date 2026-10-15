"""The example tables in fixtures/ follow the agreed columns, and the matching rule holds.

The fixtures are made-up examples (not FLORES data); the scores in them are invented.
"""

import pytest

from keyboard_tax.common import TABLES, read_table


@pytest.mark.parametrize("name", sorted(TABLES))
def test_every_example_has_the_agreed_columns(name):
    read_table(name, fixtures=True)  # raises if the columns differ


def test_labels_are_a_or_b():
    for name in ("lexicon_auto", "lexicon"):
        assert set(read_table(name, fixtures=True)["label"]) <= {"A", "B"}


def test_a_only_and_b_only_change_the_same_number_of_words():
    versions = read_table("versions", fixtures=True)
    for _, rows in versions.groupby("sent_id"):
        by_version = rows.set_index("version")
        if "a_only" in by_version.index and "b_only" in by_version.index:
            assert by_version.loc["a_only", "n_a"] == by_version.loc["b_only", "n_b"]
            assert by_version.loc["noise", "n_chars"] == by_version.loc["b_only", "n_chars"]
