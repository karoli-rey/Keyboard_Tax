"""Step 3: build the damaged versions of every sentence.

Owner:  Coder 1
Input:  outputs/1_sentences.csv, data/lexicon.csv (reviewed)
Output: outputs/3_versions.csv  (columns: sent_id, version, src, n_a, n_b, n_chars)

Versions, one row each per sentence:
    clean         the original sentence
    stripped_100  every diacritic removed
    a_only        only Class A words stripped
    b_only        only Class B words stripped, same number of words as a_only
    noise         keyboard typos, same number of changed letters as b_only
Should tier:
    stripped_25, stripped_50, stripped_75   a share of the accented words, nested
                                            (every word in _25 is also in _50 and _100)

n_a, n_b: how many Class A / Class B words were stripped in this version.
n_chars:  how many letters differ from the clean sentence.

To do:
    1. For each sentence, find its Class A and Class B words using the lexicon.
    2. k = min(number of A words, number of B words).
       If k == 0, write only clean and stripped_100 for this sentence.
    3. Pick k words of each class at random (seed from the config). Prefer words with a
       single diacritic, so a_only and b_only usually change the same number of letters
       too. The regression still uses n_a, n_b and n_chars, so small gaps are fine.
    4. Noise: replace n_chars letters in words without diacritics by a neighbouring key
       on the keyboard. Redo any typo that creates a real word, so the noise version
       contains no new ambiguity.
    5. Strip rates: shuffle the sentence's accented words once with the seed, then strip
       the first 25%, 50% or 75% of that order.
    6. Write the table with write_table(df, "versions").

Thomas's demo in notes/demos/perturb_demo.py shows a first version of steps 4 and 5.
"""

import argparse

import pandas as pd

from keyboard_tax.common import load_config, read_table, write_table

# Neighbouring keys on a QWERTY keyboard, for the noise version. Lowercase letters only.
KEYBOARD_NEIGHBOURS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij",
    "i": "uok", "o": "ipl", "p": "ol", "a": "qsz", "s": "awdz", "d": "sefx", "f": "drgc",
    "g": "fthv", "h": "gyjb", "j": "hukn", "k": "jilm", "l": "kop", "z": "asx",
    "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}


def build_versions(sentences: pd.DataFrame, lexicon: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Return one row per sentence and version (columns in common.TABLES["versions"])."""
    raise NotImplementedError("Step 3 is not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 3: damaged versions")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    config = load_config()
    sentences = read_table("sentences", fixtures=args.fixtures)
    lexicon = read_table("lexicon", fixtures=args.fixtures)
    versions = build_versions(sentences, lexicon, seed=config["seed"])
    print("Wrote", write_table(versions, "versions"))


if __name__ == "__main__":
    main()
