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
Optional, switched off in config.yaml (not used in our results):
    stripped_25, stripped_50, stripped_75   a share of the accented words, nested
                                            (every word in _25 is also in _50 and _100)

n_a, n_b: how many Class A / Class B words were stripped in this version.
n_chars:  how many letters differ from the clean sentence.

How it works:
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
       the first 25%, 50% or 75% of that order. Switched off in config.yaml (not used).
    6. Write the table with write_table(df, "versions").

Thomas's demo in notes/demos/perturb_demo.py shows a first version of steps 4 and 5.
"""

import argparse
import re
from collections import Counter
from collections.abc import Callable, Sequence
from random import Random

import pandas as pd

from keyboard_tax.classify import load_is_word
from keyboard_tax.common import load_config, read_table, strip_diacritics, write_table

# Neighbouring keys on a QWERTY keyboard, for the noise version. Lowercase letters only.
KEYBOARD_NEIGHBOURS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij",
    "i": "uok", "o": "ipl", "p": "ol", "a": "qsz", "s": "awdz", "d": "sefx", "f": "drgc",
    "g": "fthv", "h": "gyjb", "j": "hukn", "k": "jilm", "l": "kop", "z": "asx",
    "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
DEFAULT_VERSIONS = (
    "clean", "stripped_100", "a_only", "b_only", "noise",
    "stripped_25", "stripped_50", "stripped_75",
)


def _changed_letters(text: str) -> int:
    return sum(char.isalpha() and strip_diacritics(char) != char for char in text)


def _replace_spans(text: str, spans: set[tuple[int, int]]) -> str:
    pieces = []
    cursor = 0
    for start, end in sorted(spans):
        pieces.extend((text[cursor:start], strip_diacritics(text[start:end])))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def _noise(text: str, target: int, rng: Random, is_word: Callable[[str], bool] | None) -> str:
    chars = list(text)
    tokens = [
        match for match in WORD_RE.finditer(text)
        if strip_diacritics(match.group()) == match.group()
    ]
    tried: dict[tuple[int, int], set[int]] = {}
    token_order = list(range(len(tokens)))
    rng.shuffle(token_order)
    changed = 0
    while changed < target:
        made_change = False
        for token_index in token_order:
            if changed >= target:
                break
            match = tokens[token_index]
            word_key = (match.start(), match.end())
            attempted = tried.setdefault(word_key, set())
            positions = [
                position for position in range(match.start(), match.end())
                if position not in attempted and chars[position].lower() in KEYBOARD_NEIGHBOURS
            ]
            rng.shuffle(positions)
            for position in positions:
                attempted.add(position)
                alternatives = list(KEYBOARD_NEIGHBOURS[chars[position].lower()])
                rng.shuffle(alternatives)
                for replacement in alternatives:
                    proposed_char = replacement.upper() if chars[position].isupper() else replacement
                    old_char = chars[position]
                    chars[position] = proposed_char
                    candidate = "".join(chars[match.start():match.end()]).lower()
                    if is_word is None or not is_word(candidate):
                        made_change = True
                        changed += 1
                        break
                    chars[position] = old_char
                if made_change:
                    break
        if not made_change:
            break
    return "".join(chars)


def build_versions(
    sentences: pd.DataFrame,
    lexicon: pd.DataFrame,
    seed: int,
    is_word: Callable[[str], bool] | None = None,
    versions: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return one row per sentence and version (columns in common.TABLES["versions"])."""
    requested = tuple(DEFAULT_VERSIONS if versions is None else versions)
    labels = {
        str(row.word).lower(): row.label
        for row in lexicon.itertuples(index=False)
        if row.label in {"A", "B"}
    }
    rows = []

    for sentence in sentences.itertuples(index=False):
        text = str(sentence.pt)
        rng = Random(f"{seed}-{sentence.sent_id}")
        tokens = list(WORD_RE.finditer(text))
        candidates = []
        for match in tokens:
            word = match.group()
            label = labels.get(word.lower())
            changed = _changed_letters(word)
            if label and changed:
                candidates.append({
                    "span": (match.start(), match.end()),
                    "label": label,
                    "changed": changed,
                })

        by_label = {
            label: [item for item in candidates if item["label"] == label]
            for label in ("A", "B")
        }
        k = min(len(by_label["A"]), len(by_label["B"]))
        chosen = {}
        if k:
            for label in ("A", "B"):
                options = list(by_label[label])
                rng.shuffle(options)
                options.sort(key=lambda item: item["changed"])
                chosen[label] = options[:k]

        changed_all = strip_diacritics(text)
        total_counts = Counter(item["label"] for item in candidates)
        all_chars = _changed_letters(text)
        available: dict[str, tuple[str, int, int, int]] = {
            "clean": (text, 0, 0, 0),
            "stripped_100": (changed_all, total_counts["A"], total_counts["B"], all_chars),
        }

        if k:
            for label, name in (("A", "a_only"), ("B", "b_only")):
                selected = chosen[label]
                spans = {item["span"] for item in selected}
                class_counts = (k, 0) if label == "A" else (0, k)
                available[name] = (
                    _replace_spans(text, spans), class_counts[0], class_counts[1],
                    sum(item["changed"] for item in selected),
                )

            _, _, _, b_chars = available["b_only"]
            noise_text = _noise(text, b_chars, rng, is_word)
            available["noise"] = (
                noise_text, 0, 0,
                sum(left != right and left.isalpha() for left, right in zip(text, noise_text)),
            )

            accented_spans = [item["span"] for item in candidates]
            rng.shuffle(accented_spans)
            for rate in (25, 50, 75):
                count = len(accented_spans) * rate // 100
                selected_spans = set(accented_spans[:count])
                selected_items = [item for item in candidates if item["span"] in selected_spans]
                selected_counts = Counter(item["label"] for item in selected_items)
                name = f"stripped_{rate}"
                available[name] = (
                    _replace_spans(text, selected_spans), selected_counts["A"],
                    selected_counts["B"], sum(item["changed"] for item in selected_items),
                )

        for name in requested:
            if name in available:
                src, n_a, n_b, n_chars = available[name]
                rows.append({
                    "sent_id": sentence.sent_id,
                    "version": name,
                    "src": src,
                    "n_a": n_a,
                    "n_b": n_b,
                    "n_chars": n_chars,
                })

    return pd.DataFrame(rows, columns=["sent_id", "version", "src", "n_a", "n_b", "n_chars"])


