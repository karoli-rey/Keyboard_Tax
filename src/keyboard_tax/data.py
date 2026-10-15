"""Step 1: load the FLORES+ Portuguese sentences and their English translations.

Owner:  Coder 1
Input:  FLORES+ on Hugging Face (needs a login and accepted terms)
Output: outputs/1_sentences.csv  (columns: sent_id, pt, en)

To do:
    1. Load the source (Portuguese) and target (English) sentences for the split in
       config.yaml. FLORES+ has the same sentences in every language, in the same order.
    2. Put them side by side, one row per sentence, with a sent_id starting at 0.
    3. Write the table with write_table(df, "sentences").
"""

import argparse

import pandas as pd

from keyboard_tax.common import load_config, write_table


def load_flores(source: str, target: str, split: str) -> pd.DataFrame:
    """Return one row per sentence: sent_id, pt (source), en (target reference)."""
    raise NotImplementedError("Step 1 is not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description="Step 1: load FLORES+").parse_args(argv)
    config = load_config()
    sentences = load_flores(config["source_language"], config["target_language"], config["split"])
    print("Wrote", write_table(sentences, "sentences"))


if __name__ == "__main__":
    main()
