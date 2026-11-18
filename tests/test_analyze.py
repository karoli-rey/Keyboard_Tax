import numpy as np
import pandas as pd
import pytest

from keyboard_tax.analyze import (
    bleu_versus_targeted,
    clustered_regression,
    contrast_table,
    drop_table,
    hypothesis_table,
    mean_with_interval,
    pattern,
    regression,
    run,
    sentence_drops,
    sentences_in_another_script,
    sentences_where_e_is_stripped,
    system_gap_table,
    targeted_by_loss,
    targeted_check,
    targeted_summary,
    verdict,
)
from keyboard_tax.common import read_table

VERSIONS = ["clean", "stripped_100", "a_only", "b_only", "noise"]


def made_up_data(n_sentences: int = 40, seed: int = 0):
    """Scores where each B word costs 0.05, each A word 0.01 and each changed letter 0.02.

    stripped_100 has 2 A words, 1 B word and 3 changed letters: cost 0.13. The LLM loses
    half as much as NLLB.

    Sentences 0..n-1 have all five versions; two more sentences have only clean and
    stripped_100 (like the 590 real sentences without both classes).
    """
    rng = np.random.default_rng(seed)
    counts = {  # n_a, n_b, n_chars
        "clean": (0, 0, 0), "stripped_100": (2, 1, 3), "a_only": (1, 0, 1),
        "b_only": (0, 1, 1), "noise": (0, 0, 1),
    }
    cost = {v: 0.01 * a + 0.05 * b + 0.02 * c for v, (a, b, c) in counts.items()}
    rows, vrows = [], []
    for sent_id in range(n_sentences + 2):
        versions = VERSIONS if sent_id < n_sentences else ["clean", "stripped_100"]
        base = 0.9 - 0.1 * rng.random()
        for version in versions:
            for system in ("nllb", "llm"):
                factor = 0.5 if system == "llm" else 1.0
                comet = base - factor * cost[version] + rng.normal(0, 0.002)
                rows.append((sent_id, version, system, 70 - 100 * cost[version] * factor, comet))
            n_a, n_b, n_chars = counts[version]
            src = "Ele não pôde vir." if version != "b_only" else "Ele não pode vir."
            if version == "clean" and sent_id % 2:
                src = "Ela é alta e não pôde vir."
            if version == "b_only" and sent_id % 2:
                src = "Ela e alta e não pôde vir."  # é stripped in odd sentences
            vrows.append((sent_id, version, src, n_a, n_b, n_chars))
    scores = pd.DataFrame(rows, columns=["sent_id", "version", "system", "chrf", "comet"])
    versions = pd.DataFrame(vrows, columns=["sent_id", "version", "src", "n_a", "n_b", "n_chars"])
    return scores, versions


def test_sentence_drops_are_clean_minus_damaged():
    scores, _ = made_up_data(2)
    drops = sentence_drops(scores)
    one = "sent_id == 0 and system == 'nllb'"
    row = drops.query(one + " and version == 'b_only'")
    clean = scores.query(one + " and version == 'clean'")["comet"].item()
    damaged = scores.query(one + " and version == 'b_only'")["comet"].item()
    assert row["comet_drop"].item() == pytest.approx(clean - damaged)
    assert "clean" not in set(drops["version"])


def test_mean_with_interval():
    mean, low, high = mean_with_interval(pd.Series([1.0, 2.0, 3.0, 4.0]))
    assert mean == 2.5 and low < 2.5 < high
    assert all(np.isnan(mean_with_interval(pd.Series([], dtype=float))))


