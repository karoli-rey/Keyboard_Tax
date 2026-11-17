# data/

Data we create and release with the project. This file is also its datasheet:
what each file contains, how it was made, and its licence.

**Licence:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), because it
contains sentences from FLORES+ (also CC BY-SA 4.0). The code has its own licence (MIT).

## `lexicon.csv`: the reviewed Class A / B word list

1. Step 2 writes the automatic labels to `outputs/2_lexicon_auto.csv`.
2. `python -m keyboard_tax.classify --init-lexicon` copies them here as `lexicon.csv`
   with the columns below: `native_checked` is `todo` for every word marked for review
   and `no` for the others; `lost` and `note` are empty. It also writes
   `outputs/2_review_sheet.csv`, each word with its `native_checked` value and an example
   sentence, the `todo` words first, to see them in context.
   An existing `lexicon.csv` is never overwritten (only with `--force`).
3. The native speaker checks every `todo` row, corrects the label if needed, writes `yes`
   in `native_checked` and adds a short note.
   For Class B words, `lost` says what the reader loses, e.g. `tense (past to present)`.
   Step 3 stops while any row is still `todo`.
4. Commit it. Step 3 reads only this file.

Columns: `word, stripped, label, zipf, native_checked, lost, note` (example: `tests/fixtures/lexicon.csv`).

## `challenge_words.csv`: Class B words whose English really changes

One row per word: the right reading, and English words for the right and the wrong reading,
separated by `|` (example: `país`, `noun: country`, `country|nation|...`, `parents|parent`).
72 words. Written by Coder 2 with Claude (see `notes/ai_use.md`); checked by the native speaker.
Left out of the draft on purpose: *é, está, à, às, têm, nós, dá, pôr*, and nouns whose verb reading has the
same English form (*dúvida*: doubt / doubts). Their difference is grammar ("is" or "and"), and
such words are in almost every English sentence, so a word match cannot decide.

## `challenge_set.csv`: sentences where a lost accent changes the English meaning

`python -m keyboard_tax.challenge` drafts it from `challenge_words.csv`:

1. A sentence is taken if its clean Portuguese contains the word and the word lost its accent
   in at least one damaged version.
2. It is kept only if the English reference contains a right-reading word and no wrong-reading
   word, so the check can tell the two readings apart.
3. The native speaker runs the script again (it then only writes the review sheet), reads
   `outputs/6_challenge_review.csv` (each row with both sentences),
   deletes rows that do not work and fixes patterns in this file. The script never overwrites
   it without `--force`.

Draft of 16 Nov: 159 rows. Review file of 16 Nov (from Thomas): 136 kept, 13 fixed, 10 deleted,
38 added by hand, among them a few *é, está, têm, à, às* sentences with patterns written for that
sentence. Now 187 rows, 170 sentences, 74 words; every row passes rule 2, and no word occurs twice
in its sentence. Step 6 checks each system's translation
against it: "right" if the English has a right-reading word and no wrong one, "wrong" for the
opposite, "unclear" otherwise.

| Column | Example |
|---|---|
| `sent_id` | `0` (row in `outputs/1_sentences.csv`) |
| `word` | `pôde` |
| `correct_reading` | `past: could` |
| `correct_pattern` | `could\|was able` (English words for the right meaning, separated by `\|`) |
| `wrong_pattern` | `can\|can't` |
