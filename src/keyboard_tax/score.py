"""Step 5: score every translation against the English reference.

Owner:  Coder 2
Input:  outputs/4_translations.csv, outputs/1_sentences.csv
Output: outputs/5_scores.csv         one row per translation: chrF and COMET
        outputs/5_corpus_scores.csv  one row per version and system: BLEU, chrF, COMET

To do:
    1. Join each translation with its English reference and clean Portuguese source.
    2. Sentence level: chrF and COMET. COMET always gets the CLEAN Portuguese
       sentence as its source, never the damaged one.
    3. Corpus level: BLEU and chrF per version and system; mean COMET.
    4. Write both tables; save the sacreBLEU signature in notes/decisions.md.
"""

import argparse

import pandas as pd

from keyboard_tax.common import load_config, read_table, write_table


def score_sentences(
    translations: pd.DataFrame, sentences: pd.DataFrame, config: dict
) -> pd.DataFrame:
    """chrF and COMET per translation (columns in common.TABLES["scores"])."""
    raise NotImplementedError("Step 5 is not implemented yet. See the to-do list above.")


def score_corpus(
    translations: pd.DataFrame, sentences: pd.DataFrame, scores: pd.DataFrame
) -> pd.DataFrame:
    """BLEU, chrF and mean COMET per version and system."""
    raise NotImplementedError("Step 5 is not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 5: score")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    config = load_config()
    translations = read_table("translations", fixtures=args.fixtures)
    sentences = read_table("sentences", fixtures=args.fixtures)
    scores = score_sentences(translations, sentences, config)
    print("Wrote", write_table(scores, "scores"))
    corpus = score_corpus(translations, sentences, scores)
    print("Wrote", write_table(corpus, "corpus_scores"))


if __name__ == "__main__":
    main()
