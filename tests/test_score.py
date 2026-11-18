import math

import pandas as pd
import pytest

from keyboard_tax.common import check_columns, read_table
from keyboard_tax.score import (
    SUBSET_ALL,
    SUBSET_BOTH,
    score_corpus,
    score_sentences,
    with_references,
)

CONFIG = {"comet_model": "fake/comet"}


class Recorder:
    """Fake metrics that remember what they were asked to score."""

    def __init__(self) -> None:
        self.chrf_calls: list[tuple[str, str]] = []
        self.comet_calls: list[tuple[str, str, str]] = []

    def chrf(self, hypotheses: list[str], references: list[str]) -> list[float]:
        self.chrf_calls += list(zip(hypotheses, references, strict=True))
        return [100.0 if hyp == ref else 50.0 for hyp, ref in zip(hypotheses, references)]

    def comet(self, sources: list[str], hypotheses: list[str], references: list[str]) -> list:
        self.comet_calls += list(zip(sources, hypotheses, references, strict=True))
        return [1.0 if hyp == ref else 0.25 for hyp, ref in zip(hypotheses, references)]


def fake_corpus(hypotheses: list[str], references: list[str]) -> tuple[float, float]:
    same = sum(hyp == ref for hyp, ref in zip(hypotheses, references, strict=True))
    return 100.0 * same / len(hypotheses), 10.0 * len(hypotheses)


def five_version_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sentence 0 has all five versions, sentence 1 only clean and stripped_100."""
    sentences = pd.DataFrame(
        {"sent_id": [0, 1], "pt": ["Ele não pôde vir.", "Ela é alta."],
         "en": ["He could not come.", "She is tall."]}
    )
    rows = [
        (0, "clean", "Ele não pôde vir.", "He could not come."),
        (0, "stripped_100", "Ele nao pode vir.", "He cannot come."),
        (0, "a_only", "Ele nao pôde vir.", "He could not come."),
        (0, "b_only", "Ele não pode vir.", "He cannot come."),
        (0, "noise", "Ele não pôde vjr.", "He could not come."),
        (1, "clean", "Ela é alta.", "She is tall."),
        (1, "stripped_100", "Ela e alta.", "She is tall."),
    ]
    translations = pd.DataFrame(rows, columns=["sent_id", "version", "src", "hyp"])
    translations.insert(2, "system", "nllb")
    return translations, sentences


def test_scores_table_has_one_row_per_translation_with_the_agreed_columns():
    translations = read_table("translations", fixtures=True)
    sentences = read_table("sentences", fixtures=True)
    metrics = Recorder()
    scores = score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)

    check_columns(scores, "scores")
    assert scores[["sent_id", "version", "system"]].equals(
        translations[["sent_id", "version", "system"]]
    )
    assert scores["chrf"].tolist() == [100.0, 50.0, 100.0, 50.0]
    assert scores["comet"].tolist() == [1.0, 0.25, 1.0, 0.25]


def test_comet_always_gets_the_clean_portuguese_sentence():
    translations, sentences = five_version_data()
    metrics = Recorder()
    score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)

    sources = {source for source, _, _ in metrics.comet_calls}
    assert sources == {"Ele não pôde vir.", "Ela é alta."}  # never a damaged sentence


def test_identical_translations_are_scored_once():
    translations, sentences = five_version_data()
    metrics = Recorder()
    scores = score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)

    assert len(metrics.comet_calls) == len(set(metrics.comet_calls)) == 3
    assert len(metrics.chrf_calls) == 3
    assert len(scores) == 7


def test_skip_comet_leaves_the_comet_column_empty_and_loads_no_model():
    translations, sentences = five_version_data()
    scores = score_sentences(translations, sentences, CONFIG, Recorder().chrf, skip_comet=True)
    assert scores["comet"].isna().all() and scores["chrf"].notna().all()


def test_an_empty_translation_is_scored_as_an_empty_text():
    translations, sentences = five_version_data()
    translations.loc[0, "hyp"] = None
    metrics = Recorder()
    scores = score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)
    assert ("", "He could not come.") in metrics.chrf_calls
    assert scores.loc[0, "chrf"] == 50.0


def test_a_translation_without_a_reference_is_an_error():
    translations, sentences = five_version_data()
    with pytest.raises(ValueError, match="No reference"):
        with_references(translations, sentences[sentences["sent_id"] == 0])


def test_corpus_scores_have_both_subsets_with_the_right_sentences():
    translations, sentences = five_version_data()
    metrics = Recorder()
    scores = score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)
    corpus = score_corpus(translations, sentences, scores, fake_corpus)

    check_columns(corpus, "corpus_scores")
    table = corpus.set_index(["subset", "version"])
    assert table.loc[(SUBSET_ALL, "clean"), "n"] == 2
    assert table.loc[(SUBSET_BOTH, "clean"), "n"] == 1  # only the sentence with all versions
    assert table.loc[(SUBSET_ALL, "b_only"), "n"] == table.loc[(SUBSET_BOTH, "b_only"), "n"] == 1
    assert len(corpus) == 2 * 5
    # stripped_100 over all sentences: one right, one wrong
    assert table.loc[(SUBSET_ALL, "stripped_100"), "bleu"] == 50.0
    assert math.isclose(table.loc[(SUBSET_ALL, "stripped_100"), "comet"], (0.25 + 1.0) / 2)
    assert table.loc[(SUBSET_BOTH, "stripped_100"), "bleu"] == 0.0


def test_corpus_scores_refuse_scores_in_another_order():
    translations, sentences = five_version_data()
    metrics = Recorder()
    scores = score_sentences(translations, sentences, CONFIG, metrics.chrf, metrics.comet)
    with pytest.raises(ValueError, match="same rows"):
        score_corpus(translations, sentences, scores.iloc[::-1], fake_corpus)


def test_real_chrf_and_bleu_from_sacrebleu():
    pytest.importorskip("sacrebleu")
    from keyboard_tax.score import corpus_bleu_chrf, sacrebleu_signatures, sentence_chrf

    reference = "His grandfather could not come to the party."
    perfect, damaged = sentence_chrf([reference, "His grandfather can't come."], [reference] * 2)
    assert perfect == pytest.approx(100.0) and 0 < damaged < 100
    bleu, chrf = corpus_bleu_chrf([reference], [reference])
    assert bleu == pytest.approx(100.0) and chrf == pytest.approx(100.0)
    assert "version:" in sacrebleu_signatures()["BLEU"]
