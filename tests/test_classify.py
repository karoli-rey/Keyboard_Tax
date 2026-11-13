import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from keyboard_tax.classify import (
    build_lexicon,
    classify,
    find_accented_words,
    init_lexicon,
    letter_table,
    load_is_word,
    review_sheet,
)
from keyboard_tax.common import check_columns, normalize, read_table, strip_diacritics

# A tiny stand-in for the Hunspell dictionary, enough for these tests.
VOCAB = {"tem", "pode", "a", "e", "eles"}


def is_word(word: str) -> bool:
    return word in VOCAB


def test_strip_diacritics():
    assert strip_diacritics("pôde") == "pode"
    assert strip_diacritics("não") == "nao"
    assert strip_diacritics("estação") == "estacao"
    assert strip_diacritics("À") == "A"


def test_classify():
    assert classify("têm", is_word) == "B"      # tem is a word: number is lost
    assert classify("pôde", is_word) == "B"     # pode is a word: tense is lost
    assert classify("não", is_word) == "A"      # nao is not a word
    assert classify("Eles", is_word) == "none"  # no diacritic at all


def test_letter_table_ignores_punctuation_and_flags_unsplittable_letters():
    table = letter_table(["Ela disse: “não” — custa 5 €.", "Łódź"]).set_index("letter")
    assert set(table.index) == {"ã", "Ł", "ó", "ź"}
    assert table.loc["ã", "status"] == "ok"
    assert table.loc["Ł", "status"] == "not decomposable"


def test_normalize_unifies_romanian_cedilla():
    assert normalize("şi ţară", {"ş": "ș", "ţ": "ț"}) == "și țară"


def test_find_accented_words_skips_names_but_keeps_sentence_initial_words():
    sentences = pd.DataFrame({"pt": ["É uma cidade. João encontrou Áurea; a mãe chegou."]})
    assert find_accented_words(sentences) == {"é", "mãe"}


def test_build_lexicon_flags_rare_class_b_and_seeded_review_sample(monkeypatch):
    frequencies = {"pode": 5.5, "a": 7.0, "e": 7.0}
    fake_wordfreq = SimpleNamespace(zipf_frequency=lambda word, _lang: frequencies[word])
    monkeypatch.setitem(sys.modules, "wordfreq", fake_wordfreq)
    config = {"min_zipf": 6, "review_sample": 1, "seed": 7}

    first = build_lexicon(["pôde", "não", "à", "é"], is_word, config)
    second = build_lexicon(["pôde", "não", "à", "é"], is_word, config)
    assert first.equals(second)
    by_word = first.set_index("word")
    assert by_word.loc["pôde", "label"] == "B"
    assert bool(by_word.loc["pôde", "needs_review"])
    assert pd.isna(by_word.loc["não", "zipf"])
    assert first["needs_review"].sum() == 2


def test_open_dictionary_and_frequency_settings_require_team_decisions():
    with pytest.raises(ValueError, match="dictionary path in config.yaml"):
        load_is_word({"dictionary": "TODO"})
    with pytest.raises(ValueError, match="Set min_zipf"):
        build_lexicon([], is_word, {"min_zipf": "TODO"})


def test_load_is_word_reads_a_relative_dictionary_path_from_the_project_folder(
    tmp_path, monkeypatch
):
    import keyboard_tax.classify as classify_module

    (tmp_path / "data" / "raw").mkdir(parents=True)
    for suffix in (".dic", ".aff"):
        (tmp_path / "data" / "raw" / f"pt_BR{suffix}").write_text("")
    opened = []

    class FakeDictionary:
        @staticmethod
        def from_files(path):
            opened.append(path)
            return SimpleNamespace(lookup=lambda word: word == "pode")

    fake_spylls = SimpleNamespace(hunspell=SimpleNamespace(Dictionary=FakeDictionary))
    monkeypatch.setitem(sys.modules, "spylls", fake_spylls)
    monkeypatch.setitem(sys.modules, "spylls.hunspell", fake_spylls.hunspell)
    monkeypatch.setattr(classify_module, "ROOT", tmp_path)
    monkeypatch.chdir(tmp_path / "data")
    classify_module._dictionary_lookup.cache_clear()

    lookup = load_is_word({"dictionary": "data/raw/pt_BR"})
    assert opened == [str(tmp_path / "data" / "raw" / "pt_BR")]
    assert lookup("pode") and not lookup("nao")
    classify_module._dictionary_lookup.cache_clear()


def test_load_is_word_names_missing_dictionary_files(tmp_path):
    with pytest.raises(ValueError, match="get_dictionary.sh"):
        load_is_word({"dictionary": str(tmp_path / "pt_BR")})


def test_init_lexicon_marks_review_words_todo_and_keeps_the_agreed_columns():
    lexicon = init_lexicon(read_table("lexicon_auto", fixtures=True))
    check_columns(lexicon, "lexicon")
    by_word = lexicon.set_index("word")
    assert by_word.loc["avô", "native_checked"] == "todo"   # needs_review True
    assert by_word.loc["não", "native_checked"] == "no"
    assert set(lexicon["lost"]) == {""} and set(lexicon["note"]) == {""}


def test_review_sheet_shows_each_word_in_a_sentence():
    sheet = review_sheet(
        read_table("lexicon_auto", fixtures=True), read_table("sentences", fixtures=True)
    )
    assert list(sheet.columns) == [
        "word", "stripped", "label", "zipf", "native_checked", "example"
    ]
    assert sheet.set_index("word").loc["pôde", "example"] == "O avô dele não pôde vir à festa."


def test_review_sheet_lists_todo_words_first():
    lexicon_auto = read_table("lexicon_auto", fixtures=True)
    lexicon_auto["needs_review"] = [False, False, True, False, True]   # pôde and é
    sheet = review_sheet(lexicon_auto, read_table("sentences", fixtures=True))
    assert list(sheet["native_checked"]) == ["todo", "todo", "no", "no", "no"]
    assert list(sheet["word"]) == ["pôde", "é", "avô", "não", "à"]


def test_init_lexicon_never_overwrites_a_reviewed_lexicon(tmp_path, monkeypatch):
    import keyboard_tax.classify as classify_module

    reviewed = tmp_path / "lexicon.csv"
    reviewed.write_text("reviewed by hand\n")
    monkeypatch.setattr(classify_module, "table_path", lambda name: reviewed)
    with pytest.raises(SystemExit, match="--force"):
        classify_module.write_lexicon_start()
    assert reviewed.read_text() == "reviewed by hand\n"


def test_init_lexicon_with_force_writes_lexicon_and_review_sheet(tmp_path, monkeypatch):
    import keyboard_tax.classify as classify_module

    written = {}
    reviewed = tmp_path / "lexicon.csv"
    reviewed.write_text("reviewed by hand\n")
    monkeypatch.setattr(classify_module, "table_path", lambda name: reviewed)
    monkeypatch.setattr(
        classify_module, "read_table", lambda name: read_table(name, fixtures=True)
    )
    monkeypatch.setattr(
        classify_module, "write_table", lambda df, name: written.setdefault(name, df) is df
    )
    monkeypatch.setattr(classify_module, "REVIEW_SHEET", tmp_path / "2_review_sheet.csv")
    classify_module.write_lexicon_start(force=True)
    assert list(written) == ["lexicon"]
    assert (tmp_path / "2_review_sheet.csv").exists()
