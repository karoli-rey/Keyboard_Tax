# Report outline

First draft by Lucy, mapped onto the course template (14 Oct). The report itself is
written in Overleaf; this file is the plan. Edit it freely.

**Limits:** 5 pages of content, 11 pt, English, PDF on OLAT.
Headings follow the template, so the graders find every required question.

| # | Section | Pages | Content | Comes from |
|---|---|---|---|---|
| | Title, three authors, GitHub link, abstract | | Abstract: 4–5 sentences, written last | |
| 1 | Introduction | 0.75 | Accent dropping in Portuguese; Class A (*coração → coracao*) and Class B (*têm → tem*); research questions; related work and the gap | `literature/` |
| 2 | Data set | 0.5 | FLORES+ Portuguese → English: how it was built, split, metadata, why, alternatives | `notes/dataset.md` |
| 3 | Preprocessing | 1 | Accent stripping (Unicode NFD); Class A / B labels (dictionary + frequency, native-speaker check, precision); the damaged versions | steps 1–3 |
| 4 | Translation systems | 0.5 | Replaces "Model training": we train nothing. NLLB-200, Opus-MT, one LLM, and why these three | step 4 |
| 5 | Evaluation | 1.5 | BLEU, chrF, COMET; targeted check on the challenge set; regression; results table, one figure, two or three error examples | steps 5–6 |
| 6 | Future work and limitations | 0.5 | See below | |
| 7 | Optional extras | if space | Levels of linguistic organization (morphology: tense, person); tokenization of accent-free words | |
| | Use of AI tools | outside the 5 pages? (ask Sina) | Required by the CL guideline | `notes/ai_use.md` |
| | References | | From Overleaf | |

## Notes per section

**1 Introduction**
- Area of NLP: machine translation evaluation, robustness to noisy input.
- Write "we test whether", not "we prove". "BLEU barely notices" and "Class A is cheap" are
  hypotheses until our results say so.
- Keep examples to Portuguese.

**3 Preprocessing**
- Labels come from the Hunspell dictionary plus word frequency, not word frequency alone
  (word frequency lists contain "nao" as a word).
- Report how accurate the automatic labels were on the native-speaker sample (precision, recall).
- Versions: clean, all accents removed, Class A only, Class B only, typo noise.
  Strip rates of 25, 50 and 75% only if time allows.

**5 Evaluation**
- Regression: Δ = β0 + β1·b + β2·a + β3·c, one fit per system. No language term (one language).
- What we release, in two sentences: the reviewed word list (with what each Class B word loses)
  and the challenge set, CC BY-SA 4.0, described in `data/README.md`.

**6 Future work and limitations**
- Limitations: one language; FLORES+ is formal text, while people drop accents in casual text;
  large models may recover the meaning from context.
- Future work (from Lucy's notes): restoring accents before translation; training on accent-free
  text; Romanian and Spanish; a collection of real accent-free messages.
