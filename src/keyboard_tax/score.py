"""Step 5: score every translation against the English reference.

Owner:  Coder 2
Input:  outputs/4_translations.csv, outputs/1_sentences.csv
Output: outputs/5_scores.csv         one row per translation: chrF and COMET
        outputs/5_corpus_scores.csv  one row per subset, version and system: BLEU, chrF,
                                     mean COMET

How it works:
    1. Each translation is joined with its English reference and with the CLEAN Portuguese
       sentence (by sent_id).
    2. Sentence level: chrF (sacreBLEU) and COMET. COMET always gets the clean Portuguese
       sentence as its source, never the damaged one: a damaged source would hide the damage.
    3. Corpus level: BLEU and chrF over all sentences of a version and system, and the mean
       COMET. Two subsets:
         "all"          every sentence that has this version
         "both_classes" only the sentences that have all five versions (Class A and Class B
                        words). Compare a_only, b_only and noise with clean on THIS subset.
    4. Identical translations are scored once. The sacreBLEU signatures are printed; copy
       them into the report (they are also in notes/olivia_steps_4-6_notes.md).

Try it:    python -m keyboard_tax.score --fixtures --skip-comet
Full run:  python -m keyboard_tax.score          (on a GPU: scripts/colab_gpu_run.ipynb)
"""

import argparse
from collections.abc import Callable

import pandas as pd

from keyboard_tax.common import TABLES, load_config, read_table, write_table

SUBSET_ALL = "all"
SUBSET_BOTH = "both_classes"
COMET_BATCH_SIZE = 32

# (hypotheses, references) -> one score per translation
ChrfFunction = Callable[[list[str], list[str]], list[float]]
# (clean sources, hypotheses, references) -> one score per translation
CometFunction = Callable[[list[str], list[str], list[str]], list[float]]
# (hypotheses, references) -> (BLEU, chrF) for the whole set
CorpusFunction = Callable[[list[str], list[str]], tuple[float, float]]


# ---------------------------------------------------------------- the metrics

def sentence_chrf(hypotheses: list[str], references: list[str]) -> list[float]:
    """chrF (0 to 100) of each translation against its reference."""
    from sacrebleu.metrics import CHRF

    metric = CHRF()
    return [
        metric.sentence_score(hypothesis, [reference]).score
        for hypothesis, reference in zip(hypotheses, references, strict=True)
    ]


def corpus_bleu_chrf(hypotheses: list[str], references: list[str]) -> tuple[float, float]:
    """BLEU and chrF (0 to 100) of a whole set of translations."""
    from sacrebleu.metrics import BLEU, CHRF

    bleu = BLEU().corpus_score(hypotheses, [references]).score
    chrf = CHRF().corpus_score(hypotheses, [references]).score
    return bleu, chrf


def sacrebleu_signatures() -> dict[str, str]:
    """The exact settings of BLEU and chrF, to report with the scores."""
    from sacrebleu.metrics import BLEU, CHRF

    signatures = {}
    for name, metric in (("BLEU", BLEU()), ("chrF", CHRF())):
        metric.corpus_score(["a"], [["a"]])  # the signature is complete after one use
        signatures[name] = str(metric.get_signature())
    return signatures


def make_comet(model_name: str) -> CometFunction:
    """Load the COMET model once and return a function that scores with it."""
    import torch
    from comet import download_model, load_from_checkpoint

    model = load_from_checkpoint(download_model(model_name))
    gpus = 1 if torch.cuda.is_available() else 0

    def comet(sources: list[str], hypotheses: list[str], references: list[str]) -> list[float]:
        data = [
            {"src": source, "mt": hypothesis, "ref": reference}
            for source, hypothesis, reference in zip(sources, hypotheses, references, strict=True)
        ]
        return list(model.predict(data, batch_size=COMET_BATCH_SIZE, gpus=gpus).scores)

    return comet


# ---------------------------------------------------------------- the step

