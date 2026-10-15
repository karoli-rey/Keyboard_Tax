"""Step 6: compare versions and systems; make the tables and charts for the report.

Owner:  Coder 2
Input:  outputs/5_scores.csv, outputs/5_corpus_scores.csv, outputs/4_translations.csv,
        outputs/3_versions.csv, data/challenge_set.csv
Output: outputs/6_results/  (tables as CSV, charts as PNG)

To do:
    1. drop_table(): quality drop (clean minus damaged) per version and system.
    2. targeted_check(): for each challenge-set sentence, does the English match the
       correct reading or the wrong one?
    3. regression(): quality drop = b0 + b1 * B words + b2 * A words + b3 * changed letters.
       One fit per system, on all damaged versions INCLUDING noise (otherwise the letter
       effect cannot be separated from the word effects). Cluster errors by sentence,
       since every sentence appears in several versions. We expect b1 much larger than b2,
       and b3 near zero: a hypothesis to test, not a result.
    4. One chart per main result; save everything in RESULTS_DIR.
"""

import argparse

import pandas as pd

from keyboard_tax.common import RESULTS_DIR, read_table


def drop_table(scores: pd.DataFrame) -> pd.DataFrame:
    """Mean quality drop per version and system, compared with the clean version."""
    raise NotImplementedError("Step 6.1 is not implemented yet. See the to-do list above.")


def targeted_check(translations: pd.DataFrame, challenge_set: pd.DataFrame) -> pd.DataFrame:
    """One row per challenge sentence, version and system, with a correct/incorrect flag."""
    raise NotImplementedError("Step 6.2 is not implemented yet. See the to-do list above.")


def regression(scores: pd.DataFrame, versions: pd.DataFrame) -> pd.DataFrame:
    """Regression coefficients, one set per system."""
    raise NotImplementedError("Step 6.3 is not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 6: analyze")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    scores = read_table("scores", fixtures=args.fixtures)
    translations = read_table("translations", fixtures=args.fixtures)
    versions = read_table("versions", fixtures=args.fixtures)
    challenge_set = read_table("challenge_set", fixtures=args.fixtures)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    drop_table(scores).to_csv(RESULTS_DIR / "drop_table.csv", index=False)
    targeted_check(translations, challenge_set).to_csv(
        RESULTS_DIR / "targeted_check.csv", index=False
    )
    regression(scores, versions).to_csv(RESULTS_DIR / "regression.csv", index=False)
    print("Wrote results to", RESULTS_DIR)


if __name__ == "__main__":
    main()