def test_drop_table_recovers_the_built_in_costs_on_both_subsets():
    scores, _ = made_up_data()
    table = drop_table(scores).set_index(["subset", "system", "version"])
    close = lambda x: pytest.approx(x, abs=0.002)
    assert table.loc[("both_classes", "nllb", "b_only"), "comet_drop"] == close(0.07)
    assert table.loc[("both_classes", "nllb", "a_only"), "comet_drop"] == close(0.03)
    assert table.loc[("both_classes", "llm", "b_only"), "comet_drop"] == close(0.035)
    assert table.loc[("all", "nllb", "stripped_100"), "n"] == 42
    assert table.loc[("both_classes", "nllb", "stripped_100"), "n"] == 40
    low, high = table.loc[("both_classes", "nllb", "b_only"), ["comet_low", "comet_high"]]
    assert low < 0.07 < high


def test_contrasts_are_paired_differences_with_intervals():
    scores, _ = made_up_data()
    table = contrast_table(scores).set_index(["system", "contrast"])
    row = table.loc[("nllb", "b_only minus a_only")]
    assert row["comet_diff"] == pytest.approx(0.04, abs=0.002)
    assert row["comet_low"] > 0 and row["n"] == 40
    assert table.loc[("nllb", "b_only minus noise"), "comet_diff"] == pytest.approx(0.05, abs=0.002)


def test_clustered_regression_matches_known_coefficients():
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(50), 4)
    x = np.column_stack([np.ones(200), rng.normal(size=200), rng.normal(size=200)])
    y = x @ np.array([1.0, 2.0, -0.5]) + rng.normal(0, 0.01, size=200)
    beta, se = clustered_regression(y, x, groups)
    assert beta == pytest.approx([1.0, 2.0, -0.5], abs=0.01)
    assert (se > 0).all() and (se < 0.01).all()


def test_regression_finds_the_built_in_cost_per_word_and_letter():
    scores, versions = made_up_data()
    fit = regression(scores, versions).set_index(["system", "term"])
    assert fit.loc[("nllb", "b1 (B words)"), "estimate"] == pytest.approx(0.05, abs=0.005)
    assert fit.loc[("nllb", "b2 (A words)"), "estimate"] == pytest.approx(0.01, abs=0.005)
    assert fit.loc[("nllb", "b3 (changed letters)"), "estimate"] == pytest.approx(0.02, abs=0.005)
    assert fit.loc[("nllb", "b1 (B words)"), "n"] == 4 * 40 + 2
    assert fit.loc[("llm", "b1 (B words)"), "estimate"] == pytest.approx(0.025, abs=0.005)


@pytest.mark.parametrize(
    ("hyp", "expected"),
    [
        ("His grandfather could not come.", "right"),
        ("His grandfather can't come.", "wrong"),
        ("He could come, but he can't.", "unclear"),
        ("His grandfather did not come.", "unclear"),
    ],
)
def test_verdict(hyp, expected):
    correct, wrong = pattern("could|was able"), pattern("can|can't|cannot")
    assert verdict(hyp, correct, wrong) == expected


def test_pattern_matches_whole_words_only():
    assert pattern("can").search("He can come.")
    assert not pattern("can").search("A canoe.")


def test_targeted_check_counts_only_rows_where_the_word_was_stripped():
    translations = read_table("translations", fixtures=True)
    versions = read_table("versions", fixtures=True)
    challenge = read_table("challenge_set", fixtures=True)
    check = targeted_check(translations, challenge, versions)
    by = check.set_index("version")
    assert by.loc["clean", "stripped"] == False and by.loc["clean", "verdict"] == "right"
    assert by.loc["b_only", "stripped"] == True and by.loc["b_only", "verdict"] == "wrong"
    summary = targeted_summary(check).set_index("version")
    assert summary.loc["clean", "accuracy"] == 1.0
    assert summary.loc["b_only", "accuracy"] == 0.0


def test_targeted_by_loss_uses_the_kind_the_native_speaker_wrote():
    check = targeted_check(
        read_table("translations", fixtures=True),
        read_table("challenge_set", fixtures=True),
        read_table("versions", fixtures=True),
    )
    table = targeted_by_loss(check, read_table("lexicon", fixtures=True))
    assert set(table["loss"]) == {"tense"}
    assert table.set_index("version").loc["b_only", "accuracy"] == 0.0