def with_references(translations: pd.DataFrame, sentences: pd.DataFrame) -> pd.DataFrame:
    """Add the English reference (`ref`) and the clean Portuguese (`clean_src`) to each row."""
    lookup = sentences.rename(columns={"pt": "clean_src", "en": "ref"})
    joined = translations.merge(
        lookup[["sent_id", "clean_src", "ref"]], on="sent_id", how="left", validate="m:1"
    )
    missing = joined["ref"].isna()
    if missing.any():
        ids = sorted(joined.loc[missing, "sent_id"].unique())[:5]
        raise ValueError(f"No reference for sent_id {ids}. Do steps 1 and 4 use the same data?")
    joined["hyp"] = joined["hyp"].fillna("").astype(str)  # an empty translation scores low
    return joined


def score_sentences(
    translations: pd.DataFrame,
    sentences: pd.DataFrame,
    config: dict,
    chrf_function: ChrfFunction | None = None,
    comet_function: CometFunction | None = None,
    skip_comet: bool = False,
) -> pd.DataFrame:
    """chrF and COMET per translation (columns in common.TABLES["scores"]).

    The tests pass their own small functions instead of the real metrics. With
    skip_comet=True the COMET column stays empty (for a try-out without a GPU).
    """
    joined = with_references(translations, sentences)
    # Many versions get the same translation: score each distinct case once.
    cases = joined[["clean_src", "hyp", "ref"]].drop_duplicates().reset_index(drop=True)
    hypotheses, references = cases["hyp"].tolist(), cases["ref"].tolist()
    cases["chrf"] = (chrf_function or sentence_chrf)(hypotheses, references)
    if skip_comet:
        cases["comet"] = float("nan")
    else:
        comet = comet_function or make_comet(config["comet_model"])
        cases["comet"] = comet(cases["clean_src"].tolist(), hypotheses, references)
    scored = joined.merge(cases, on=["clean_src", "hyp", "ref"], how="left", validate="m:1")
    return scored[TABLES["scores"][1]]


def score_corpus(
    translations: pd.DataFrame,
    sentences: pd.DataFrame,
    scores: pd.DataFrame,
    corpus_function: CorpusFunction | None = None,
) -> pd.DataFrame:
    """BLEU, chrF and mean COMET per subset, version and system."""
    joined = with_references(translations, sentences)
    keys = ["sent_id", "version", "system"]
    if not joined[keys].reset_index(drop=True).equals(scores[keys].reset_index(drop=True)):
        raise ValueError("`scores` must have the same rows in the same order as `translations`.")
    joined["comet"] = scores["comet"].to_numpy()
    versions_per_sentence = joined.groupby("sent_id")["version"].nunique()
    in_all_versions = versions_per_sentence[
        versions_per_sentence == joined["version"].nunique()
    ].index
    subsets = {SUBSET_ALL: joined, SUBSET_BOTH: joined[joined["sent_id"].isin(in_all_versions)]}
    measure = corpus_function or corpus_bleu_chrf
    rows = []
    for subset, table in subsets.items():
        for (version, system), group in table.groupby(["version", "system"], sort=False):
            bleu, chrf = measure(group["hyp"].tolist(), group["ref"].tolist())
            rows.append(
                {
                    "subset": subset,
                    "version": version,
                    "system": system,
                    "n": len(group),
                    "bleu": bleu,
                    "chrf": chrf,
                    "comet": group["comet"].mean(),
                }
            )
    return pd.DataFrame(rows, columns=TABLES["corpus_scores"][1])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 5: score")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    parser.add_argument(
        "--skip-comet",
        action="store_true",
        help="only chrF and BLEU; the COMET column stays empty (try-out without a GPU)",
    )
    args = parser.parse_args(argv)
    config = load_config()
    translations = read_table("translations", fixtures=args.fixtures)
    sentences = read_table("sentences", fixtures=args.fixtures)
    scores = score_sentences(translations, sentences, config, skip_comet=args.skip_comet)
    print("Wrote", write_table(scores, "scores"))
    corpus = score_corpus(translations, sentences, scores)
    print("Wrote", write_table(corpus, "corpus_scores"))
    print(corpus.round(3).to_string(index=False))
    for name, signature in sacrebleu_signatures().items():
        print(f"sacreBLEU signature, {name}: {signature}")
    if args.skip_comet:
        print("COMET was skipped. Run without --skip-comet on a GPU for the full scores.")


if __name__ == "__main__":
    main()
