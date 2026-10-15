from keyboard_tax.classify import classify, letter_table
from keyboard_tax.common import normalize, strip_diacritics

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