def summarize(versions: pd.DataFrame) -> str:
    """How many sentences got each version, and where the noise fell short of b_only.

    The noise version can change fewer letters than b_only when a sentence has too few
    letters outside accented words; n_chars still records the real number.
    """
    lines = [f"{versions['sent_id'].nunique()} sentences"]
    counts = versions.groupby("version", sort=False)["sent_id"].nunique()
    lines += [f"  {name:<13} {count}" for name, count in counts.items()]
    by_version = versions.pivot(index="sent_id", columns="version", values="n_chars")
    if {"noise", "b_only"} <= set(by_version.columns):
        paired = by_version[["noise", "b_only"]].dropna()
        short = int((paired["noise"] < paired["b_only"]).sum())
        lines.append(f"noise changed fewer letters than b_only in {short} sentence(s)")
    return "\n".join(lines)


def check_reviewed(lexicon: pd.DataFrame) -> None:
    """Stop if the native speaker has not finished data/lexicon.csv (native_checked "todo")."""
    todo = lexicon.loc[
        lexicon["native_checked"].astype(str).str.strip().str.lower() == "todo", "word"
    ]
    if len(todo):
        examples = ", ".join(map(str, todo.head(5)))
        raise SystemExit(
            f"data/lexicon.csv still has {len(todo)} word(s) with native_checked 'todo' "
            f"(e.g. {examples}). Finish the review first, see data/README.md."
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 3: damaged versions")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    config = load_config()
    sentences = read_table("sentences", fixtures=args.fixtures)
    lexicon = read_table("lexicon", fixtures=args.fixtures)
    if not args.fixtures:
        check_reviewed(lexicon)
    dictionary = None if args.fixtures else load_is_word(config)
    versions = build_versions(
        sentences, lexicon, seed=config["seed"], is_word=dictionary,
        versions=config["versions"],
    )
    print("Wrote", write_table(versions, "versions"))
    print(summarize(versions))


if __name__ == "__main__":
    main()
