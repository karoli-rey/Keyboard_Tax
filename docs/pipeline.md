# How the pipeline works

This page explains the code: what each step does, the rules behind it, and what is not in
the repository. The motivation and the results are in the paper and in `results.ipynb`.
All settings are in `config.yaml`; how to run each step is in the main `README.md`.

## The steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1 | `data.py` | Loads the 1,012 FLORES+ `devtest` sentences in Brazilian Portuguese with their English translations | `outputs/1_sentences.csv` |
| 2 | `classify.py` | Finds every accented word, removes the accents and asks the pt_BR dictionary whether the result is still a word: no → Class A, yes → Class B | `outputs/2_lexicon_auto.csv` |
| check | by hand | A native speaker checked all 224 automatic Class B words and 50 random Class A words | `data/lexicon.csv`: 1,144 words (1,046 A, 98 B) |
| 3 | `versions.py` | Builds five versions of each sentence (next table) | `outputs/3_versions.csv`: 3,290 rows |
| 4 | `translate.py` | Translates every version with three systems | `outputs/4_translations.csv`: 9,870 rows |
| 5 | `score.py` | Scores each translation against the English reference: BLEU, chrF, COMET | `outputs/5_scores.csv`, `outputs/5_corpus_scores.csv` |
| 6 | `analyze.py` | Compares versions and systems, runs the challenge-set check, tests the hypotheses | `outputs/6_results/`, `results/` |

## The five versions

| Version | What is changed | Sentences |
|---|---|---|
| `clean` | nothing | 1,012 |
| `stripped_100` | every accent removed | 1,012 |
| `a_only` | k Class A words lose their accent | 422 |
| `b_only` | k Class B words lose their accent | 422 |
| `noise` | keyboard typos in words without accents, as many letters as in `b_only` | 422 |

k = min(number of Class A words, number of Class B words) in the sentence, so `a_only` and
`b_only` damage the same number of words. Only the 422 sentences with words of both classes
get the last three versions, and these three are always compared with `clean` on those 422.

## Rules worth knowing

**Step 2: labels**
- Accents are removed with Unicode NFD, which splits a letter from its accent (ê → e + ^).
  The accent is dropped and the text recomposed (`strip_diacritics` in `common.py`).
- The dictionary (pt_BR, VERO 3.2) is asked through `spylls`, never read as a word list: the
  `.dic` file holds stems only, so *tem* would be missing and *têm* would wrongly become Class A.
- No frequency cut (`min_zipf: 99`): word frequency lists also count text typed without
  accents (*musica* is frequent), so every automatic Class B word was checked by hand.
- A word stays Class B only if its accent-free form is used in normal written Brazilian
  Portuguese. Rare verb forms, *tu* forms, abbreviations and foreign words count as Class A.
  Names are skipped.

**Step 3: versions**
- The words to strip are picked at random with a fixed seed (`seed: 0`), preferring words with
  one accent, so `a_only` and `b_only` usually change the same number of letters too.
- A typo that happens to create a real word is redone, so `noise` adds no new ambiguity.

**Step 4: translation**
- NLLB-200 (distilled, 600M) and Opus-MT (ROMANCE→en, as there is no official pt→en model)
  use beam search with beam size 4. Qwen2.5-7B-Instruct was chosen as the LLM because its
  weights are open and it supports Portuguese; it runs in 4-bit on a free Colab GPU, with
  one fixed prompt and no sampling.
- LLM answers are cleaned by fixed rules (`clean_llm_output`) that remove extras such as
  "Here is the translation:". For 4 sentences the LLM answered partly in Chinese; these
  answers were kept, and step 6 repeats the analysis without them.
- Each distinct text is translated once per system and saved batch by batch in
  `outputs/4_cache/`, so a crashed GPU session loses nothing.

**Step 5: scores**
- COMET always gets the **clean** Portuguese sentence as its source: a damaged source would
  hide the damage we want to measure.
- sacreBLEU 2.6.0 signatures:
  BLEU `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0`,
  chrF `nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0`.
  COMET model: `Unbabel/wmt22-comet-da`.

**Step 6: analysis**
- Drop = clean score minus damaged score, per sentence. Means come with a 95% confidence
  interval (normal approximation).
- Main test: paired contrasts on the same sentences (`b_only` minus `a_only`, `b_only` minus
  `noise`). The planned regression cannot separate Class A words from changed letters
  (correlation 0.88), so it is reported with that caveat.
- Challenge set: 187 items where a lost accent changes the English meaning
  (`data/challenge_set.csv`, see `data/README.md`). Each translation is marked right, wrong
  or unclear by matching English words; accuracy comes with a Wilson 95% interval.
- Robustness: drops and contrasts again without the sentences where *é* is the stripped
  Class B word, and without the 4 sentences with Chinese answers.

## What is not in the repository

- **FLORES+ sentences.** The dataset is gated on Hugging Face
  (`openlanguagedata/flores_plus`: log in and accept the terms). Everything the code writes
  from it goes to `outputs/`, which is never committed. `data/` and `results/` hold words,
  scores and sentence numbers only.
- **The dictionary.** `scripts/get_dictionary.sh` downloads it at a fixed commit.
