"""Helpers shared by all steps: settings, file names and columns, accent stripping.

Every step reads and writes its tables with read_table() and write_table(). Both check
the columns, so a mistake in one step shows up at the hand-off, not three steps later.
Change a table's columns only after the team agrees, and update its example in
tests/fixtures/ in the same pull request.
"""

import unicodedata
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
RESULTS_DIR = ROOT / "outputs" / "6_results"

# name: (file, columns in order)
TABLES: dict[str, tuple[str, list[str]]] = {
    "sentences": ("outputs/1_sentences.csv", ["sent_id", "pt", "en"]),
    "letters": ("outputs/2_letters.csv", ["letter", "stripped", "count", "status"]),
    "lexicon_auto": (
        "outputs/2_lexicon_auto.csv",
        ["word", "stripped", "label", "zipf", "needs_review"],
    ),
    "lexicon": (
        "data/lexicon.csv",
        ["word", "stripped", "label", "zipf", "native_checked", "lost", "note"],
    ),
    "versions": (
        "outputs/3_versions.csv",
        ["sent_id", "version", "src", "n_a", "n_b", "n_chars"],
    ),
    "translations": (
        "outputs/4_translations.csv",
        ["sent_id", "version", "system", "src", "hyp"],
    ),
    "scores": ("outputs/5_scores.csv", ["sent_id", "version", "system", "chrf", "comet"]),
    "corpus_scores": (
        "outputs/5_corpus_scores.csv",
        ["version", "system", "bleu", "chrf", "comet"],
    ),
    "challenge_set": (
        "data/challenge_set.csv",
        ["sent_id", "word", "correct_reading", "correct_pattern", "wrong_pattern"],
    ),
}


# ---------------------------------------------------------------- settings

def load_config(path: Path = ROOT / "config.yaml") -> dict:
    """Return the settings from config.yaml as a dictionary."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------- tables

def table_path(name: str, fixtures: bool = False) -> Path:
    """Where table `name` lives; with fixtures=True, its small example."""
    if fixtures:
        return FIXTURES / f"{name}.csv"
    return ROOT / TABLES[name][0]


def check_columns(df: pd.DataFrame, name: str) -> None:
    """Raise a clear error if `df` does not have exactly the agreed columns."""
    expected = TABLES[name][1]
    if list(df.columns) != expected:
        raise ValueError(
            f"Table '{name}' has columns {list(df.columns)}, expected {expected}. "
            "See TABLES in src/keyboard_tax/common.py."
        )


def read_table(name: str, fixtures: bool = False) -> pd.DataFrame:
    """Read a table and check its columns."""
    path = table_path(name, fixtures)
    if not path.exists():
        hint = "" if fixtures else " Run the step that creates it, or use --fixtures."
        raise FileNotFoundError(f"Missing {path}.{hint}")
    df = pd.read_csv(path)
    check_columns(df, name)
    return df


def write_table(df: pd.DataFrame, name: str) -> Path:
    """Check the columns, then write the table to its agreed place."""
    check_columns(df, name)
    path = table_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------- text

def strip_diacritics(text: str) -> str:
    """Remove all diacritics: 'pôde' -> 'pode', 'estação' -> 'estacao'.

    Unicode stores each accented letter as base letter + mark (ê = e + ^), so we split
    the letters (NFD), drop the marks and join them again (NFC). No hand-written table.
    """
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", kept)


def normalize(text: str, mapping: dict[str, str]) -> str:
    """Unify characters before stripping (e.g. Romanian cedilla ş -> comma ș)."""
    text = unicodedata.normalize("NFC", text)
    for old, new in mapping.items():
        text = text.replace(old, new)
    return text
