"""Step 6: compare versions and systems; make the tables and charts for the report.

Owner:  Coder 2
Input:  outputs/5_scores.csv, outputs/4_translations.csv, outputs/3_versions.csv,
        outputs/1_sentences.csv, data/challenge_set.csv (optional)
Output: outputs/6_results/  (tables as CSV, charts as PNG, a summary as text)

What it computes. "Drop" always means clean minus damaged, per sentence, so a positive
number is a loss. Every mean comes with a 95% confidence interval (CI); a paired
difference whose CI excludes 0 counts as a real difference.
    1. drop_table:      mean drop per version and system. a_only, b_only and noise are
                        compared with clean on the sentences that have all five versions.
    2. contrast_table:  the paired differences our hypotheses are about, e.g. b_only minus
                        a_only in the same sentence, with a CI.
    3. regression:      drop = b0 + b1 * B words + b2 * A words + b3 * changed letters,
                        one fit per system on all damaged versions including noise, with
                        standard errors clustered by sentence (each sentence appears in
                        several versions). Caution: in our data "A words" and "changed
                        letters" move almost together (nearly one letter per A word), so the
                        fit cannot separate them well. The contrasts in 2 are the main test;
                        the regression is reported as planned, with this caveat.
    4. targeted_check:  for each challenge sentence, does the English contain the right
                        reading or the wrong one? Only where the word really lost its accent.
                        bleu_versus_targeted compares that loss with the BLEU loss on the
                        same sentences (H5: does BLEU hide the damage?).
    5. robustness:      1 and 2 again without the sentences whose stripped Class B word is
                        "é", and without the sentences the LLM answered in another script.
    6. hypotheses:      H1 to H6 (and H2b) from the plan, each marked supported or not.

Run:  python -m keyboard_tax.analyze              (seconds, no GPU)
      python -m keyboard_tax.analyze --fixtures   (on the example data)
"""

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from keyboard_tax.common import RESULTS_DIR, ROOT, read_table

SAVED_RESULTS_DIR = ROOT / "results"

METRICS = ["comet", "chrf"]
MAIN_METRIC = "comet"
DAMAGED = ["stripped_100", "a_only", "b_only", "noise"]
FIVE_VERSIONS = ["clean", "stripped_100", "a_only", "b_only", "noise"]
Z95 = 1.96  # half-width of a 95% interval in standard errors
OTHER_SCRIPT = re.compile(r"[぀-ヿ㐀-鿿가-힯]")  # CJK characters


# ---------------------------------------------------------------- helpers

def mean_with_interval(values: pd.Series) -> tuple[float, float, float]:
    """Mean and 95% confidence interval (normal approximation; n is in the hundreds)."""
    values = values.dropna()
    n = len(values)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    mean = float(values.mean())
    half = Z95 * float(values.std(ddof=1)) / np.sqrt(n) if n > 1 else float("nan")
    return mean, mean - half, mean + half


