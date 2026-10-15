# Decisions

## Open questions (the Researcher answers these in week 1, the team agrees)

- [ ] Which FLORES+ split do we report on?
- [ ] Which pt_BR dictionary (source, version, licence)?
- [ ] Frequency threshold for rare Class B words (`min_zipf`)?
- [ ] How do we skip names?
- [ ] Which LLM, its exact prompt, and where it runs (GPU or API)?
- [ ] Rule for the targeted check (who writes the patterns, who double-checks them)?
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
