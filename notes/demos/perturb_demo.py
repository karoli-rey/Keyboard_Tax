"""Demo of the perturb stage: how one sentence becomes the different versions.

By Thomas (exploration, not pipeline code). Comments translated from German.
Uses a tiny word list instead of the real dictionary. Note: here class_a_only and
class_b_only strip ALL words of their class; the pipeline matches the counts instead
(see src/keyboard_tax/versions.py).
"""

import unicodedata
from random import Random

# ---------------------------------------------------------------- 1. Stripping


def strip_diacritics(text: str) -> str:
    """é -> e, ã -> a, ç -> c. Language independent, via Unicode decomposition."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


# ------------------------------------------------- 2. Dictionary (mini version)
# In the real project: Hunspell pt_BR. Here only the words this demo needs.

VOCAB = {
    "a", "as", "ao", "aos", "mas", "e", "em", "da", "de", "do", "vir",
    "eles", "elas", "filhos", "filho", "cidade",
    "tem", "tens", "ter", "pode", "podem", "poder",
    "marco", "marcos", "transito", "nova", "novo", "ponte", "aberta",
    "liga", "ligar", "duas", "partes", "parte",
}


def classify(token: str) -> str:
    """A = stripped form is not a word. B = stripped form is another word."""
    low = token.lower()
    stripped = strip_diacritics(low)
    if stripped == low:
        return "none"  # had no diacritic at all
    return "B" if stripped in VOCAB else "A"


# ----------------------------------------------------------- 3. Versions

KEYBOARD_NEIGHBOURS = {
    "a": "sq", "e": "wr", "i": "ou", "o": "ip", "u": "yi",
    "s": "ad", "t": "ry", "n": "bm", "r": "et", "c": "xv",
    "d": "sf", "l": "k", "m": "n", "p": "o", "v": "cb",
}


def perturb(sentence: str, mode: str, rate: float = 1.0, seed: int = 0):
    rng = Random(seed)
    tokens = sentence.split(" ")
    out, n_a, n_b, n_chars = [], 0, 0, 0

    for tok in tokens:
        cls = classify(tok.strip(".,;:!?"))
        stripped = strip_diacritics(tok)
        changed = sum(1 for x, y in zip(tok, stripped) if x != y)

        take = False
        if mode == "clean":
            take = False
        elif mode == "drop":
            take = cls in ("A", "B") and rng.random() < rate
        elif mode == "class_a_only":
            take = cls == "A"
        elif mode == "class_b_only":
            take = cls == "B"

        if take:
            out.append(stripped)
            n_chars += changed
            n_a += cls == "A"
            n_b += cls == "B"
        else:
            out.append(tok)

    text = " ".join(out)

    # Control condition: same number of changed letters, but at random positions
    if mode == "random_matched":
        budget = sum(
            sum(1 for x, y in zip(t, strip_diacritics(t)) if x != y) for t in tokens
        )
        chars = list(sentence)
        positions = [i for i, c in enumerate(chars) if c.lower() in KEYBOARD_NEIGHBOURS]
        rng.shuffle(positions)
        for i in positions[:budget]:
            chars[i] = rng.choice(KEYBOARD_NEIGHBOURS[chars[i].lower()])
        text, n_a, n_b, n_chars = "".join(chars), 0, 0, budget

    return {"text": text, "n_a": n_a, "n_b": n_b, "n_chars": n_chars}


# ------------------------------------------------------------------ 4. Demo

SENTENCE = "Eles têm três filhos, mas a mãe não pôde vir à estação."

print("=" * 78)
print("Word analysis")
print("=" * 78)
print(f"{'Token':<12} {'stripped':<12} {'Class':<8} What is lost")
print("-" * 78)
notes = {
    "têm": "tem = he/she has    -> number lost",
    "três": "tres is not a word  -> recoverable",
    "mãe": "mae is not a word   -> recoverable",
    "não": "nao is not a word   -> recoverable",
    "pôde": "pode = can          -> tense lost",
    "à": "a = the/to          -> preposition lost",
    "estação": "estacao not a word  -> recoverable",
}
for tok in SENTENCE.split(" "):
    bare = tok.strip(".,;:!?")
    cls = classify(bare)
    if cls != "none":
        print(f"{bare:<12} {strip_diacritics(bare):<12} {cls:<8} {notes.get(bare, '')}")

print()
print("=" * 78)
print("The versions")
print("=" * 78)
for mode, rate in [
    ("clean", 0.0), ("drop", 0.25), ("drop", 0.50), ("drop", 1.00),
    ("class_a_only", 1.0), ("class_b_only", 1.0), ("random_matched", 1.0),
]:
    r = perturb(SENTENCE, mode, rate, seed=42)
    label = f"{mode}-{int(rate * 100)}" if mode == "drop" else mode
    print(f"\n{label:<16} a={r['n_a']}  b={r['n_b']}  chars={r['n_chars']}")
    print(f"{'':<16} {r['text']}")
