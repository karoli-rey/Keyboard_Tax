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
import unicodedata

import pandas as pd

from keyboard_tax.common import load_config, write_table


def load_flores(source: str, target: str, split: str) -> pd.DataFrame:
    """Return one row per sentence: sent_id, pt (source), en (target reference)."""
    if not split or split.strip().upper() == "TODO":
        raise ValueError("Set the FLORES+ split in config.yaml before loading the dataset.")

    from datasets import load_dataset

    def load_language(language: str) -> dict[str, str]:
        rows = load_dataset("openlanguagedata/flores_plus", language, split=split)
        result = {}
        for row in rows:
            if "id" not in row or "text" not in row:
                raise ValueError(
                    f"FLORES+ rows must contain 'id' and 'text' fields, got {sorted(row)}."
                )
            sentence_id = row["id"]
            if sentence_id in result:
                raise ValueError(f"Duplicate FLORES+ sentence id {sentence_id!r} in {language}.")
            result[sentence_id] = unicodedata.normalize("NFC", row["text"])
        return result

    source_rows = load_language(source)
    target_rows = load_language(target)
    if source_rows.keys() != target_rows.keys():
        missing_target = source_rows.keys() - target_rows.keys()
        missing_source = target_rows.keys() - source_rows.keys()
        raise ValueError(
            "FLORES+ source and target IDs do not match "
            f"(missing target: {sorted(missing_target)[:5]}, "
            f"missing source: {sorted(missing_source)[:5]})."
        )

    return pd.DataFrame(
        [
            {"sent_id": index, "pt": sentence, "en": target_rows[sentence_id]}
            for index, (sentence_id, sentence) in enumerate(source_rows.items())
        ],
        columns=["sent_id", "pt", "en"],
    )


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description="Step 1: load FLORES+").parse_args(argv)
    config = load_config()
    sentences = load_flores(config["source_language"], config["target_language"], config["split"])
    print("Wrote", write_table(sentences, "sentences"))


if __name__ == "__main__":
    main()
