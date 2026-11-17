# Decisions

## Open questions (the Researcher answers these in week 1, the team agrees)

- [x] Which FLORES+ split do we report on?
- [x] Which pt_BR dictionary (source, version, licence)?
- [x] Frequency threshold for rare Class B words (`min_zipf`)?
- [x] How do we skip names? (decided 2026-11-01)
- [ ] Which LLM, its exact prompt, and where it runs (GPU or API)? (proposed 2026-11-15, see the log; the team still has to agree)
- [x] sacreBLEU signatures (run of 16 Nov): BLEU `nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.6.0`, chrF `nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.6.0`
- [x] Rule for the targeted check: Coder 2 drafts the patterns (`data/challenge_words.csv`), the native speaker checks every row of `data/challenge_set.csv` (proposed 2026-11-16, see the log)
- [ ] Roles: who is Researcher, Coder 1 (steps 1–3), Coder 2 (steps 4–6)?

## Questions for the lecturer

- [ ] Grading split: 50/50 or 60/40 (report/project)? The instructions say both.
- [ ] Do references and the AI-use statement count toward the 5 pages?
- [ ] Is the 55 hours of project work per person or per team?

Once answered, move each one to the log below and copy the value into `config.yaml`.

## Log

One line per decision, with the reason. This becomes the Method section of the report.

