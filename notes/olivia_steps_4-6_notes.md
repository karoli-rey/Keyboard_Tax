# Steps 4 to 6: Olivia's technical notes

Olivia (Coder 2) built steps 4 to 6: translate, score, analyze, and the draft of the challenge
set. These notes say what each step does and why, so the report's sections 4 and 5 can be
written from them. Steps 1 to 3 are in `thomas_steps_1-3_notes.md`; the results with their
explanation are in `results.ipynb`.

## Starting point

Step 3 hands over `outputs/3_versions.csv`: 3,290 versions of 1,012 sentences.

| Version | Sentences | What is changed |
|---|---|---|
| `clean` | 1,012 | nothing |
| `stripped_100` | 1,012 | every accent removed |
| `a_only`, `b_only`, `noise` | 422 each | the same number of Class A words, Class B words, or typo letters |

3,290 versions × 3 systems = 9,870 translations.

## Step 4: translate (`translate.py`)

| Choice | What | Why |
|---|---|---|
| NLLB | `facebook/nllb-200-distilled-600M` | The smallest NLLB model, so all versions fit in free GPU time |
| Opus-MT | `Helsinki-NLP/opus-mt-ROMANCE-en` | There is no official Portuguese–English Opus-MT model |
| LLM | `Qwen/Qwen2.5-7B-Instruct`, 4-bit | Open weights (Apache 2.0), lists Portuguese, fits a free Colab GPU. Not a Claude model, because Claude suggested the first labels of the word list |
| Decoding, NLLB and Opus-MT | beam search, beam size 4, at most 256 new tokens | A common default; equal settings keep the two comparable |
| LLM prompt | one fixed prompt in `config.yaml`, one sentence per request, no sampling | Repeatable answers; the prompt was not tuned on `devtest` |
| LLM answer | cleaned by fixed rules (`clean_llm_output`): a label in front, notes after a blank line, quotation marks around the whole answer | "Here is the translation:" would lower the scores for a reason that has nothing to do with accents. The raw answer stays in the cache |
| Cache | each distinct text is translated once per system; every batch is saved in `outputs/4_cache/`, in a file named after the settings | Many versions share a text; a crashed GPU session loses nothing; changed settings never reuse old translations |
| Where | free Google Colab GPU, `scripts/colab_gpu_run.ipynb`; results come back as a zip | Too slow on a laptop; anyone can repeat the run. No Google Drive access is needed |

**Result:** 9,870 translations, none empty. For 4 sentences the LLM answered partly or fully in
Chinese (7 of its 3,254 distinct texts, clean and stripped alike). We kept these answers: it is
how the model behaves, not an effect of our damage. Step 6 repeats the analysis without them.

## Step 5: score (`score.py`)

- **chrF and BLEU** with sacreBLEU 2.6.0. Signatures, to be quoted in the report:
  BLEU `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0`,
  chrF `nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0`.
- **COMET** `Unbabel/wmt22-comet-da`. It always gets the **clean** Portuguese sentence as its
  source: a damaged source would hide the damage we want to measure.
- chrF and COMET per translation (`5_scores.csv`); BLEU, chrF and mean COMET per version and
  system (`5_corpus_scores.csv`).
- `5_corpus_scores.csv` has a `subset` column: `all` (every sentence with that version) and
  `both_classes` (the 422 sentences with all five versions). Compare `a_only`, `b_only` and
  `noise` with `clean` on `both_classes` only, otherwise two different sets of sentences are mixed.
- Each distinct (clean source, translation, reference) case is scored once.
- On Colab, COMET runs in its own Python environment (section 11 of the notebook), because it
  needs older helper packages than Colab preinstalls.

## Step 6: analyze (`analyze.py`)

| Part | What it does |
|---|---|
| Drop | For every sentence: score of the clean translation minus score of the damaged one. Mean with a 95% confidence interval (normal approximation) |
| Contrasts | Paired differences between versions of the same sentence: `b_only` minus `a_only`, `b_only` minus `noise`. On the 422 sentences. This is the main test of H2 and H3 |
| Regression | drop = b0 + b1·(B words) + b2·(A words) + b3·(letters changed), one fit per system, errors clustered by sentence, plain least squares in numpy |
| Targeted check | Word-level check on the challenge set: right / wrong / unclear per item, only where the word really lost its accent |
| BLEU against the check | On the challenge sentences: the share by which BLEU falls against the share by which right readings fall (H5) |
| Robustness | Everything again without the 182 sentences where *é* is the stripped Class B word, and without the 4 sentences with Chinese LLM answers |
| Hypotheses | H1 to H6 and H2b, each marked supported or not |

**Why the regression is not our main test.** A stripped Class A word almost always changes one
letter, so "A words" and "letters changed" move together (correlation 0.88). The fit cannot
tell them apart: b2 comes out negative and b3 positive, which only shifts the same cost between
two near-identical predictors. The regression stays in the results because the proposal
promised it, with this caveat next to it. The paired contrasts answer the same question
without the problem, and they are the standard way to compare systems on the same sentences.

## The challenge set (`challenge.py`, `data/challenge_set.csv`)

1. 73 hand-written word pairs with English words for the right and the wrong reading
   (`data/challenge_words.csv`).
2. The script takes every sentence where the word lost its accent **and** the English reference
   contains a right-reading word and no wrong-reading word. Draft: 159 rows.
3. Review (file from Thomas, 16 Nov): 136 kept, 13 fixed, 10 deleted, 38 added. Rows were
   deleted where the word occurs twice, where another word gives the same English, or where
   both readings have the same English (*experiência*). Now 187 rows, 170 sentences, 74 words.
4. Very common words (*é, está, têm, à, às*) are in only where the English reference allows a
   word match; elsewhere their difference is grammar ("is" or "and") and a word match cannot
   decide. The COMET drop covers them.

Thomas checked every row of the review by hand as native speaker.

## Results in short

| # | Hypothesis | Result |
|---|---|---|
| H1 | Removing all accents lowers quality | Supported for all three systems |
| H2 | Class B costs more than Class A | Supported |
| H2b | The same without *é* | Only for Opus-MT |
| H3 | Typos cost less than Class B | Not supported: typos cost about 2.5 times more |
| H4 | Regression: b1 > b2, b3 near zero | Cannot be decided (collinearity) |
| H5 | BLEU hides the Class B damage | Supported for NLLB and Opus-MT, not certain for the LLM |
| H6 | The LLM loses least | Supported |

Numbers, charts and explanations: `results.ipynb`.

## How to rerun

```bash
python -m keyboard_tax.translate                 # step 4, on a GPU (Colab notebook)
python -m keyboard_tax.score                     # step 5, on a GPU for COMET
python -m keyboard_tax.analyze --save-results    # step 6, on a laptop; also refreshes results/
```
