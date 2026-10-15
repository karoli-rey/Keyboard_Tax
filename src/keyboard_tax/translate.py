"""Step 4: translate every version with the three systems.

Owner:  Coder 2
Input:  outputs/3_versions.csv
Output: outputs/4_translations.csv  (columns: sent_id, version, system, src, hyp)

To do:
    1. One Translator per system in the config: nllb, opus_mt, llm.
    2. The LLM gets the fixed prompt from the config, with randomness switched off.
    3. Strip any extra text the LLM adds, such as "Here is the translation:".
    4. Save after each system, so a crash does not lose finished work.
    5. Write the table with write_table(df, "translations").

Tip: develop with --fixtures and only a few sentences; run the full data on a GPU.
"""

import argparse
from typing import Protocol

import pandas as pd

from keyboard_tax.common import load_config, read_table, write_table


class Translator(Protocol):
    """Every translation system has a name and a translate() method."""

    name: str

    def translate(self, texts: list[str]) -> list[str]:
        """Translate Portuguese sentences into English, in the same order."""
        ...


def get_translator(system: str, config: dict) -> Translator:
    """Return the translator for "nllb", "opus_mt" or "llm"."""
    raise NotImplementedError("Step 4 is not implemented yet. See the to-do list above.")


def translate_all(versions: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Translate every row with every system (columns in common.TABLES["translations"])."""
    raise NotImplementedError("Step 4 is not implemented yet. See the to-do list above.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 4: translate")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    args = parser.parse_args(argv)
    config = load_config()
    versions = read_table("versions", fixtures=args.fixtures)
    translations = translate_all(versions, config)
    print("Wrote", write_table(translations, "translations"))


if __name__ == "__main__":
    main()
