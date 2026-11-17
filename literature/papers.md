# Papers

One short entry per paper. Newest entries at the bottom.

## Template

**Paper:** authors (venue year), title, link
**What they did:**
**What they found:**
**What they did not do:**
**How it relates to our project:**

---

## What the literature says so far (answer to the question in `README.md`)

Nobody we found has measured, for systems people actually use, what *ambiguous* accent loss
costs compared with harmless loss. Chen et al. (2024) come closest: they find that removing
diacritics barely changes BLEU for models they trained themselves, could not confirm that
meaning-changing diacritics hurt more, and say that a data set built for that question is
needed. Our lexicon and challenge set are such a data set, for Portuguese, tested on three
off-the-shelf systems. Work on typos (Belinkov and Bisk 2018; Liu et al. 2025) does not ask
whether the damaged word is still a real word.

## Entries

Written on 17 Nov from the papers' own pages with Claude's help (see `notes/ai_use.md`).
Before citing a paper in the report, read the passage you cite.

**Paper:** Chen, Adebara and Abdul-Mageed (NAACL 2024), Interplay of Machine Translation, Diacritics, and Diacritization. https://aclanthology.org/2024.naacl-long.420/
**What they did:** Trained their own small translation models for 55 languages into English (36 African languages on Bible text, 19 European languages on Europarl, Portuguese among them), with and without diacritics in the source, and with diacritization as a second task.
**What they found:** Keeping or removing diacritics changes BLEU very little (effect sizes 0.08 to 0.17). Learning to restore diacritics helps translation only with very little training data (up to 5,000 sentences).
**What they did not do:** No off-the-shelf systems. Translation is scored with BLEU only. They group languages by whether diacritics mark words or grammar, but the result is "not conclusive", and they say a data set built to contain such ambiguity would be needed. No word-level split into ambiguous and harmless loss.
**How it relates to our project:** The closest work, and the gap we fill: we build the data set they ask for (Class A / B lexicon, challenge set) and test systems people use, with COMET and a word-level check besides BLEU.

**Paper:** Duran, Avanço and Nunes (STIL 2015), A Importância dos Falsos Homógrafos para a Correção Automática de Erros Ortográficos em Português. https://sol.sbc.org.br/index.php/stil/article/view/3989
**What they did:** Studied 25,722 Portuguese word pairs that differ only by one diacritic ("false homographs"). A word typed without its accent is then itself a correct word, so a spellchecker cannot see the error.
**What they found:** 2,052 unaccented words are rarer than their accented partner and can be taken out of a spellchecker's word list, which helps with user-written text that often lacks accents.
**What they did not do:** Spelling correction only; no translation, no measure of what the confusion costs later.
**How it relates to our project:** Their false homographs are our Class B. It shows that the phenomenon is known and frequent in Portuguese, and that people do type without accents. We measure its cost for translation.

**Paper:** Belinkov and Bisk (ICLR 2018), Synthetic and Natural Noise Both Break Neural Machine Translation. https://arxiv.org/abs/1711.02173
**What they did:** Added synthetic noise (swapped letters, scrambled letters, neighbouring-key typos) and real human typos to French, German and Czech sources and translated into English with three kinds of models.
**What they found:** All models break: for German, BLEU falls from about 34 to about 1 on scrambled text and to about 11 on real typos. Training on noise helps only for the kind of noise seen in training.
**What they did not do:** No diacritics as a noise type, no Portuguese, no question whether the noisy word is still a real word. Models of 2017.
**How it relates to our project:** The reference for "noise breaks translation". Our typo baseline uses one of their noise types (neighbouring-key typos). Our result that typos cost more than missing accents fits their finding.

**Paper:** Liu, Zhao, Altinger, Schütze and Hedderich (arXiv 2025), Evaluating Robustness of Large Language Models Against Multilingual Typographical Errors. https://arxiv.org/abs/2510.09536
**What they did:** Built MulTypo, which inserts keyboard-based typos (replace, insert, delete, swap) in 12 languages, and tested 18 open LLMs on several tasks, translation on FLORES-200 among them.
**What they found:** Typos lower the scores in every task; larger models lose somewhat less; instruction tuning does not make models more robust. Translating into English suffers more than translating from English.
**What they did not do:** No Portuguese and no diacritic loss. They do not separate typos that give another real word from typos that give a non-word.
**How it relates to our project:** Recent evidence that LLMs are also sensitive to noisy input, on the same benchmark family. We add the real-word case (Class B), which their typo types leave out.

**Paper:** Müller, Rios, Voita and Sennrich (WMT 2018), A Large-Scale Test Set for the Evaluation of Context-Aware Pronoun Translation in Neural Machine Translation. https://aclanthology.org/W18-6307/
**What they did:** Built ContraPro: 12,000 English to German examples that test one thing, the translation of "it". The model must prefer the correct translation over versions with the wrong pronoun.
**What they found:** Models that use context gain only a little BLEU but up to 16 points of pronoun accuracy. Scores for overall quality hardly move for an error that touches one word.
**What they did not do:** Pronouns, not diacritics; their test scores given translations, ours checks the system's own output with word patterns.
**How it relates to our project:** The model for our challenge set and for H5: a test set aimed at one phenomenon shows damage that BLEU hides.

---

## Topics still to search

From Lucy's notes; not searched yet. Find one or two key papers per topic; they go in the Introduction
or in Future work, not in our experiments.

| Topic | Search terms | Report section |
|---|---|---|
| Restoring accents automatically | diacritic restoration, diacritization | Future work |
| Training MT on noisy or accent-free text | noise injection, data augmentation, robust NMT | Future work |
| Subword tokenizers and accented letters | BPE, tokenization, diacritics | Optional extras |
| Test sets that target one phenomenon | challenge set, contrastive evaluation, MT | Introduction |
| Why BLEU misses meaning errors | BLEU, COMET, metric sensitivity, meaning-changing errors | Evaluation |
| How often people really drop accents | accent omission, informal text, Portuguese social media | Introduction |
