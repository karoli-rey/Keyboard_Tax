> **Review, 14 Oct 2026.** Most of these notes are adopted (see `notes/decisions.md`).
> Four corrections before anyone relies on them:
>
> 1. **Licence:** our data must be released under **CC BY-SA 4.0**, not CC-BY, because FLORES+ is CC BY-SA.
> 2. **Matching (section 4):** word counts *can* be matched per sentence: strip k = min(#A, #B) words of each class.
>    In the example sentence that gives 3 and 3, and choosing words with one diacritic also matches the letters (3 and 3).
>    The demo strips *all* words of a class, which is why it looks unmatchable.
> 3. **Character map (section 5):** the generator must list letters only. On real FLORES text it would also flag
>    punctuation and symbols (“ ” — € °) as "special_map needed". Fixed in step 2 (`letter_table` in `src/keyboard_tax/classify.py`).
>    The example output in section 5 came from four sample sentences, not from FLORES.
> 4. **LLM for the challenge set (section 6):** fine as a helper, but use a different LLM from the one we evaluate,
>    log it in `notes/ai_use.md`, and report agreement with the native speaker (Cohen's kappa).
>
> Also check: UniMorph is not named in the session 1 slides we have; confirm before claiming it is course material.

---

# Keyboard Tax: Technical Notes

**For Lucy and Olivia. Working notes from Thomas, to be folded into the project plan.**
Everything below is a proposal or a finding, not a decision. Argue with any of it.

---

## 0. What changed since the plan

| Item | Status |
|---|---|
| Languages | Three, each with a native speaker in the team |
| Class A/B assignment | Dictionary lookup, **not** an LLM, see section 6 |
| Character mapping config | Generated, not hand written, see section 5 |
| Dictionary source | Hunspell, with one important trap, see section 7 |

---

## 1. Languages

| Language | Speaker | Tier | Why |
|---|---|---|---|
| Portuguese | Thomas | **Must** | Many Class B collisions where grammar is lost, not vocabulary |
| English | not needed | **Must** | Target language for all translations, and the zero line in the analysis |
| Romanian | Lucy | Should | Same kind of grammatical loss in a different place, plus a real encoding problem |
| Spanish | Olivia | Could | Cheap to add once the pipeline runs |

Sina told us to hold to one language plus English for the committed scope, so Portuguese is the only one we promise. Romanian and Spanish ride along in the optional tiers.

The practical consequence: Lucy and Olivia can create their language config files in about twenty minutes each, and the automatic numbers for their languages run from day one. Whether their languages also get a challenge set is a decision for week 4, based on how we are doing on time.

### Why Romanian is a good second language

Romanian marks definiteness at the end of the word, and the difference is often exactly one diacritic.

- *casă* is a house, *casa* is the house
- *fată* is a girl, *fata* is the girl

Strip the accent and the article disappears. That is the same phenomenon as Portuguese *têm* against *tem*, except that it attacks a different grammatical category. If the effect shows up in both, it is not a quirk of Portuguese.

There are lexical pairs too, such as *țara* (the country) against *tara* (flaw), or *păr* (hair) against *par* (pole). **Lucy should confirm these before any of them goes into the paper.**

Romanian also hands us a second gift. The letters ș and ț exist in two different Unicode encodings, one with a comma below (U+0219, U+021B) and one with a cedilla (U+015F, U+0163), and which one a text uses depends on when and how it was written. That is exactly the kind of writing-system infrastructure problem the course discusses in the low-resource session, and we can demonstrate it on real data instead of only citing it.

**Two things for Lucy to check in week 1:**

1. Which Unicode form does FLORES use for Romanian? We have to normalise explicitly, and a test should cover both forms.
2. The â and î spelling rule (î at the start and end of a word, â inside it, for the same sound) needs a line in the language config so nobody is confused later.

### Spanish

Classic collisions: *sí* / *si*, *él* / *el*, *tú* / *tu*, *más* / *mas*, *está* / *esta*, *práctico* / *practico* / *practicó*. The last one is a three way collision across tense and person, which is the same grammatical-loss pattern we are after.

---

## 2. What the project is, end to end

It is not an app. We hand in a PDF report that links to a public GitHub repository. The code is a Python package that runs from the command line.

Here is one sentence going through the entire experiment. This is the whole project in miniature.

```
FLORES gives us both sides of the same line:

  Portuguese:  "Eles têm dois filhos e ela não pôde vir."
  English:     "They have two children and she could not come."   <- our reference

Condition "clean":
  source   = "Eles têm dois filhos e ela não pôde vir."
  -> NLLB -> "They have two children and she could not come."
  -> COMET against the reference:  0.89

Condition "strip-100":
  source   = "Eles tem dois filhos e ela nao pode vir."
  -> NLLB -> "He has two children and she cannot come."
  -> COMET against the reference:  0.61

  Delta s   = 0.28
  n_class_b = 2   (têm, pôde)
  n_class_a = 1   (não)
  n_chars   = 3
```

(The COMET values are illustrative. The structure is real.)

That is one row in the results table. Multiply by about 1000 sentences, five conditions and three MT systems.

**The important detail:** we do not compare the two English outputs to each other. We compare each one against the human reference from FLORES, and the difference between the two scores is the measurement. Comparing the outputs to each other would measure instability rather than loss of quality, and we would lose the whole baseline-and-ceiling framing from the evaluation lecture.

---

## 3. FLORES, concretely

FLORES-200 is an **evaluation benchmark**, not training data. Meta's NLLB team took around 3000 sentences from Wikimedia projects (Wikinews, Wikivoyage, Wikijunior) and had them professionally translated into 200+ languages.

The property that matters for us: **the same sentences in every language.** Sentence 417 in Portuguese is the translation of sentence 417 in English and means the same thing as sentence 417 in Romanian. This is called n-way parallel.

That is why we need FLORES rather than any Portuguese corpus. If Portuguese degrades more than Spanish, it cannot be because the Portuguese sentences happened to be harder. They were the same sentences.

### The physical shape

Simpler than you would think. One plain text file per language, one sentence per line, and the line number is the link.

```
devtest/
  eng_Latn.devtest     <- line 417
  por_Latn.devtest     <- line 417 is its translation
  ron_Latn.devtest     <- same
  spa_Latn.devtest     <- same
```

Two splits: `dev` with 997 sentences and `devtest` with 1012. We use `devtest`.

### Illustrative example

The sentences below are constructed, not real FLORES rows, but the form and register are right.

| File | Line 417 |
|---|---|
| `eng_Latn` | The new bridge was opened to traffic in March and connects the two parts of the city. |
| `por_Latn` | A nova ponte foi aberta ao **trânsito** em **março** e liga as duas partes da cidade. |
| `ron_Latn` | Noul pod a fost deschis **circulației** în martie **și** leagă cele **două părți** ale **orașului**. |
| `spa_Latn` | El nuevo puente se **abrió** al **tráfico** en marzo y une las dos partes de la ciudad. |

Now strip the Portuguese accents:

```
Original:   ...aberta ao trânsito em março e liga...
Stripped:   ...aberta ao transito em marco e liga...
```

Both changed words are **Class B**, meaning real collisions:

- *trânsito* (traffic) becomes *transito*, which is the first person singular of *transitar*
- *março* (March) becomes *marco*, which is a word of its own (landmark, boundary stone) and also a first name

Spanish shows the same pattern: *tráfico* becomes *trafico*, first person singular of *traficar*.

### Loading it

```python
from datasets import load_dataset

pt = load_dataset("openlanguagedata/flores_plus", "por_Latn", split="devtest")
en = load_dataset("openlanguagedata/flores_plus", "eng_Latn", split="devtest")

print(pt[416]["text"])   # line 417, zero indexed
print(en[416]["text"])
```

**Check the dataset name in week 1.** It has moved over the years. It used to be `facebook/flores`; the maintained continuation is `openlanguagedata/flores_plus`. Try it rather than assume.

### Two limitations to record

**FLORES is formal prose.** The sentences come from Wikipedia articles and news, not from chat messages. So we measure what accent loss costs in clean written text, not in real phone text. This belongs in the Limitations section.

**FLORES has been public since 2022,** so modern LLMs may have seen it in training and their clean scores could be inflated. For our actual contrast this does not matter, because we compare Class A against Class B and both would be equally affected. One sentence in Limitations.

---

## 4. The perturb stage: how sentences get modified

The program does this, not a person, and it is deterministic with a fixed seed.

Take this Portuguese sentence:

> Eles têm três filhos, mas a mãe não pôde vir à estação.

First, each accented word gets a class:

```
Token        stripped     Class    What is lost
têm          tem          B        tem = he/she has    -> number
três         tres         A        tres is not a word  -> recoverable
mãe          mae          A        recoverable
não          nao          A        recoverable
pôde         pode         B        pode = can          -> tense
à            a            B        a = the/to          -> preposition
estação      estacao      A        recoverable
```

Three B and four A in a single sentence.

Then the one original sentence becomes seven variants. This is real output from a working script:

```
clean            a=0  b=0  chars=0
    Eles têm três filhos, mas a mãe não pôde vir à estação.

drop-25          a=2  b=0  chars=2
    Eles têm tres filhos, mas a mãe nao pôde vir à estação.

drop-50          a=3  b=0  chars=3
    Eles têm tres filhos, mas a mae nao pôde vir à estação.

drop-100         a=4  b=3  chars=8
    Eles tem tres filhos, mas a mae nao pode vir a estacao.

class_a_only     a=4  b=0  chars=5
    Eles têm tres filhos, mas a mae nao pôde vir à estacao.

class_b_only     a=0  b=3  chars=3
    Eles tem três filhos, mas a mãe não pode vir a estação.

random_matched   a=0  b=0  chars=8
    Eles tên rrês fikhps, maa a mãe não pôse vot à estação.
```

**Compare the two middle conditions.** In `class_a_only` the sentence looks more damaged, but every broken word can be worked out unambiguously. In `class_b_only` the sentence looks almost normal, but it now says *he has* instead of *they have* and *can* instead of *could*. That contrast is the entire project in two lines of text.

And `random_matched` shows why we need the control: eight changed characters, same as drop-100, but visibly destroyed. Our expectation is that the model copes better with this than with `class_b_only`, even though it looks far worse.

### One honest detail about matching

`class_a_only` has four tokens and five characters here, `class_b_only` has three and three. Per sentence you can never match exactly. Two fixes, and we need both:

- **For the figure:** match at corpus level by subsampling the larger class down.
- **For the statistics:** the regression handles it anyway, because `a` and `b` are separate predictors.

---

## 5. The character mapping: why there is no hand written config

This caused confusion, so here it is in full.

### Unicode already contains the mapping

A character like ê is not atomic. Unicode records its decomposition:

```
Character         : ê
One code point    : U+00EA   (LATIN SMALL LETTER E WITH CIRCUMFLEX)
Unicode says      : 0065 0302     <- 0065 is "e", 0302 is the circumflex
```

So stripping works like this:

```
before : 'têm'   ->  U+0074  U+00EA  U+006D            3 code points
NFD    : 'têm'   ->  U+0074  U+0065  U+0302  U+006D    4, the ê has fallen apart
filter : 'tem'   ->  U+0074  U+006D  U+0065            combining mark dropped
```

After NFD, ê is literally an `e` followed by a floating accent. We throw away everything that is a combining mark. Which base letter remains was never our decision; it was built into the ê.

In the first 8192 code points alone, 889 characters carry such a decomposition. Writing that table by hand would mean copying something that already exists, and every typo would be a silent bug.

### The code

```python
import unicodedata

def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )
```

Four lines. Run with **zero configuration** on eight languages:

```
Portuguese    Eles têm três filhos, mas a mãe não pôde vir à estação.
              Eles tem tres filhos, mas a mae nao pode vir a estacao.

Romanian      Noul pod a fost deschis circulației și leagă două părți ale orașului.
              Noul pod a fost deschis circulatiei si leaga doua parti ale orasului.

Spanish       El nuevo puente se abrió al tráfico en marzo; el niño está aquí.
              El nuevo puente se abrio al trafico en marzo; el nino esta aqui.

French        Où est la forêt? Ça coûte très cher à Noël.
              Ou est la foret? Ca coute tres cher a Noel.

Czech         Příliš žluťoučký kůň úpěl ďábelské ódy.
              Prilis zlutoucky kun upel dabelske ody.

Vietnamese    Tôi đã đến đó nhưng không thấy gì cả.
              Toi đa đen đo nhung khong thay gi ca.      <-- leftover: đ

German        Schön, dass die Mütter größer sind.
              Schon, dass die Mutter großer sind.        <-- leftover: ß

Turkish       Açık havada ılık bir gün geçirdik.
              Acık havada ılık bir gun gecirdik.         <-- leftover: ı
```

**For our three languages the leftover column is empty.** Portuguese, Romanian and Spanish need no special handling at all. Only đ, ß and ı are base letters in their own right, with no decomposition, and they would need an explicit entry.

### What the config actually holds

```yaml
# configs/por.yaml
code: por
flores_code: por_Latn
dictionary: hunspell/pt_BR
special_map: {}          # empty
translit_map: null       # Portuguese has no ASCII convention
```

```yaml
# configs/ron.yaml
code: ron
flores_code: ron_Latn
dictionary: hunspell/ro_RO
special_map: {}
normalize_unicode:       # pull the cedilla variant onto the comma variant
  "ş": "ș"
  "ţ": "ț"
translit_map: null
```

```yaml
# configs/spa.yaml
code: spa
flores_code: spa_Latn
dictionary: hunspell/es_ES
special_map: {}
translit_map: null
```

The Romanian `normalize_unicode` block is a different thing from stripping. Both variants of ș strip to s anyway. But as long as they are different characters, the program counts them as different words and looks them up differently. So we unify them **before** stripping.

If a language had its own ASCII convention it would go into `translit_map`. German would be the case: ö to oe, ß to ss. Our three languages do not have one; people simply drop the accent.

### But we still want it written down, so we generate it

For the paper we have to be able to say exactly which characters were touched. The answer is to **generate** the table, freeze it and commit it:

```yaml
# configs/por_charmap.yaml
# GENERATED from FLORES por_Latn. Do not edit by hand.
# Generated with Unicode 14.0.0
mapping:
  "ã": "a"    #   7x  U+00E3  latin small letter a with tilde  [ok]
  "ç": "c"    #   3x  U+00E7  latin small letter c with cedilla  [ok]
  "ê": "e"    #   2x  U+00EA  latin small letter e with circumflex  [ok]
  "ô": "o"    #   2x  U+00F4  latin small letter o with circumflex  [ok]
  "à": "a"    #   2x  U+00E0  latin small letter a with grave  [ok]
  "â": "a"    #   1x  U+00E2  latin small letter a with circumflex  [ok]
  "ó": "o"    #   1x  U+00F3  latin small letter o with acute  [ok]
  "é": "e"    #   1x  U+00E9  latin small letter e with acute  [ok]
  "á": "a"    #   1x  U+00E1  latin small letter a with acute  [ok]
```

The workflow:

1. Scan the corpus for every non-ASCII character
2. Ask Unicode for its decomposition
3. Write the table out with counts and a status flag
4. Commit the file
5. The native speaker reads it and signs it off (nine lines for Portuguese, thirty seconds)
6. From then on the pipeline checks **against** this file

Step 6 is the real gain. The frozen table is no longer an input, it is a guard. If a character shows up in the corpus that is not in the file, the run fails loudly instead of quietly doing something wrong.

The status flag is also how we **find** the exceptions rather than guessing them. For Portuguese everything says `ok`. If a corpus contained ß, ı or đ the status would read `NOT DECOMPOSABLE -> special_map needed`. Lucy runs the generator over the Romanian corpus and reads the status column; if nothing is flagged, her `special_map` stays empty.

---

## 6. Class A and B assignment: no LLM

### The core is three lines

```python
def classify(token, vocab):
    stripped = strip_diacritics(token)
    if stripped == token:
        return "none"                      # had no diacritic
    return "B" if stripped in vocab else "A"
```

*têm* becomes *tem*, *tem* is in the dictionary, so Class B. *não* becomes *nao*, *nao* is not in the dictionary, so Class A.

### Why not an LLM

**Reproducibility is a graded criterion.** A dictionary lookup gives the same answer in three years. An LLM API does not, and we could not defend the numbers later.

**The question is decidable, not a judgement call.** "Is this string in the vocabulary" needs no language understanding. Using an LLM for it would be like replacing `x in set` with an API call.

**The low-resource lecture warns about exactly this.** The slide on LLM-as-annotator carries the caveat that LLM knowledge of less widely spoken languages is often shallow. For Romanian we would walk straight into it.

### The dictionary alone is not enough

Three problems need a human:

1. **Accent-free spellings inside the dictionary.** This is Issue 1 from the plan. `wordfreq` is built partly from social media, where people drop accents, so `nao` is in there with a real frequency, and a clear Class A case gets labelled Class B. Hence Hunspell, which by definition contains only correct orthography.

2. **Rare collision partners.** *avô* becomes *avo*, and *avo* is formally a Portuguese word (the denominator of a fraction). Technically Class B, practically nobody will ever read it that way. These cases need a frequency threshold and human judgement.

3. **Vocabulary gaps.** Proper nouns and loanwords are often missing, so something gets labelled Class A although the collision partner does exist.

### What the native speaker actually reviews

Important for effort estimation: **word types, not occurrences.** The review list looks like this (frequencies here are simulated, the real ones come from the dictionary or a frequency list):

```
accented      stripped     Class   Zipf   Note
----------------------------------------------------------------------------
têm           tem          B       5.8    frequent, clearly Class B
pôde          pode         B       5.5    frequent, clearly Class B
à             a            B       7.2    frequent, clearly Class B
é             e            B       7.0    frequent, clearly Class B
pôr           por          B       6.1    frequent, clearly Class B
nós           nos          B       5.4    frequent, clearly Class B
está          esta         B       5.9    frequent, clearly Class B
vêm           vem          B       5.0    frequent, clearly Class B
avô           avo          B       2.1    RARE -> check, maybe count as A
março         marco        B       4.3    RARE -> check, maybe count as A
trânsito      transito     B       4.0    RARE -> check, maybe count as A
sábia         sabia        B       4.4    RARE -> check, maybe count as A
secretária    secretaria   B       4.2    RARE -> check, maybe count as A
não           nao          A       -      not a word, recoverable
três          tres         A       -      not a word, recoverable
mãe           mae          A       -      not a word, recoverable
estação       estacao      A       -      not a word, recoverable
```

Only the rows marked RARE go to a person. The threshold (4.5 in the example above) is arbitrary and flags a few cases that are in fact unproblematic. **Which threshold we pick is a decision we have to make and state in the paper.**

Portuguese FLORES probably has a few hundred distinct accented word types, of which maybe fifty to eighty land in the review band. That is one to two hours, not weeks. And because a few frequent types cover most occurrences, checking the top thirty would be enough at a pinch.

### The full workflow

```
1. load the Hunspell dictionary
2. strip and look up every accented word type         automatic
3. attach frequency, flag borderline cases            automatic
4. write the review list as CSV                       automatic
5. native speaker works through the flagged rows      1 to 2 hours
6. freeze the corrected list and commit it            <- the source of truth
7. the pipeline reads only this file from now on
```

Step 6 is where a heuristic becomes a resource. That file **is** our collision lexicon, one of the three things we release under CC-BY.

### Where an LLM does belong

There is one place, and it is a different job from classification. Two levels:

- **Type level: is *tem* a word?** Decidable, context free, dictionary. No LLM.
- **Token level: was *têm* or *tem* meant in this particular sentence?** Context dependent, real language understanding.

The second is exactly what we need for every item in the challenge set, about 250 sentences per language. There an LLM can propose and the native speaker confirms or corrects. It saves real time. Two conditions so it holds up in the paper: we report how often human and LLM agreed, and the human always wins on disagreement.

That also gives us a second number for free, namely how well an LLM handles this task in our three languages. That is the very question the low-resource lecture raises about LLM-as-annotator, and we could answer it empirically instead of only citing it.

### What goes into the Method section

Roughly:

> Class membership is assigned automatically. A word is Class B if removing its diacritics yields a form that appears in the Hunspell dictionary for that language above a Zipf frequency of X, and Class A otherwise. A native speaker reviewed all candidates near the threshold and corrected N of M types. The resulting lexicon is released with the code.

### Two safeguards on this module

`classify.py` is the one place where a bug would quietly corrupt the headline result while the numbers still look plausible. Two cheap protections:

**Unit tests before anything else** for the three critical functions: the accent stripping, the A and B labelling, and the edit-distance matching of the control condition. Maybe two hours of work, and they protect every number that ends up in the paper.

**Every change to `classify.py` gets a second reader** before it is merged. Not on principle, but because this is the module where a plausible-looking mistake is invisible from the outside.

---

## 7. Dictionaries: where to get them, and one trap

### Sources

| Source | How |
|---|---|
| **LibreOffice dictionaries** | github.com/LibreOffice/dictionaries, one folder per language, the canonical collection |
| **System packages** | `apt install hunspell-pt-br hunspell-ro hunspell-es`, or Homebrew, lands in `/usr/share/hunspell/` |
| **wooorm/dictionaries** | npm collection on GitHub, cleanly packaged with explicit per-language licence info |

A dictionary is always two files: `pt_BR.dic` with the stems and `pt_BR.aff` with the inflection rules. We need both.

Availability is good for all three of our languages: `pt_BR` and `pt_PT`, `ro_RO`, `es_ES` plus regional variants.

### The trap, and it would be fatal for us

**The `.dic` file is not a word list.** It contains stems with inflection flags. A line looks like this:

```
cat/SM
walk/GDS
```

The `S` generates the plural, the `D` the past tense, and so on. If we read the file naively as a word list, every inflected form is missing. Here is the direct comparison on the English dictionary:

```
Word         naive in .dic?   spylls lookup?
------------------------------------------------
cat          True             True
cats         False            True      <-- not in the file, but a word
walk         True             True
walked       False            True      <-- same
walking      True             True
happiness    True             True
unhappy      True             True
```

Now apply that to our problem. *tem* is the third person singular of *ter*, an inflected form. Depending on how the Portuguese dictionary is built, *tem* may not appear as a line at all. A naive read would classify *têm* to *tem* as **Class A**, although it is our flagship Class B example. Our central result would be broken, and the numbers would still look plausible.

**Rule: ask the spell checker, do not read the file.**

```python
from spylls.hunspell import Dictionary

d = Dictionary.from_files("dicts/pt_BR")

def is_word(w):
    return d.lookup(w)
```

`spylls` is a pure Python implementation of Hunspell. No C library needed, so it also works in Colab without trouble. The alternative `cyhunspell` is faster but painful to install on some platforms. At a few thousand lookups the speed difference does not matter.

### Two things for reproducibility

**Pin the version.** Dictionaries change. Download the files once, commit them to the repo or pin the source commit, and record the version in the datasheet. Otherwise someone gets different numbers in two years and we cannot say why.

**Note the licence.** The LibreOffice dictionaries carry different licences per language: LGPL, GPL or MPL. Our collision lexicon goes out under CC-BY. One sentence in the datasheet stating which dictionary and which version was used covers it, and it belongs there anyway.

### A bonus worth checking: UniMorph

Our collision lexicon has a column for "which piece of grammar is lost". We may not have to fill it by hand. **UniMorph** provides tables of the form

```
ter    têm    V;IND;PRS;3;PL
ter    tem    V;IND;PRS;3;SG
```

The difference between the feature sets is exactly the information that disappears when stripping, here PL against SG, so number. That could be derived automatically, with the native speaker only spot checking.

Two reasons this fits us: UniMorph covers Portuguese, Romanian and Spanish, and it already appeared in the course, in the extra exercise on the index of synthesis in session 1. Referring to it shows we are using the course material rather than only citing it.

**Check coverage before relying on it.** If UniMorph is thin for Romanian, the column stays manual for the most frequent pairs.

---

## 8. Additions to the week 1 checklist

| Item | Suggested owner |
|---|---|
| Check which FLORES dataset name currently loads | Thomas |
| Check which Portuguese variety FLORES uses, Brazilian or European, and pick the matching dictionary | Thomas |
| Check the Romanian Unicode form in FLORES, comma below or cedilla | Lucy |
| Test whether `nao` and `voce` appear in the chosen dictionary | Lucy |
| Decide and document the frequency threshold for rare collision partners | all three |
| Confirm the Romanian example pairs before they go into the paper | Lucy |
| Check UniMorph coverage for all three languages | Olivia |
| Download and pin the dictionaries, record versions in the datasheet | Thomas |
| Read Chen et al. 2024 and write one paragraph on how we differ | Lucy |

### Still open

- Do references and an appendix count towards the five content pages? (ask the lecturers)
- Is the 55 hour figure per person or for the whole team? (ask the lecturers)
- Does Spanish get a challenge set, or only the automatic numbers? (decide in week 4)

---

*Scripts referenced here (`perturb_demo.py`, `gen_charmap.py`, `show_unicode.py`) run on the standard library alone and are in the shared folder.*