| Date | Decision | Why | Who | Status |
|---|---|---|---|---|
| 2026-10-14 | Class A / B by dictionary lookup, not by an LLM | Reproducible; "is this a word?" needs no language understanding | Thomas | proposed |
| 2026-10-14 | Ask the dictionary through spylls `lookup()`, never read the .dic file as a list | The .dic file holds stems; inflected forms such as "tem" would be missing | Thomas | proposed |
| 2026-10-14 | Strip with Unicode NFD, drop combining marks, recompose with NFC | Unicode already holds the mapping; no hand-written table | Thomas | proposed |
| 2026-10-14 | Step 2 lists every accented letter for a one-time check by the native speaker | Unexpected letters (e.g. from foreign names) are seen, not silently handled | Thomas | proposed |
| 2026-10-14 | Native speaker reviews rare Class B words plus a random sample of others | Saves time; the sample measures how accurate the automatic labels are | Thomas, Karen | proposed |
| 2026-10-14 | Match A-only and B-only per sentence: strip k = min(#A, #B) words of each | A fair comparison; the regression covers small letter differences | Karen | proposed |
| 2026-10-14 | Noise: neighbouring-key typos, same letter count as B-only, never a real word | Same damage as B-only, without ambiguity | Thomas, Karen | proposed |
| 2026-10-14 | Release our data under CC BY-SA 4.0 | FLORES+ is CC BY-SA, and our data contains its sentences | Karen | proposed |
| 2026-10-14 | Portuguese committed; Romanian and Spanish only if time allows | Lecturer feedback: one language plus English | team | proposed |
| 2026-10-14 | Data: FLORES+ (`openlanguagedata/flores_plus`), not the older FLORES-200 | FLORES+ is the maintained version | Karen | proposed |
| 2026-10-14 | NLLB model: `facebook/nllb-200-distilled-600M` | Smallest NLLB model, so all versions fit in our GPU time | Karen | proposed |
| 2026-10-14 | Opus-MT model: `Helsinki-NLP/opus-mt-ROMANCE-en` | There is no official `opus-mt-pt-en` model | Karen | proposed |
| 2026-10-14 | COMET model: `Unbabel/wmt22-comet-da`, always given the clean source | Standard reference-based COMET; a damaged source would hide the damage | Karen | proposed |
| 2026-10-14 | Regression: one fit per system, on all damaged versions including noise, errors clustered by sentence | Noise rows let us separate the effect of changed letters from the effect of A and B words | Karen | proposed |
| 2026-10-14 | Lexicon gets a `lost` column: what a Class B word loses (e.g. tense) | Promised in the proposal | Karen | proposed |
| 2026-10-14 | No language term (γ) in the regression, no language-level fit | Only one language is committed | Karen | proposed |
| 2026-10-14 | Release two things, not three: lexicon and challenge set. The real-message collection moves to future work | Not enough time, and collecting messages raises privacy and terms-of-use questions | Karen | proposed |
| 2026-10-14 | Report uses the template headings; "Model training" becomes "Translation systems" | Graders look for the template questions; we train nothing | Lucy, Karen | proposed |
| 2026-10-14 | New folders: `literature/` for the literature review, `report/` for the outline | Keep research, report plan and team notes apart | Karen | proposed |
| 2026-11-01 | Skip a candidate name only if it never occurs lowercase and occurs capitalized away from a sentence start | Avoid treating sentence-initial capitalization as evidence that an accented word is a name | Coder 1 | proposed |
| 2026-11-13 | FLORES+ split: `devtest` (1012 sentences) | `dev` stays free for trying things out; `devtest` is the split papers usually report | Thomas | proposed |
| 2026-11-13 | Dictionary: LibreOffice pt_BR (VERO 3.2, LGPLv3/MPL), downloaded by `scripts/get_dictionary.sh`, not committed | Free, maintained Hunspell dictionary for Brazilian Portuguese; the licence allows use but we do not redistribute it | Thomas | proposed |
| 2026-11-13 | `min_zipf: 99`: the native speaker reviews every Class B word | wordfreq also counts text typed without accents, so the stripped form looks too frequent ("musica" has Zipf 4.0, almost only as a typo of "música"); a frequency cut would count such words as Class B without a check, although no reader takes them for the rare real word | Thomas | proposed |
| 2026-11-13 | Lexicon review in two passes: Claude (Anthropic) suggested labels for the 274 review words, then Thomas as native speaker checked and confirmed every one (`native_checked` = `yes`) | Faster review; the native speaker stays responsible for each label; the AI use is logged in `notes/ai_use.md` | Thomas | proposed |
| 2026-11-13 | A word is Class B only if its stripped form is used in normal written Brazilian Portuguese. Rare or archaic verb forms, 2sg (tu) forms, abbreviations, prefixes and foreign words count as Class A | The dictionary also accepts forms no reader would think of. Result: 98 of the 224 automatic Class B words stay B, 126 become A; all 50 sampled Class A words stay A | Thomas | proposed |
| 2026-11-15 | LLM: `Qwen/Qwen2.5-7B-Instruct`, loaded in 4-bit (`llm_4bit: true`) | Open weights (Apache 2.0), free to download, lists Portuguese among its languages, fits a free Colab GPU in 4-bit; not a Claude model, because Claude suggested the first-pass lexicon labels | Olivia | proposed |
| 2026-11-15 | LLM prompt: one fixed prompt in `config.yaml`, one sentence per request, no sampling (always the most likely next word); to be tried on `dev` sentences only, never on `devtest` | Repeatable answers; the prompt is not tuned on the sentences we report on | Olivia | proposed |
| 2026-11-15 | NLLB and Opus-MT: beam search with beam size 4, at most 256 new tokens, the same for both | A common default; equal settings keep the two translators comparable | Olivia | proposed |
| 2026-11-15 | Step 4 translates each distinct sentence once per system and saves every finished batch in `outputs/4_cache/`; the file name carries a code of the settings | Many versions share a text; a crashed GPU session loses nothing; changed settings never reuse old translations | Olivia | proposed |
| 2026-11-15 | LLM answers are cleaned by fixed rules (`clean_llm_output`): a label in front, notes after a blank line, quotation marks around the whole answer; the raw answer stays in the cache | Extra text such as "Here is the translation:" would lower the scores for a reason that has nothing to do with accents | Olivia | proposed |
| 2026-11-15 | Steps 4 and 5 run on a free Google Colab GPU (`scripts/colab_gpu_run.ipynb`); the results are downloaded as a zip file | The models are too slow on a laptop; Colab is free and the run can be repeated by anyone | Olivia | proposed |
| 2026-11-16 | `5_corpus_scores.csv` gets two new columns: `subset` ("all" or "both_classes") and `n` (number of sentences) | A-only, B-only and noise exist for only 422 sentences; comparing them with clean scores over all 1,012 sentences would mix two different sets of sentences | Olivia | proposed |
| 2026-11-16 | Step 5 scores each distinct (clean source, translation, reference) case once; an empty translation counts as an empty text | Many versions get the same translation; the result is the same and the run is faster | Olivia | proposed |
| 2026-11-16 | The LLM answered partly or fully in Chinese for 7 of its 3,254 distinct sentences (4 FLORES+ sentences, clean and stripped versions alike). We keep these answers unchanged and repeat the analysis without those 4 sentences | It is how the model behaves, not an effect of our damage; changing answers by hand would not be repeatable | Olivia | proposed |
| 2026-11-16 | COMET runs in its own Python environment on Colab (`uv venv`, section 11 of the notebook) | COMET needs older helper packages that clash with what Colab preinstalls (TensorFlow, protobuf); a separate environment avoids touching them | Olivia | proposed |
| 2026-11-16 | Main test of H2 and H3: paired differences between versions of the same sentence (b_only minus a_only, b_only minus noise), with 95% confidence intervals, on the 422 sentences with all five versions | Pairing removes the differences between sentences; the regression cannot separate "A words" from "changed letters" (they move almost together, correlation 0.88) | Olivia | proposed |
| 2026-11-16 | The regression stays in the results as planned, with its caveat printed next to it; it uses plain least squares with standard errors clustered by sentence (numpy only, no statsmodels) | Keeps the proposal's method visible and the install small | Olivia | proposed |
| 2026-11-16 | Robustness: every drop and contrast is repeated without the 182 sentences where "é" is the stripped Class B word, and without the 4 sentences the LLM answered in another script | "é" is 240 of 636 Class B occurrences; the Chinese answers are a quirk of the model | Olivia | proposed |
| 2026-11-16 | Challenge set drafted by script (`python -m keyboard_tax.challenge`) from 73 hand-written word rows in `data/challenge_words.csv`, then checked row by row by the native speaker (Thomas). We report how many of the 159 draft rows he kept or changed | The Researcher's file did not arrive; a script makes the draft repeatable, and the native speaker stays responsible for every row | Olivia | proposed |
| 2026-11-16 | A sentence enters the challenge set only if the English reference contains a right-reading word and no wrong-reading word | Otherwise the check could not tell the two readings apart, even for a perfect translation | Olivia | proposed |
| 2026-11-16 | Left out of the challenge set: *é, está, à, às, têm, nós, dá, pôr*, and nouns whose verb reading has the same English form (*dúvida*: doubt / doubts) | Their English difference is grammar ("is" or "and"); such words are in almost every sentence, so a word match cannot decide. The COMET drop still covers them | Olivia | proposed |
| 2026-11-16 | Targeted check: "right" if the English has a right-reading word and no wrong one, "wrong" for the opposite, "unclear" otherwise; accuracy = right / all. Damaged rows count only where the word really lost its accent | Simple, repeatable rule; "unclear" is not counted as right | Olivia | proposed |
| 2026-11-16 | H5 (BLEU hides the B damage): on the challenge sentences, compare the share by which corpus BLEU falls (clean to all accents removed) with the share by which targeted accuracy falls; supported if the lower end of the accuracy CI is above the BLEU share | Same sentences, same versions, one number each; the plan asked for exactly this comparison | Olivia | proposed |
| 2026-11-16 | H2b (H2 without *é*) uses the same paired contrast as H2 on the 240 sentences left when the 182 *é* sentences are removed | Shows whether the Class B effect is only an *é* effect | Olivia | proposed |
| 2026-11-17 | Challenge set after the review file from Thomas (16 Nov): of 159 draft rows 136 kept, 13 fixed, 10 deleted; 38 rows added by hand (among them a few *é, está, têm, à, às* sentences with sentence-specific patterns). Now 187 rows, 170 sentences, 74 words. `tráfego`, `prévia` and `experiência` also corrected in `data/challenge_words.csv`; `prévia` in the lexicon is now "adjective to verb". **Open:** the review file says "first pass by Claude, Thomas checks it before the challenge set is final", so Thomas still has to confirm that he checked the rows himself | Rows deleted where the word occurs twice, where another word in the sentence gives the same English, or where the two readings have the same English (*experiência*) | Thomas, Olivia | proposed |
