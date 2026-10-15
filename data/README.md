# data/

Data we create and release with the project. This file is also its datasheet:
what each file contains, how it was made, and its licence.

**Licence:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), because it
contains sentences from FLORES+ (also CC BY-SA 4.0). The code has its own licence (MIT).

## `lexicon.csv`: the reviewed Class A / B word list

1. Step 2 writes the automatic labels to `outputs/2_lexicon_auto.csv`.
2. Copy it here as `lexicon.csv`, drop the `needs_review` column, add `native_checked`, `lost` and `note`.
3. The native speaker checks every row that was marked for review, corrects the label if
   needed, writes `yes` in `native_checked` and adds a short note.
   For Class B words, `lost` says what the reader loses, e.g. `tense (past to present)`.
4. Commit it. Step 3 reads only this file.

Columns: `word, stripped, label, zipf, native_checked, lost, note` (example: `tests/fixtures/lexicon.csv`).

## `challenge_set.csv`: sentences where a lost accent changes the English meaning

Made by the Researcher with the native speaker. Only include words where the English
really changes. Step 6 checks each system's translation against it.

| Column | Example |
|---|---|
| `sent_id` | `0` (row in `outputs/1_sentences.csv`) |
| `word` | `pôde` |
| `correct_reading` | `past: could` |
| `correct_pattern` | `could\|was able` (English words for the right meaning, separated by `\|`) |
| `wrong_pattern` | `can\|can't` |
