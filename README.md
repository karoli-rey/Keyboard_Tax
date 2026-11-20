# The Keyboard Tax

What diacritic loss costs machine translation.
Course project for *Essentials in Text and Speech Processing*
Lucia Ivan, Karen Olivia Reyes Mendoza, Thomas Schurter.

## Goal

People often type Portuguese without accents. Some words then turn into other real words
(*pôde* "could" becomes *pode* "can"). We translate Portuguese into English and test whether
this changes the meaning, and whether the usual translation scores notice.

- **Class A:** without its accent, the word is not a word (*não → nao*). Looks like a typo.
- **Class B:** without its accent, the word is another real word (*pôde → pode*). Looks fine, means something else.

## Pipeline

```mermaid
flowchart LR
    S1["1 Load data"] --> S2["2 Label A / B"] --> R(["Native speaker check"]) --> S3["3 Damaged versions"]
    S3 --> S4["4 Translate"] --> S5["5 Score"] --> S6["6 Analyze"]
    C(["Challenge set: draft + native speaker check"]) --> S6
```

| Step | File | Owner | Writes |
|---|---|---|---|
| 1 | `data.py` | Coder 1 | `outputs/1_sentences.csv` |
| 2 | `classify.py` | Coder 1 | `outputs/2_lexicon_auto.csv`, `outputs/2_letters.csv` |
| review | by hand | Coder 1 (native speaker) | `data/lexicon.csv` |
| challenge set | `challenge.py`, then by hand | draft: Coder 2; check: Coder 1 (native speaker) | `data/challenge_set.csv` |
| 3 | `versions.py` | Coder 1 | `outputs/3_versions.csv` |
| 4 | `translate.py` | Coder 2 | `outputs/4_translations.csv` |
| 5 | `score.py` | Coder 2 | `outputs/5_scores.csv`, `outputs/5_corpus_scores.csv` |
| 6 | `analyze.py` | Coder 2 | `outputs/6_results/` (tables, charts, `summary.txt`) |

Each step reads the file the step before wrote. The columns of every file are fixed in
`src/keyboard_tax/common.py`, and `tests/fixtures/` has a small example of each one, so any
step can be built before the previous step is finished. Each file starts with a short
description of what the step does.

## Results

Open **`results.ipynb`**: the idea, every result with its chart and a short explanation.
It runs in a few seconds on any laptop (no GPU, no model, no dataset login), and its outputs
are stored in the file, so it can also just be read.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"                         # tests, results.ipynb, steps 1-3 and 6
scripts/get_dictionary.sh                       # pt_BR dictionary for step 2, to data/raw/
pytest                                          # run the tests: 98 passed
python -m keyboard_tax.versions --fixtures      # run a step on the example data
python -m keyboard_tax.versions                 # run a step on the real data
```

Steps 4 and 5 also need the models: `pip install -e ".[dev,models]"`, on Python 3.11 or 3.12
(torch has no release for Python 3.14 yet). For the full data they need a GPU: open
`scripts/colab_gpu_run.ipynb` in Google Colab (about one hour in all). Results come back as a zip; unzip it into `outputs/`.
On a laptop, try step 4 on the example data with
`python -m keyboard_tax.translate --fixtures --systems opus_mt`.

Step 6 runs on a laptop: `python -m keyboard_tax.analyze --save-results` (also refreshes `results/`).

All settings (models, seed, thresholds) are in `config.yaml`.

## How we work

| Role | Name | Owns |
|---|---|---|
| Coder 1 | Thomas Schurter | Steps 1–3; review of the word list and of the challenge set as native speaker |
| Coder 2 | Karen Olivia Reyes Mendoza | Steps 4–6; draft of the challenge set; `docs/pipeline.md` |
| Researcher | Lucia Ivan | Report structure; ideas for the introduction and for future work |

- One branch per task, merged through a pull request that a teammate reviews.
- Short commit messages that say what changed: `Add accent stripping`.
- Changes to `classify.py` always get a second reader: a bug there changes the main result.
- The use of AI tools is declared in the report.
- Files in `outputs/` are generated: never edit or commit them.

## Project map

```
results.ipynb        all results with charts and explanations: start here
results/             the scores the notebook reads (numbers only, no sentences)
config.yaml          all settings: models, seed, prompt, versions
pyproject.toml       the package and its dependencies
src/keyboard_tax/    the pipeline, one file per step
  common.py          shared helpers: settings, file names and columns, accent stripping
  data.py            step 1  load FLORES+
  classify.py        step 2  label Class A / B
  versions.py        step 3  damaged versions
  translate.py       step 4  three translation systems
  score.py           step 5  BLEU, chrF, COMET
  challenge.py       draft of the challenge set (used in step 6)
  analyze.py         step 6  tables, charts, targeted check, hypotheses
data/                what we release (CC BY-SA 4.0): word list and challenge set;
                     data/README.md is their datasheet
scripts/
  colab_gpu_run.ipynb  steps 4 and 5 on a free Colab GPU
  get_dictionary.sh    downloads the pt_BR dictionary for step 2
tests/               tests (pytest), with a small example of every table in fixtures/
docs/pipeline.md     how each step works and why, and what is not in the repository
.github/             runs the tests on every push; pull request template
outputs/             created by the code, never committed (holds FLORES+ sentences)
```

The report itself is written in Overleaf and handed in as a PDF; it is not part of this repository.

## License

Code: MIT (`LICENSE`). Data in `data/`: CC BY-SA 4.0, see `data/README.md`.
