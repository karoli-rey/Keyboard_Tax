import re

import pandas as pd
import pytest

from keyboard_tax.common import read_table, strip_diacritics
from keyboard_tax.versions import build_versions, check_reviewed, summarize

ALL_VERSIONS = [
    "clean", "stripped_100", "a_only", "b_only", "noise",
    "stripped_25", "stripped_50", "stripped_75",
]


def _fixture_versions(is_word=None):
    return build_versions(
        read_table("sentences", fixtures=True),
        read_table("lexicon", fixtures=True),
        seed=13,
        is_word=is_word,
        versions=ALL_VERSIONS,
    )


def test_versions_match_a_and_b_counts_and_noise_letter_budget():
    versions = _fixture_versions()
    by_version = versions[versions["sent_id"] == 0].set_index("version")
    assert by_version.loc["a_only", "n_a"] == by_version.loc["b_only", "n_b"]
    assert by_version.loc["noise", "n_chars"] == by_version.loc["b_only", "n_chars"]


def test_versions_are_deterministic_for_the_same_seed():
    assert _fixture_versions().equals(_fixture_versions())


def test_versions_preserve_case_when_stripping():
    sentences = pd.DataFrame({"sent_id": [3], "pt": ["Não? Pôde."]})
    lexicon = pd.DataFrame({"word": ["não", "pôde"], "label": ["A", "B"]})
    versions = build_versions(sentences, lexicon, seed=2, versions=ALL_VERSIONS)
    by_version = versions.set_index("version")
    assert by_version.loc["stripped_100", "src"] == "Nao? Pode."
    assert by_version.loc["a_only", "src"] == "Nao? Pôde."
    assert by_version.loc["b_only", "src"] == "Não? Pode."


def test_sentence_without_both_classes_gets_only_clean_and_fully_stripped():
    versions = _fixture_versions()
    sentence_versions = set(versions.loc[versions["sent_id"] == 1, "version"])
    assert sentence_versions == {"clean", "stripped_100"}


def test_strip_rate_versions_are_nested():
    versions = _fixture_versions()
    by_version = versions[versions["sent_id"] == 0].set_index("version")
    accented_words = {"avô", "não", "pôde", "à"}

    def stripped_words(version):
        text = by_version.loc[version, "src"].lower()
        return {word for word in accented_words if strip_diacritics(word) in text and word not in text}

    stripped_25 = stripped_words("stripped_25")
    stripped_50 = stripped_words("stripped_50")
    stripped_75 = stripped_words("stripped_75")
    stripped_100 = stripped_words("stripped_100")
    assert stripped_25 <= stripped_50 <= stripped_75 <= stripped_100
    assert stripped_100 == accented_words


def test_noise_retries_mutations_that_make_real_words():
    sentences = pd.DataFrame({"sent_id": [0], "pt": ["Não pôde visitá-la."]})
    lexicon = pd.DataFrame({"word": ["não", "pôde"], "label": ["A", "B"]})
    real_words = {"nao", "pode", "visita", "la", "visita-la"}
    noise = build_versions(
        sentences, lexicon, seed=11, is_word=lambda word: word in real_words,
        versions=["clean", "stripped_100", "a_only", "b_only", "noise"],
    ).set_index("version").loc["noise"]
    original_words = re.findall(r"[^\W\d_]+", sentences.loc[0, "pt"].lower())
    noise_words = re.findall(r"[^\W\d_]+", noise["src"].lower())
    changed_words = [new for old, new in zip(original_words, noise_words) if old != new]
    assert noise["n_chars"] == 1
    assert changed_words
    assert not any(word in real_words for word in changed_words)

@pytest.mark.parametrize(
    "texts", [["2026", "Não pôde."], ["Não pôde.", "2026"]], ids=["first", "after_a_and_b"]
)
def test_sentence_without_words_gets_only_clean_and_fully_stripped(texts):
    sentences = pd.DataFrame({"sent_id": range(len(texts)), "pt": texts})
    lexicon = pd.DataFrame({"word": ["não", "pôde"], "label": ["A", "B"]})
    versions = build_versions(sentences, lexicon, seed=0, versions=ALL_VERSIONS)
    number_id = texts.index("2026")
    other_id = 1 - number_id
    assert set(versions.loc[versions["sent_id"] == number_id, "version"]) == {
        "clean", "stripped_100",
    }
    assert "b_only" in set(versions.loc[versions["sent_id"] == other_id, "version"])


def test_check_reviewed_stops_while_words_are_still_todo():
    lexicon = read_table("lexicon", fixtures=True)
    check_reviewed(lexicon)  # every fixture row is "yes"
    lexicon.loc[0, "native_checked"] = "todo"
    with pytest.raises(SystemExit, match=r"1 word\(s\) with native_checked 'todo'"):
        check_reviewed(lexicon)


def test_summary_counts_versions_and_noise_that_fell_short():
    sentences = pd.DataFrame({"sent_id": [0, 1], "pt": ["Não pôde.", "Ela é."]})
    lexicon = pd.DataFrame({"word": ["não", "pôde", "é"], "label": ["A", "B", "B"]})
    versions = build_versions(
        sentences, lexicon, seed=0,
        versions=["clean", "stripped_100", "a_only", "b_only", "noise"],
    )
    summary = summarize(versions)
    assert "2 sentences" in summary
    assert "  b_only        1" in summary
    assert "  clean         2" in summary
    # "Não pôde." has no letter outside accented words, so the noise changes nothing.
    assert "noise changed fewer letters than b_only in 1 sentence(s)" in summary
