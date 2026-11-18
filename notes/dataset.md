# Dataset notes

Short answers with their source. This file feeds report section 2 (Data set).
Written by Olivia on 17 Nov; facts checked against the dataset card and our own run.

## FLORES+

**How was it built?**
English sentences were sampled in equal parts from Wikinews, Wikijunior and Wikivoyage and
translated into more than 200 language varieties by professional translators. It started as
FLORES-101 (3,001 sentences, 101 languages; Goyal et al. 2022), grew into FLORES-200 with the
NLLB project (NLLB Team 2024) and is now maintained as FLORES+ by the Open Language Data
Initiative (OLDI). Every language has the same sentences in the same order, so sentence *n* in
Portuguese is the translation of sentence *n* in English.

**Which split do we use, and how many sentences does it have?**
`devtest`: 1,012 sentences. `dev` (997 sentences) stays free for trying things out.
A third, hidden test set is not part of the public data.

**Which Portuguese variety is it?**
Brazilian Portuguese: the dataset card lists `por_Latn` with the Glottolog code `braz1246`.
That is why we use the pt_BR dictionary, and the text agrees (*ônibus*, *metrô*, *bebê*).

**Which information comes with each sentence (metadata)?**
`id`, `text`, the language codes (`iso_639_3`, `iso_15924`, `glottocode`, `variant`), `url` of
the English source article, `domain`, `topic`, `has_image`,
`has_hyperlink` and `last_updated` (FLORES+ version). Step 1 keeps only `id` and `text`
(`sent_id`, `pt`, `en` in `outputs/1_sentences.csv`).

**What is the licence, and what does it mean for our release?**
CC BY-SA 4.0. Our lexicon and challenge set contain FLORES+ sentences, so we release them under
the same licence, name the source, and say what we changed (`data/README.md`). The dataset is
meant for evaluation only and must not be used as training data; we train nothing.

**How do we get access?**
The dataset is gated on Hugging Face (`openlanguagedata/flores_plus`): log in, accept the
terms on the dataset page, create a read token, then `huggingface-cli login`. Everyone uses
their own token; it never goes into the code or the repository.

**Our numbers** (run of 13 Nov, `outputs/`)

| What | Number |
|---|---|
| Sentences (Portuguese with English reference) | 1,012 |
| Average length | 23 words (Portuguese), 22 words (English) |
| Sentences with at least one accented word from our word list | 963 |
| Accented word tokens | 3,319 (2,683 Class A, 636 Class B) |
| Accented word types in the word list | 1,144 (1,046 Class A, 98 Class B) |
| Sentences with both classes (all five versions) | 422 |

## Why FLORES+ and not something else?

**Why we chose FLORES+**
- Every Portuguese sentence has a professional English reference, which BLEU, chrF and COMET need.
- It is the standard public benchmark for translation, so our clean scores can be compared with
  published ones.
- It is correctly accented, edited text: every missing accent in our experiment is one we
  removed, so we know exactly what was damaged.
- It is free, has a clear licence, and is small enough to translate 3,290 versions with three
  systems on a free GPU.

**Alternatives considered**

| Alternative | Why not |
|---|---|
| Europarl, OpenSubtitles and other OPUS corpora | Opus-MT is trained on OPUS data, so it may have seen the test sentences |
| Tatoeba | Very short sentences with little context; context is what could rescue a Class B word |
| Real messages typed without accents (social media) | No English reference, and collecting them raises privacy and terms-of-use questions (moved to future work) |

**Limits of this choice** (for report section 6)
- FLORES+ is formal text (news, travel guides, children's encyclopedia). People drop accents
  mostly in informal writing, so we measure the cost on clean prose, not on real chat text.
- The sentences are translations from English, not text first written in Portuguese.
- FLORES has been public since 2021 to 2022, so the LLM may have seen it. We compare drops
  between versions of the same sentence, not absolute scores, which limits this problem.

## Other resources

**Portuguese dictionary**
LibreOffice pt_BR Hunspell dictionary (VERO 3.2), licence LGPLv3 / MPL. Downloaded by
`scripts/get_dictionary.sh` from a fixed commit of `LibreOffice/dictionaries`, never committed.
Step 2 asks it "is this a word?" through `spylls` 0.1.7.

**Word frequency list**
`wordfreq` 3.1.1 (Robyn Speer). Code Apache-2.0; data CC BY-SA 4.0. For Portuguese it combines
Wikipedia, subtitles, news, web text and Twitter, with data up to 2021 (the project is no
longer updated). Frequencies are on the Zipf scale: the base-10 logarithm of occurrences per
billion words (6 = once per thousand words, 3 = once per million). It also counts text typed
without accents (*musica* has Zipf 4.0), so we do not use it to decide Class B: the native
speaker reviews every Class B word (`min_zipf: 99`).

**Translation and scoring models**
See `config.yaml` and `notes/olivia_steps_4-6_notes.md`: NLLB-200 distilled 600M, Opus-MT ROMANCE-en,
Qwen2.5-7B-Instruct, COMET `wmt22-comet-da`.

## Sources

- FLORES+ dataset card: https://huggingface.co/datasets/openlanguagedata/flores_plus
- Goyal et al. (TACL 2022), The Flores-101 Evaluation Benchmark for Low-Resource and
  Multilingual Machine Translation: https://aclanthology.org/2022.tacl-1.30
- NLLB Team (Nature 2024), Scaling neural machine translation to 200 languages (cited on the
  dataset card)
- wordfreq: https://pypi.org/project/wordfreq/ and
  https://github.com/rspeer/wordfreq/blob/master/SUNSET.md
- LibreOffice dictionaries: https://github.com/LibreOffice/dictionaries
