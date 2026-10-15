"""Step 2: label every accented word as Class A or Class B, automatically.

Class A: without its diacritics, the word is NOT a real word   (não  -> nao)
Class B: without its diacritics, the word IS a real word       (pôde -> pode)

Owner:  Coder 1. Every change here gets a second reader before merging.
Input:  outputs/1_sentences.csv
Output: outputs/2_letters.csv       every accented letter and what it becomes
        outputs/2_lexicon_auto.csv  every accented word with its automatic label

Then the native speaker checks the letters list once, reviews the words marked
needs_review, and saves the corrected word list as data/lexicon.csv (see data/README.md).
Step 3 reads only that reviewed file, so rerunning this step never overwrites the review.

To do:
    1. find_accented_words(): every distinct lowercased word with a diacritic. Skip names.
    2. load_is_word(): ask the Hunspell dictionary with spylls, Dictionary.lookup().
       Never read the .dic file as a word list: it holds stems, not inflected forms,
       so "tem" (from "ter") would be missing and "têm" would wrongly become Class A.
    3. zipf: frequency of the stripped form (wordfreq), only used to flag rare words.
    4. needs_review: True for Class B words with zipf < min_zipf, plus `review_sample`
       other words at random (so we can report how accurate the automatic labels are).
"""

import argparse
from collections import Counter
from collections.abc import Callable

import pandas as pd

from keyboard_tax.common import load_config, normalize, read_table, strip_diacritics, write_table


def letter_table(texts: list[str]) -> pd.DataFrame:
    """Every non-ASCII letter in `texts`: what it becomes, how often, and a status.

    Letters Unicode cannot split (such as Ł in a foreign name) get the status
    "not decomposable" so a person can decide what to do. Punctuation is ignored.
    """
    counts = Counter(c for text in texts for c in text if ord(c) > 127 and c.isalpha())
    rows = [
        {
            "letter": letter,
            "stripped": strip_diacritics(letter),
            "count": count,
            "status": "ok" if strip_diacritics(letter) != letter else "not decomposable",
        }
        for letter, count in counts.most_common()
    ]
    return pd.DataFrame(rows, columns=["letter", "stripped", "count", "status"])


def classify(word: str, is_word: Callable[[str], bool]) -> str:
    """Return "none" (no diacritic), "A" or "B"."""
    lowered = word.lower()
    stripped = strip_diacritics(lowered)
    if stripped == lowered:
        return "none"
    return "B" if is_word(stripped) else "A"


def find_accented_words(sentences: pd.DataFrame) -> set[str]:
    """Every distinct lowercased word with a diacritic in the Portuguese column."""
    raise NotImplementedError("Step 2.1 is not implemented yet. See the to-do list above.")


def load_is_word(config: dict) -> Callable[[str], bool]:
    """Return a function that asks the Hunspell dictionary (via spylls)."""
    raise NotImplementedError("Step 2.2 is not implemented yet. See the to-do list above.")


def build_lexicon(words: list[str], is_word: Callable[[str], bool], config: dict) -> pd.DataFrame:
    """One row per word (columns in common.TABLES["lexicon_auto"])."""
    raise NotImplementedError("Steps 2.3-2.4 are not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 2: label Class A / B")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    config = load_config()
    sentences = read_table("sentences", fixtures=args.fixtures)
    texts = [normalize(t, config["normalize_unicode"]) for t in sentences["pt"]]
    print("Wrote", write_table(letter_table(texts), "letters"))
    words = sorted(find_accented_words(sentences))
    lexicon = build_lexicon(words, load_is_word(config), config)
    print("Wrote", write_table(lexicon, "lexicon_auto"))


if __name__ == "__main__":
    main()
