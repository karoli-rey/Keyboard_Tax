"""Draft the challenge set: sentences where a lost accent changes the English meaning.

Owner:  Researcher + native speaker. First draft made by Coder 2 (see notes/ai_use.md).
Input:  data/challenge_words.csv  one row per Class B word whose English really changes:
                                  the right reading, and English words for each reading
        outputs/1_sentences.csv, outputs/3_versions.csv
Output: data/challenge_set.csv    one row per sentence and word; step 6 reads it
        outputs/6_challenge_review.csv  the same rows with the Portuguese and English
                                  sentence next to them, for the native speaker

How it works:
    1. A sentence is a candidate if its clean Portuguese contains the word and at least one
       damaged version (stripped_100 or b_only) lost the accent on it.
    2. It is kept only if the English reference contains a word of the right reading and no
       word of the wrong one. Otherwise the check could not tell the two readings apart.
    3. The native speaker runs this script (it then only writes the review sheet), reads
       outputs/6_challenge_review.csv and edits data/challenge_set.csv: delete rows that do
       not work, fix patterns. The file is never overwritten without --force.

Left out of the draft on purpose: é, está, à, às, têm, nós, dá, pôr and words whose two readings have
the same English form (dúvida "doubt / doubts"). Their difference is grammar ("is" versus
"and"), and such words appear in almost every English sentence, so a word match cannot
decide. The COMET drop covers them.

Try it:    python -m keyboard_tax.challenge --fixtures
Full run:  python -m keyboard_tax.challenge
"""

import argparse
import re

import pandas as pd

from keyboard_tax.analyze import pattern
from keyboard_tax.common import ROOT, TABLES, read_table, table_path, write_table

VERSIONS_WITH_B = ["stripped_100", "b_only"]
REVIEW_FILE = ROOT / "outputs" / "6_challenge_review.csv"


def draft_challenge_set(
    words: pd.DataFrame, sentences: pd.DataFrame, versions: pd.DataFrame
) -> pd.DataFrame:
    """One row per sentence and word where the check can tell the two readings apart."""
    damaged = (
        versions[versions["version"].isin(VERSIONS_WITH_B)].groupby("sent_id")["src"].apply(list)
    )
    rows = []
    for item in words.itertuples(index=False):
        in_text = re.compile(r"\b" + re.escape(item.word) + r"\b", re.IGNORECASE)
        right, wrong = pattern(item.correct_pattern), pattern(item.wrong_pattern)
        for sent_id, pt, en in sentences[["sent_id", "pt", "en"]].itertuples(index=False):
            if not in_text.search(pt):
                continue
            lost = any(not in_text.search(src) for src in damaged.get(sent_id, []))
            testable = bool(right.search(en)) and not wrong.search(en)
            if lost and testable:
                rows.append(
                    {
                        "sent_id": sent_id,
                        "word": item.word,
                        "correct_reading": item.correct_reading,
                        "correct_pattern": item.correct_pattern,
                        "wrong_pattern": item.wrong_pattern,
                    }
                )
    table = pd.DataFrame(rows, columns=TABLES["challenge_set"][1])
    return table.sort_values(["sent_id", "word"]).reset_index(drop=True)


def review_sheet(challenge_set: pd.DataFrame, sentences: pd.DataFrame) -> pd.DataFrame:
    """The challenge set with the Portuguese and English sentence, for the review."""
    return challenge_set.merge(sentences, on="sent_id", how="left")[
        ["sent_id", "word", "pt", "en", "correct_reading", "correct_pattern", "wrong_pattern"]
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Draft the challenge set")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures; write nothing")
    parser.add_argument("--force", action="store_true", help="overwrite data/challenge_set.csv")
    args = parser.parse_args(argv)
    words = read_table("challenge_words", fixtures=args.fixtures)
    sentences = read_table("sentences", fixtures=args.fixtures)
    versions = read_table("versions", fixtures=args.fixtures)
    draft = draft_challenge_set(words, sentences, versions)
    print(
        f"{len(draft)} rows, {draft['sent_id'].nunique()} sentences, "
        f"{draft['word'].nunique()} of {len(words)} words"
    )
    if args.fixtures:
        print(draft.to_string(index=False))
        return
    if table_path("challenge_set").exists() and not args.force:
        print(
            "data/challenge_set.csv exists (maybe already reviewed). Not overwriting it; "
            "use --force to start again from the draft."
        )
        challenge_set = read_table("challenge_set")
    else:
        challenge_set = draft
        print("Wrote", write_table(challenge_set, "challenge_set"))
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    review_sheet(challenge_set, sentences).to_csv(REVIEW_FILE, index=False)
    print("Wrote the review sheet for the current file:", REVIEW_FILE)


if __name__ == "__main__":
    main()
