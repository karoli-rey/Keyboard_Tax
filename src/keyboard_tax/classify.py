"""Step 2: label every accented word as Class A or Class B, automatically.

Class A: without its diacritics, the word is NOT a real word   (não  -> nao)
Class B: without its diacritics, the word IS a real word       (pôde -> pode)

Owner:  Coder 1. Every change here gets a second reader before merging.
Input:  outputs/1_sentences.csv
Output: outputs/2_letters.csv       every accented letter and what it becomes
        outputs/2_lexicon_auto.csv  every accented word with its automatic label

Then the native speaker checks the letters list once, reviews the words marked
needs_review, and saves the corrected word list as data/lexicon.csv (see data/README.md).
`--init-lexicon` starts that file from the automatic labels, together with
outputs/2_review_sheet.csv (each word with an example sentence). It never overwrites an
existing data/lexicon.csv without --force. Step 3 reads only the reviewed file, so
rerunning this step never overwrites the review.

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
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from random import Random

import pandas as pd

from keyboard_tax.common import (
    ROOT,
    load_config,
    normalize,
    read_table,
    strip_diacritics,
    table_path,
    write_table,
)

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


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
    lower_seen = set()
    capitalized_noninitial = set()
    accented = set()
    for text in sentences["pt"]:
        text = unicodedata.normalize("NFC", str(text))
        sentence_start = 0
        for match in WORD_RE.finditer(text):
            token = match.group()
            lowered = token.lower()
            if strip_diacritics(lowered) != lowered:
                accented.add(lowered)
                prefix = text[sentence_start:match.start()]
                sentence_initial = not any(char.isalpha() for char in prefix)
                if token == lowered:
                    lower_seen.add(lowered)
                elif token[0].isupper() and not sentence_initial:
                    capitalized_noninitial.add(lowered)
            boundary = max(
                text.rfind(".", sentence_start, match.start()),
                text.rfind("!", sentence_start, match.start()),
                text.rfind("?", sentence_start, match.start()),
            )
            if boundary >= sentence_start:
                sentence_start = boundary + 1
    return {word for word in accented if word in lower_seen or word not in capitalized_noninitial}


@lru_cache(maxsize=4)
def _dictionary_lookup(path: str) -> Callable[[str], bool]:
    from spylls.hunspell import Dictionary

    return Dictionary.from_files(path).lookup


def load_is_word(config: dict) -> Callable[[str], bool]:
    """Return a function that asks the Hunspell dictionary (via spylls).

    `dictionary` in config.yaml is the path without extension (data/raw/pt_BR for
    pt_BR.dic and pt_BR.aff). A relative path is read from the project folder, so the
    step works from any working directory.
    """
    dictionary_path = config.get("dictionary")
    if not dictionary_path or str(dictionary_path).strip().upper() == "TODO":
        raise ValueError("Set the pt_BR Hunspell dictionary path in config.yaml before step 2.")
    path = Path(str(dictionary_path)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    missing = [
        str(path.with_name(path.name + suffix))
        for suffix in (".dic", ".aff")
        if not path.with_name(path.name + suffix).exists()
    ]
    if missing:
        raise ValueError(
            f"Missing Hunspell files {missing}. Run scripts/get_dictionary.sh, or set "
            "`dictionary` in config.yaml to the path without .dic/.aff."
        )
    try:
        return _dictionary_lookup(str(path))
    except (OSError, ValueError) as error:
        raise ValueError(f"Could not load the Hunspell dictionary at {str(path)!r}.") from error


def build_lexicon(words: list[str], is_word: Callable[[str], bool], config: dict) -> pd.DataFrame:
    """One row per word (columns in common.TABLES["lexicon_auto"])."""
    min_zipf = config.get("min_zipf")
    if min_zipf is None or str(min_zipf).strip().upper() == "TODO":
        raise ValueError("Set min_zipf in config.yaml before building the automatic lexicon.")
    try:
        min_zipf = float(min_zipf)
    except (TypeError, ValueError) as error:
        raise ValueError("config.yaml min_zipf must be a number.") from error

    from wordfreq import zipf_frequency

    rows = []
    for word in sorted(set(words)):
        stripped = strip_diacritics(word.lower())
        label = classify(word, is_word)
        zipf = zipf_frequency(stripped, "pt") if label == "B" else None
        rows.append(
            {
                "word": word,
                "stripped": stripped,
                "label": label,
                "zipf": zipf,
                "needs_review": label == "B" and zipf < min_zipf,
            }
        )

    review_sample = int(config.get("review_sample", 0))
    if review_sample > 0:
        candidates = [index for index, row in enumerate(rows) if not row["needs_review"]]
        sample = Random(config.get("seed", 0)).sample(
            candidates, min(review_sample, len(candidates))
        )
        for index in sample:
            rows[index]["needs_review"] = True
    return pd.DataFrame(rows, columns=["word", "stripped", "label", "zipf", "needs_review"])


REVIEW_SHEET = ROOT / "outputs" / "2_review_sheet.csv"


def _native_checked_start(lexicon_auto: pd.DataFrame) -> list[str]:
    """Return "todo" for the words marked needs_review, "no" for the others."""
    return [
        "todo" if str(flag).strip().lower() == "true" else "no"
        for flag in lexicon_auto["needs_review"]
    ]


def init_lexicon(lexicon_auto: pd.DataFrame) -> pd.DataFrame:
    """Start data/lexicon.csv from the automatic labels (columns in TABLES["lexicon"]).

    native_checked is "todo" for the words the native speaker must check, "no" otherwise.
    """
    lexicon = lexicon_auto[["word", "stripped", "label", "zipf"]].copy()
    lexicon["native_checked"] = _native_checked_start(lexicon_auto)
    lexicon["lost"] = ""
    lexicon["note"] = ""
    return lexicon


def review_sheet(lexicon_auto: pd.DataFrame, sentences: pd.DataFrame) -> pd.DataFrame:
    """Each word with the first sentence it occurs in, to see it in context while checking.

    The "todo" words (the ones the native speaker must check) come first.
    """
    examples: dict[str, str] = {}
    for text in sentences["pt"]:
        text = unicodedata.normalize("NFC", str(text))
        for match in WORD_RE.finditer(text):
            examples.setdefault(match.group().lower(), text)
    sheet = lexicon_auto[["word", "stripped", "label", "zipf"]].copy()
    sheet["native_checked"] = _native_checked_start(lexicon_auto)
    sheet["example"] = [examples.get(str(word).lower(), "") for word in sheet["word"]]
    todo_last = sheet["native_checked"] != "todo"
    return sheet.iloc[todo_last.argsort(kind="stable")].reset_index(drop=True)


def write_lexicon_start(force: bool = False) -> None:
    """Write data/lexicon.csv and outputs/2_review_sheet.csv from the step 2 output."""
    lexicon_path = table_path("lexicon")
    if lexicon_path.exists() and not force:
        raise SystemExit(
            f"{lexicon_path} already exists and may hold the native speaker's review. "
            "Not overwriting it; use --force to start again from the automatic labels."
        )
    lexicon_auto = read_table("lexicon_auto")
    print("Wrote", write_table(init_lexicon(lexicon_auto), "lexicon"))
    sheet = review_sheet(lexicon_auto, read_table("sentences"))
    REVIEW_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(REVIEW_SHEET, index=False)
    print("Wrote", REVIEW_SHEET)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 2: label Class A / B")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    parser.add_argument(
        "--init-lexicon", action="store_true",
        help="start data/lexicon.csv and outputs/2_review_sheet.csv from the step 2 output",
    )
    parser.add_argument(
        "--force", action="store_true", help="with --init-lexicon: overwrite data/lexicon.csv"
    )
    args = parser.parse_args(argv)
    if args.init_lexicon:
        if args.fixtures:
            parser.error("--init-lexicon works on the real step 2 output, not on --fixtures")
        write_lexicon_start(force=args.force)
        return
    config = load_config()
    sentences = read_table("sentences", fixtures=args.fixtures)
    texts = [normalize(t, config["normalize_unicode"]) for t in sentences["pt"]]
    print("Wrote", write_table(letter_table(texts), "letters"))
    words = sorted(find_accented_words(sentences))
    lexicon = build_lexicon(words, load_is_word(config), config)
    print("Wrote", write_table(lexicon, "lexicon_auto"))


if __name__ == "__main__":
    main()
