# Report outline

The plan for the report, section by section (first draft by Lucy, 14 Oct; updated 18 Nov to
what we did). The report itself is written in Overleaf.

**Limits:** 5 pages of content, 11 pt, English, PDF on OLAT.
Headings follow the course template, so the graders find every required question.

| # | Section | Pages | Content | Source in the repo | Status |
|---|---|---|---|---|---|
| | Title, authors, GitHub link, abstract | | Abstract: 4–5 sentences, written last | | to write |
| 1 | Introduction | 0.75 | Accents dropped in Portuguese; Class A (*não → nao*) and Class B (*país → pais*); research questions; related work and the gap | `literature/papers.md` | to write |
| 2 | Data set | 0.5 | FLORES+ Portuguese → English: how it was built, split, metadata, why, alternatives | `notes/dataset.md` | notes ready |
| 3 | Preprocessing | 1 | Accent stripping (Unicode NFD); Class A / B labels (dictionary, native-speaker review); the five versions | `notes/thomas_steps_1-3_notes.md` | notes ready |
| 4 | Translation systems | 0.5 | Replaces "Model training": we train nothing. NLLB-200, Opus-MT, Qwen2.5-7B, and why | `report/sections_4_5.tex` | drafted |
| 5 | Evaluation | 1.5 | BLEU, chrF, COMET; paired drops with 95% CIs; challenge set; regression and its caveat; one table, one or two figures, three examples | `report/sections_4_5.tex`, `results.ipynb` | drafted, about 1 page too long |
| 6 | Limitations and future work | 0.5 | See below | | to write |
| | Use of AI tools | outside the 5 pages? (ask the lecturer) | Required by the UZH and CL guidelines | | to write in Overleaf |
| | References | | From Overleaf | | to write |

## Notes per section

**1 Introduction**
- Area of NLP: machine translation evaluation, robustness to noisy input.
- Motivation (Lucy's notes): a Class B loss is a silent failure. The translation reads fluent
  and grammatical, but means something else, so scores can miss it.
- The gap (`literature/papers.md`, first paragraph): nobody has measured, for systems people
  use, what ambiguous accent loss costs compared with harmless loss.
- Keep examples to Portuguese.

**3 Preprocessing**
- Class A / B: a word is Class B if its stripped form is a word in the pt_BR Hunspell
  dictionary and is used in normal written Brazilian Portuguese. No frequency threshold:
  frequency lists also count text typed without accents (*musica*).
- Native-speaker review: of 224 automatic Class B words, 98 stay B and 126 become A; all 50
  sampled Class A words stay A. Word list: 1,144 words (1,046 A, 98 B).
- Versions: clean, all accents removed, Class A only, Class B only (same number of words),
  typos (same number of letters as Class B only). 422 sentences have all five.

**5 Evaluation**
- Main test: paired drops (clean minus damaged, same sentence) with 95% CIs.
- The planned regression is reported with its caveat: Class A words and changed letters are
  collinear (correlation 0.88), so it cannot separate them (H4 undecided).
- What we release, in two sentences: the reviewed word list (with what each Class B word
  loses) and the challenge set, CC BY-SA 4.0, described in `data/README.md`.

**6 Limitations and future work**
- Limitations: one language pair; FLORES+ is formal text, while people drop accents in casual
  text; the challenge set uses word matching (3–10% unclear); one native speaker.
- Future work (from Lucy's notes): restoring accents before translation; training on
  accent-free text; Romanian and Spanish; a collection of real accent-free messages.
- Practical takeaway (Lucy's notes): apps that translate casual text should restore accents
  first; our results say where it matters most (meaning pairs and future verbs).