def sentence_drops(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per damaged version, system and sentence: drop = clean minus damaged."""
    clean = scores[scores["version"] == "clean"].set_index(["system", "sent_id"])[METRICS]
    damaged = scores[scores["version"] != "clean"].set_index(["system", "sent_id"])
    drops = damaged[["version"]].copy()
    for metric in METRICS:
        drops[f"{metric}_drop"] = clean[metric].reindex(damaged.index) - damaged[metric]
    return drops.reset_index()


def sentences_with_all_versions(scores: pd.DataFrame) -> pd.Index:
    """The sentences that have every one of the five versions (both classes present)."""
    counts = scores.groupby("sent_id")["version"].nunique()
    return counts[counts == len(FIVE_VERSIONS)].index


# ---------------------------------------------------------------- 1. drops

def drop_table(scores: pd.DataFrame) -> pd.DataFrame:
    """Mean drop per version and system, with a 95% CI, on two subsets.

    "all": every sentence that has the version. "both_classes": only the sentences with
    all five versions, so that a_only, b_only and noise are compared on equal ground.
    """
    drops = sentence_drops(scores)
    both = sentences_with_all_versions(scores)
    rows = []
    for subset, table in (("all", drops), ("both_classes", drops[drops["sent_id"].isin(both)])):
        for (system, version), group in table.groupby(["system", "version"], sort=False):
            row = {"subset": subset, "system": system, "version": version, "n": len(group)}
            for metric in METRICS:
                mean, low, high = mean_with_interval(group[f"{metric}_drop"])
                row.update({f"{metric}_drop": mean, f"{metric}_low": low, f"{metric}_high": high})
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 2. contrasts

CONTRASTS = [  # (name, version A, version B): the mean of (drop A minus drop B)
    ("b_only minus a_only", "b_only", "a_only"),
    ("b_only minus noise", "b_only", "noise"),
    ("noise minus a_only", "noise", "a_only"),
]


def contrast_table(scores: pd.DataFrame) -> pd.DataFrame:
    """Paired differences between two versions of the same sentence, with a 95% CI."""
    drops = sentence_drops(scores)
    drops = drops[drops["sent_id"].isin(sentences_with_all_versions(scores))]
    wide = drops.pivot(index=["system", "sent_id"], columns="version")
    rows = []
    for system in drops["system"].unique():
        for name, first, second in CONTRASTS:
            row = {"system": system, "contrast": name}
            for metric in METRICS:
                diff = wide.loc[system, (f"{metric}_drop", first)] - wide.loc[
                    system, (f"{metric}_drop", second)
                ]
                mean, low, high = mean_with_interval(diff)
                row.update({f"{metric}_diff": mean, f"{metric}_low": low, f"{metric}_high": high})
                row["n"] = int(diff.notna().sum())
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 3. regression

def clustered_regression(
    y: np.ndarray, x: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Least squares with standard errors clustered by group (same formula as statsmodels).

    Returns (coefficients, standard errors). The first column of `x` is the constant.
    """
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    bread = np.linalg.pinv(x.T @ x)  # pinv: no crash when two predictors are redundant
    meat = np.zeros((x.shape[1], x.shape[1]))
    for group in np.unique(groups):
        rows = groups == group
        score = x[rows].T @ residuals[rows]
        meat += np.outer(score, score)
    n, k, g = len(y), x.shape[1], len(np.unique(groups))
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    covariance = correction * bread @ meat @ bread
    return beta, np.sqrt(np.diag(covariance))


def regression(
    scores: pd.DataFrame, versions: pd.DataFrame, metric: str = MAIN_METRIC
) -> pd.DataFrame:
    """drop = b0 + b1 * B words + b2 * A words + b3 * changed letters, one fit per system."""
    drops = sentence_drops(scores).merge(
        versions[["sent_id", "version", "n_a", "n_b", "n_chars"]], on=["sent_id", "version"]
    )
    names = ["b0 (constant)", "b1 (B words)", "b2 (A words)", "b3 (changed letters)"]
    rows = []
    for system, group in drops.groupby("system", sort=False):
        if group["sent_id"].nunique() < 10:  # too few sentences for a meaningful fit
            continue
        y = group[f"{metric}_drop"].to_numpy(dtype=float)
        x = np.column_stack(
            [np.ones(len(group)), group["n_b"], group["n_a"], group["n_chars"]]
        ).astype(float)
        beta, se = clustered_regression(y, x, group["sent_id"].to_numpy())
        for name, b, s in zip(names, beta, se, strict=True):
            rows.append(
                {
                    "system": system,
                    "metric": metric,
                    "term": name,
                    "estimate": b,
                    "low": b - Z95 * s,
                    "high": b + Z95 * s,
                    "n": len(group),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4. targeted check

def pattern(words: str) -> re.Pattern:
    """A regex that matches any of the words in "could|was able", as whole words."""
    choices = [re.escape(word.strip()) for word in str(words).split("|") if word.strip()]
    return re.compile(r"\b(?:" + "|".join(choices) + r")\b", re.IGNORECASE)


def verdict(hypothesis: str, correct: re.Pattern, wrong: re.Pattern) -> str:
    """"right", "wrong" or "unclear" for one English translation."""
    has_right, has_wrong = bool(correct.search(hypothesis)), bool(wrong.search(hypothesis))
    if has_right and not has_wrong:
        return "right"
    if has_wrong and not has_right:
        return "wrong"
    return "unclear"


def targeted_check(
    translations: pd.DataFrame, challenge_set: pd.DataFrame, versions: pd.DataFrame
) -> pd.DataFrame:
    """One row per challenge sentence, version and system.

    `stripped` says whether the challenge word really lost its accent in that version;
    a_only and b_only strip only some words, so the check only counts stripped rows.
    """
    source = versions.set_index(["sent_id", "version"])["src"]
    rows = []
    for challenge in challenge_set.itertuples(index=False):
        correct, wrong = pattern(challenge.correct_pattern), pattern(challenge.wrong_pattern)
        word = re.compile(r"\b" + re.escape(challenge.word) + r"\b", re.IGNORECASE)
        for row in translations[translations["sent_id"] == challenge.sent_id].itertuples():
            text = source.get((row.sent_id, row.version), row.src)
            rows.append(
                {
                    "sent_id": row.sent_id,
                    "word": challenge.word,
                    "version": row.version,
                    "system": row.system,
                    "stripped": row.version != "clean" and not word.search(str(text)),
                    "verdict": verdict(str(row.hyp), correct, wrong),
                }
            )
    return pd.DataFrame(
        rows, columns=["sent_id", "word", "version", "system", "stripped", "verdict"]
    )


def targeted_summary(check: pd.DataFrame) -> pd.DataFrame:
    """Share of right / wrong / unclear per version and system.

    clean rows are the baseline; damaged rows count only where the word was stripped.
    """
    counted = check[(check["version"] == "clean") | check["stripped"]]
    summary = (
        counted.groupby(["system", "version", "verdict"]).size().unstack(fill_value=0)
    )
    for column in ("right", "wrong", "unclear"):
        summary[column] = summary.get(column, 0)
    summary["n"] = summary[["right", "wrong", "unclear"]].sum(axis=1)
    summary["accuracy"] = summary["right"] / summary["n"]
    columns = ["system", "version", "n", "right", "wrong", "unclear", "accuracy"]
    return summary.reset_index()[columns]


def targeted_by_loss(check: pd.DataFrame, lexicon: pd.DataFrame) -> pd.DataFrame:
    """targeted_summary per kind of loss, taken from the lexicon's `lost` column.

    "meaning (bay to stall)" counts as "meaning"; the kinds are meaning, tense, word class,
    verb form and so on, as the native speaker wrote them.
    """
    kind = lexicon.set_index("word")["lost"].fillna("").str.split("(").str[0].str.strip()
    check = check.assign(loss=check["word"].map(kind).replace("", "other").fillna("other"))
    parts = [
        targeted_summary(group).assign(loss=loss) for loss, group in check.groupby("loss")
    ]
    if not parts:
        return pd.DataFrame()
    table = pd.concat(parts, ignore_index=True)
    return table[["loss"] + [c for c in table.columns if c != "loss"]]


# ---------------------------------------------------------------- 5. robustness

def sentences_where_e_is_stripped(versions: pd.DataFrame) -> set[int]:
    """Sentences whose b_only version strips "é" (the most common Class B word)."""
    pairs = versions[versions["version"].isin(["clean", "b_only"])].pivot(
        index="sent_id", columns="version", values="src"
    )
    pairs = pairs.dropna()
    found = set()
    e_word = re.compile(r"\bé\b", re.IGNORECASE)
    for sent_id, clean, b_only in pairs[["clean", "b_only"]].itertuples():
        if len(e_word.findall(clean)) > len(e_word.findall(b_only)):
            found.add(sent_id)
    return found


def sentences_in_another_script(translations: pd.DataFrame) -> set[int]:
    """Sentences that some system translated (partly) in Chinese, Japanese or Korean."""
    hits = translations["hyp"].fillna("").str.contains(OTHER_SCRIPT, regex=True)
    return set(translations.loc[hits, "sent_id"])


# ---------------------------------------------------------------- 6. hypotheses

def excludes_zero(low: float, high: float) -> bool:
    return bool(low > 0 or high < 0)


def system_gap_table(scores: pd.DataFrame, version: str = "stripped_100") -> pd.DataFrame:
    """Paired difference in drop between systems on the same sentence, with a 95% CI."""
    drops = sentence_drops(scores)
    wide = drops[drops["version"] == version].pivot(
        index="sent_id", columns="system", values=f"{MAIN_METRIC}_drop"
    )
    rows = []
    systems = list(wide.columns)
    for first in systems:
        for second in systems:
            if first < second:
                mean, low, high = mean_with_interval(wide[first] - wide[second])
                rows.append(
                    {
                        "version": version,
                        "systems": f"{first} minus {second}",
                        "diff": mean,
                        "low": low,
                        "high": high,
                        "n": int(wide[[first, second]].dropna().shape[0]),
                    }
                )
    return pd.DataFrame(rows)


def bleu_versus_targeted(
    translations: pd.DataFrame,
    sentences: pd.DataFrame,
    check: pd.DataFrame,
    version: str = "stripped_100",
    corpus_function=None,
) -> pd.DataFrame:
    """RQ3 / H5: on the challenge sentences, BLEU and chrF against the targeted check.

    Both compare clean with `version` on the same items (where the word lost its accent).
    "drop share" = (clean minus damaged) / clean. The accuracy drop gets a 95% CI.
    """
    if corpus_function is None:
        from keyboard_tax.score import corpus_bleu_chrf as corpus_function
    references = sentences.set_index("sent_id")["en"]
    items = check[(check["version"] == version) & check["stripped"]]
    rows = []
    for system in systems_in(items):
        keys = list(items.loc[items["system"] == system, ["sent_id", "word"]].itertuples(
            index=False, name=None
        ))
        ids = sorted({sent_id for sent_id, _ in keys})
        hyps = translations[translations["system"] == system].set_index(["version", "sent_id"])[
            "hyp"
        ]
        refs = [references[i] for i in ids]
        bleu_clean, chrf_clean = corpus_function([hyps[("clean", i)] for i in ids], refs)
        bleu_damaged, chrf_damaged = corpus_function([hyps[(version, i)] for i in ids], refs)
        verdicts = check[check["system"] == system].set_index(["sent_id", "word", "version"])[
            "verdict"
        ]
        right = {
            v: pd.Series([verdicts[(s, w, v)] == "right" for s, w in keys], dtype=float)
            for v in ("clean", version)
        }
        accuracy_clean = right["clean"].mean()
        drop, low, high = mean_with_interval(right["clean"] - right[version])
        rows.append(
            {
                "system": system,
                "version": version,
                "n_items": len(keys),
                "n_sentences": len(ids),
                "bleu_clean": bleu_clean,
                "bleu_damaged": bleu_damaged,
                "bleu_drop_share": (bleu_clean - bleu_damaged) / bleu_clean,
                "chrf_drop_share": (chrf_clean - chrf_damaged) / chrf_clean,
                "accuracy_clean": accuracy_clean,
                "accuracy_damaged": right[version].mean(),
                "accuracy_drop_share": drop / accuracy_clean,
                "accuracy_drop_low": low / accuracy_clean,
                "accuracy_drop_high": high / accuracy_clean,
            }
        )
    return pd.DataFrame(rows)


def hypothesis_table(
    drops: pd.DataFrame,
    contrasts: pd.DataFrame,
    fit: pd.DataFrame,
    gaps: pd.DataFrame,
    contrasts_without_e: pd.DataFrame | None = None,
    bleu_check: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """H1 to H6 from the plan, checked on the main metric; 'supported' per system.

    H2b needs the contrasts without "é", H5 the BLEU-versus-targeted table; each is
    skipped when its table is missing.
    """
    rows = []
    if fit.empty or contrasts.empty:
        return pd.DataFrame(rows, columns=["hypothesis", "system", "supported", "detail"])
    for system in drops["system"].unique():
        d = drops[(drops["system"] == system) & (drops["subset"] == "all")].set_index("version")
        c = contrasts[contrasts["system"] == system].set_index("contrast")
        f = fit[fit["system"] == system].set_index("term")
        if f.empty or c.empty:
            continue
        tests = {
            "H1: removing all accents lowers quality": (
                d.loc["stripped_100", f"{MAIN_METRIC}_low"] > 0,
                f"drop {d.loc['stripped_100', f'{MAIN_METRIC}_drop']:.4f}",
            ),
            "H2: b_only costs more than a_only": (
                c.loc["b_only minus a_only", f"{MAIN_METRIC}_low"] > 0,
                f"diff {c.loc['b_only minus a_only', f'{MAIN_METRIC}_diff']:.4f}",
            ),
            "H3: typos cost less than b_only": (
                c.loc["b_only minus noise", f"{MAIN_METRIC}_low"] > 0,
                f"diff {c.loc['b_only minus noise', f'{MAIN_METRIC}_diff']:.4f}",
            ),
            "H4: b1 > b2 and b3 near zero": (
                f.loc["b1 (B words)", "low"] > f.loc["b2 (A words)", "high"]
                and not excludes_zero(
                    f.loc["b3 (changed letters)", "low"], f.loc["b3 (changed letters)", "high"]
                ),
                (
                    f"b1 {f.loc['b1 (B words)', 'estimate']:.4f}, "
                    f"b2 {f.loc['b2 (A words)', 'estimate']:.4f}, "
                    f"b3 {f.loc['b3 (changed letters)', 'estimate']:.4f} "
                    "(A words and changed letters are collinear: read with care)"
                ),
            ),
        }
        if contrasts_without_e is not None and len(contrasts_without_e):
            e = contrasts_without_e[contrasts_without_e["system"] == system].set_index(
                "contrast"
            ).loc["b_only minus a_only"]
            tests["H2b: H2 without 'é'"] = (
                e[f"{MAIN_METRIC}_low"] > 0,
                (
                    f"diff {e[f'{MAIN_METRIC}_diff']:.4f} [{e[f'{MAIN_METRIC}_low']:.4f}, "
                    f"{e[f'{MAIN_METRIC}_high']:.4f}], {int(e['n'])} sentences"
                ),
            )
        if bleu_check is not None and len(bleu_check) and system in set(bleu_check["system"]):
            b = bleu_check.set_index("system").loc[system]
            tests["H5: BLEU hides the B damage"] = (
                b["accuracy_drop_low"] > b["bleu_drop_share"],
                (
                    f"targeted accuracy falls {b['accuracy_drop_share']:.0%} "
                    f"[{b['accuracy_drop_low']:.0%}, {b['accuracy_drop_high']:.0%}], "
                    f"BLEU {b['bleu_drop_share']:.0%}"
                ),
            )
        for name, (supported, detail) in tests.items():
            rows.append(
                {"hypothesis": name, "system": system, "supported": bool(supported),
                 "detail": detail}
            )
    if "llm" in set(drops["system"]):
        for row in gaps.itertuples():
            if "llm" in row.systems:
                other = row.systems.replace("llm", "").replace("minus", "").strip()
                llm_first = row.systems.startswith("llm")
                diff = row.diff if llm_first else -row.diff
                low, high = (row.low, row.high) if llm_first else (-row.high, -row.low)
                rows.append(
                    {
                        "hypothesis": "H6: the LLM loses less than the other systems",
                        "system": f"llm vs {other}",
                        "supported": bool(high < 0),
                        "detail": f"llm drop minus {other} drop {diff:.4f} [{low:.4f}, {high:.4f}]",
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- charts

SYSTEM_COLORS = {"nllb": "#1f77b4", "opus_mt": "#ff7f0e", "llm": "#2ca02c"}
SYSTEM_NAMES = {"nllb": "NLLB", "opus_mt": "Opus-MT", "llm": "LLM (Qwen2.5)"}
VERSION_LABELS = {
    "clean": "clean",
    "stripped_100": "all removed",
    "a_only": "Class A only",
    "b_only": "Class B only",
    "noise": "typos",
}


def systems_in(table: pd.DataFrame) -> list[str]:
    """The systems of a table in a fixed order, so every chart uses the same colours."""
    found = set(table["system"])
    return [s for s in SYSTEM_COLORS if s in found] + sorted(found - set(SYSTEM_COLORS))


def chart_drops(drops: pd.DataFrame, path: Path) -> None:
    """Mean COMET drop per version, one bar group per system, with CIs."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    table = drops[drops["subset"] == "both_classes"]
    systems = systems_in(table)
    if not systems:  # no sentence has all five versions (tiny data)
        return
    fig, ax = plt.subplots(figsize=(7, 3.6))
    width = 0.8 / len(systems)
    for i, system in enumerate(systems):
        rows = table[table["system"] == system].set_index("version").reindex(DAMAGED)
        x = np.arange(len(DAMAGED)) + i * width
        errors = np.vstack(
            [rows[f"{MAIN_METRIC}_drop"] - rows[f"{MAIN_METRIC}_low"],
             rows[f"{MAIN_METRIC}_high"] - rows[f"{MAIN_METRIC}_drop"]]
        )
        ax.bar(
            x, rows[f"{MAIN_METRIC}_drop"], width, yerr=errors, capsize=3,
            label=SYSTEM_NAMES.get(system, system),
            color=SYSTEM_COLORS.get(system),
        )
    ax.set_xticks(np.arange(len(DAMAGED)) + width * (len(systems) - 1) / 2)
    ax.set_xticklabels([VERSION_LABELS[v] for v in DAMAGED])
    ax.set_ylabel("COMET drop (clean minus damaged)")
    n = int(table["n"].max())
    ax.set_title(f"Quality loss per kind of damage, {n} sentences, 95% CI")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_regression(fit: pd.DataFrame, path: Path) -> None:
    """Coefficients b1, b2, b3 per system with CIs."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    terms = ["b1 (B words)", "b2 (A words)", "b3 (changed letters)"]
    fit = fit[fit["metric"] == MAIN_METRIC] if "metric" in fit else fit
    systems = systems_in(fit)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for i, system in enumerate(systems):
        rows = fit[fit["system"] == system].set_index("term").reindex(terms)
        x = np.arange(len(terms)) + (i - (len(systems) - 1) / 2) * 0.2
        ax.errorbar(
            x, rows["estimate"],
            yerr=[rows["estimate"] - rows["low"], rows["high"] - rows["estimate"]],
            fmt="o", capsize=3, label=SYSTEM_NAMES.get(system, system),
            color=SYSTEM_COLORS.get(system),
        )
    ax.set_xticks(np.arange(len(terms)))
    ax.set_xticklabels(["per Class B word", "per Class A word", "per changed letter"])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("COMET drop")
    ax.set_title(
        "Regression, 95% CI. A words and changed letters are collinear:\n"
        "the split between them is not reliable",
        fontsize=10,
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def wilson_interval(right: pd.Series, n: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """95% Wilson interval for a share: stays within 0 and 1, also for shares near 100%."""
    right, n = np.asarray(right, dtype=float), np.asarray(n, dtype=float)
    share = right / n
    centre = (share + Z95**2 / (2 * n)) / (1 + Z95**2 / n)
    half = Z95 * np.sqrt(share * (1 - share) / n + Z95**2 / (4 * n**2)) / (1 + Z95**2 / n)
    return np.clip(centre - half, 0, 1), np.clip(centre + half, 0, 1)


def chart_targeted(summary: pd.DataFrame, path: Path) -> None:
    """Accuracy on the challenge set per version and system, with 95% Wilson intervals."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    versions = [v for v in FIVE_VERSIONS if v in set(summary["version"])]
    systems = systems_in(summary)
    counts = summary.groupby("version")["n"].max()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    width = 0.8 / len(systems)
    for i, system in enumerate(systems):
        rows = summary[summary["system"] == system].set_index("version").reindex(versions)
        low, high = wilson_interval(rows["right"], rows["n"])
        errors = np.vstack([rows["accuracy"] - low, high - rows["accuracy"]])
        ax.bar(
            np.arange(len(versions)) + i * width, rows["accuracy"], width, yerr=errors,
            capsize=3, label=SYSTEM_NAMES.get(system, system), color=SYSTEM_COLORS.get(system),
        )
    ax.set_xticks(np.arange(len(versions)) + width * (len(systems) - 1) / 2)
    ax.set_xticklabels([f"{VERSION_LABELS[v]}\n(n = {counts[v]})" for v in versions])
    ax.set_ylim(0, 1.15)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_ylabel("share of right readings")
    ax.set_title("Challenge set: does the English keep the meaning? (95% CI)")
    ax.legend(frameon=False, ncol=len(systems), loc="upper center")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- the step

def error_examples(
    translations: pd.DataFrame, scores: pd.DataFrame, sentences: pd.DataFrame, count: int = 10
) -> pd.DataFrame:
    """The b_only cases with the largest COMET drop: candidates for the report's examples."""
    drops = sentence_drops(scores)
    worst = (
        drops[drops["version"] == "b_only"]
        .sort_values(f"{MAIN_METRIC}_drop", ascending=False)
        .head(count)[["system", "sent_id", f"{MAIN_METRIC}_drop"]]
    )
    hyps = translations.set_index(["system", "sent_id", "version"])["hyp"]
    srcs = translations.set_index(["sent_id", "version"])["src"].drop_duplicates()
    refs = sentences.set_index("sent_id")["en"]
    rows = []
    for row in worst.itertuples(index=False):
        rows.append(
            {
                "system": row.system,
                "sent_id": row.sent_id,
                "comet_drop": getattr(row, f"{MAIN_METRIC}_drop"),
                "clean_src": srcs.get((row.sent_id, "clean")),
                "b_only_src": srcs.get((row.sent_id, "b_only")),
                "reference": refs.get(row.sent_id),
                "clean_hyp": hyps.get((row.system, row.sent_id, "clean")),
                "b_only_hyp": hyps.get((row.system, row.sent_id, "b_only")),
            }
        )
    return pd.DataFrame(rows)


def run(
    scores: pd.DataFrame,
    translations: pd.DataFrame,
    versions: pd.DataFrame,
    sentences: pd.DataFrame,
    challenge_set: pd.DataFrame | None,
    results_dir: Path,
    lexicon: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Compute every table, write all files, return the tables."""
    results_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "drop_table": drop_table(scores),
        "contrasts": contrast_table(scores),
        "regression": regression(scores, versions),
        "system_gaps": system_gap_table(scores),
        "error_examples": error_examples(translations, scores, sentences),
    }
    without_e = sentences_where_e_is_stripped(versions)
    other_script = sentences_in_another_script(translations)
    for name, excluded in (("without_e", without_e), ("without_other_script", other_script)):
        kept = scores[~scores["sent_id"].isin(excluded)]
        tables[f"drop_table_{name}"] = drop_table(kept)
        tables[f"contrasts_{name}"] = contrast_table(kept)
    if challenge_set is not None and len(challenge_set):
        check = targeted_check(translations, challenge_set, versions)
        tables["targeted_check"] = check
        tables["targeted_summary"] = targeted_summary(check)
        if lexicon is not None:
            tables["targeted_by_loss"] = targeted_by_loss(check, lexicon)
        try:
            tables["bleu_vs_targeted"] = bleu_versus_targeted(translations, sentences, check)
        except ImportError:
            print("sacrebleu is not installed, so H5 is skipped: pip install sacrebleu")
    tables["hypotheses"] = hypothesis_table(
        tables["drop_table"],
        tables["contrasts"],
        tables["regression"],
        tables["system_gaps"],
        tables["contrasts_without_e"],
        tables.get("bleu_vs_targeted"),
    )
    for name, table in tables.items():
        table.to_csv(results_dir / f"{name}.csv", index=False)
    chart_drops(tables["drop_table"], results_dir / "chart_drops.png")
    if len(tables["regression"]):
        chart_regression(tables["regression"], results_dir / "chart_regression.png")
    if "targeted_summary" in tables:
        chart_targeted(tables["targeted_summary"], results_dir / "chart_targeted.png")
    left_out = (
        f"Sentences left out in the robustness checks: {len(without_e)} where 'é' is "
        f"stripped, {len(other_script)} with a translation in another script."
    )
    hypotheses = tables["hypotheses"]
    summary = [
        left_out,
        "",
        "Mean COMET drop, sentences with all five versions (positive = quality lost):",
        tables["drop_table"][tables["drop_table"]["subset"] == "both_classes"]
        .pivot(index="version", columns="system", values="comet_drop")
        .reindex(DAMAGED)
        .round(4)
        .to_string(),
        "",
        "Hypotheses (main metric: COMET, 95% CI):",
        hypotheses.to_string(index=False) if len(hypotheses) else "(too few sentences)",
    ]
    if "targeted_summary" in tables:
        summary += [
            "",
            "Challenge set, share of right readings (only rows where the word lost its accent):",
            tables["targeted_summary"]
            .pivot(index="version", columns="system", values="accuracy")
            .round(3)
            .to_string(),
        ]
    (results_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return tables


SAVED_TABLES = [
    "targeted_check", "targeted_summary", "targeted_by_loss", "bleu_vs_targeted",
    "contrasts_without_e", "contrasts_without_other_script",
]


def save_results(
    tables: dict[str, pd.DataFrame],
    scores: pd.DataFrame,
    versions: pd.DataFrame,
    corpus_scores: pd.DataFrame,
    folder: Path,
) -> None:
    """Write the tables that results.ipynb needs to results/ (committed).

    Numbers only, no sentences: FLORES+ asks that its text stays behind its login, so the
    notebook can be run by anyone without downloading the data or a model.
    """
    folder.mkdir(parents=True, exist_ok=True)
    scores.to_csv(folder / "scores.csv", index=False)
    corpus_scores.to_csv(folder / "corpus_scores.csv", index=False)
    versions.drop(columns="src").to_csv(folder / "version_counts.csv", index=False)
    for name in SAVED_TABLES:
        if name in tables:
            tables[name].to_csv(folder / f"{name}.csv", index=False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 6: analyze")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="also write the tables for results.ipynb to results/ (numbers only, no sentences)",
    )
    args = parser.parse_args(argv)
    scores = read_table("scores", fixtures=args.fixtures)
    translations = read_table("translations", fixtures=args.fixtures)
    versions = read_table("versions", fixtures=args.fixtures)
    sentences = read_table("sentences", fixtures=args.fixtures)
    try:
        challenge_set = read_table("challenge_set", fixtures=args.fixtures)
    except FileNotFoundError:
        challenge_set = None
        print("No data/challenge_set.csv yet: the targeted check is skipped.")
    lexicon = read_table("lexicon", fixtures=args.fixtures)
    results_dir = RESULTS_DIR if not args.fixtures else RESULTS_DIR / "fixtures"
    tables = run(scores, translations, versions, sentences, challenge_set, results_dir, lexicon)
    print((results_dir / "summary.txt").read_text(encoding="utf-8"))
    if args.save_results:
        corpus_scores = read_table("corpus_scores", fixtures=args.fixtures)
        save_results(tables, scores, versions, corpus_scores, SAVED_RESULTS_DIR)
        print("Wrote the tables for results.ipynb to", SAVED_RESULTS_DIR)
    print("Wrote results to", results_dir)


if __name__ == "__main__":
    main()