def test_bleu_versus_targeted_compares_the_same_items():
    check = pd.DataFrame(
        {
            "sent_id": [0, 0, 1, 1],
            "word": ["país", "país", "força", "força"],
            "version": ["clean", "stripped_100"] * 2,
            "system": "nllb",
            "stripped": [False, True, False, True],
            "verdict": ["right", "wrong", "right", "right"],
        }
    )
    translations = pd.DataFrame(
        {
            "sent_id": [0, 0, 1, 1],
            "version": ["clean", "stripped_100"] * 2,
            "system": "nllb",
            "src": "x",
            "hyp": ["a", "b", "c", "c"],
        }
    )
    sentences = pd.DataFrame({"sent_id": [0, 1], "pt": "x", "en": ["a", "c"]})

    def share_identical(hyps, refs):  # a stand-in for BLEU and chrF
        same = sum(h == r for h, r in zip(hyps, refs, strict=True)) / len(refs) * 100
        return same, same

    table = bleu_versus_targeted(translations, sentences, check, corpus_function=share_identical)
    row = table.iloc[0]
    assert row["n_items"] == 2 and row["n_sentences"] == 2
    assert row["accuracy_clean"] == 1.0 and row["accuracy_damaged"] == 0.5
    assert row["accuracy_drop_share"] == 0.5
    assert row["bleu_drop_share"] == 0.5


def test_robustness_sets():
    _, versions = made_up_data(4)
    assert sentences_where_e_is_stripped(versions) == {1, 3}
    translations = pd.DataFrame(
        {"sent_id": [0, 1, 2], "version": "clean", "system": "llm", "src": "x",
         "hyp": ["Fine.", "The美国总统 said.", "Also fine."]}
    )
    assert sentences_in_another_script(translations) == {1}


def test_hypotheses_follow_the_intervals():
    scores, versions = made_up_data()
    drops, contrasts = drop_table(scores), contrast_table(scores)
    fit, gaps = regression(scores, versions), system_gap_table(scores)
    table = hypothesis_table(drops, contrasts, fit, gaps).set_index(["hypothesis", "system"])
    assert table.loc[("H1: removing all accents lowers quality", "nllb"), "supported"]
    assert table.loc[("H2: b_only costs more than a_only", "nllb"), "supported"]
    assert table.loc[("H3: typos cost less than b_only", "nllb"), "supported"]
    assert table.loc[("H6: the LLM loses less than the other systems", "llm vs nllb"), "supported"]


def test_run_writes_every_table_and_chart(tmp_path):
    scores = read_table("scores", fixtures=True)
    translations = read_table("translations", fixtures=True)
    versions = read_table("versions", fixtures=True)
    sentences = read_table("sentences", fixtures=True)
    tables = run(scores, translations, versions, sentences, None, tmp_path)
    assert {"drop_table", "contrasts", "regression", "hypotheses", "error_examples"} <= set(tables)
    assert (tmp_path / "summary.txt").exists()

    scores, versions = made_up_data()
    translations = pd.DataFrame(
        {"sent_id": scores["sent_id"], "version": scores["version"], "system": scores["system"],
         "src": "x", "hyp": "y"}
    ).drop_duplicates()
    sentences = pd.DataFrame({"sent_id": range(42), "pt": "x", "en": "y"})
    run(scores, translations, versions, sentences, None, tmp_path / "big")
    assert (tmp_path / "big" / "chart_drops.png").stat().st_size > 0
    assert (tmp_path / "big" / "chart_regression.png").stat().st_size > 0


def test_wilson_interval_stays_between_0_and_1_and_contains_the_share():
    from keyboard_tax.analyze import wilson_interval

    low, high = wilson_interval(pd.Series([186, 141, 0]), pd.Series([187, 187, 10]))
    assert (low >= 0).all() and (high <= 1).all()
    assert low[0] < 186 / 187 < high[0]
    assert round(low[1], 3) == 0.688 and round(high[1], 3) == 0.810
