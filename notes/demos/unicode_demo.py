"""Demo: how Unicode already knows how to take accents off a letter.

By Thomas (exploration, not pipeline code). Comments translated from German.
"""

import unicodedata as ud

print("=" * 72)
print("1. What is 'ê' really?")
print("=" * 72)
c = "ê"
print(f"  Character         : {c}")
print(f"  One code point    : U+{ord(c):04X}   ({ud.name(c)})")
print(f"  Unicode says      : {ud.decomposition(c)}   <- the table we were looking for")
print()
nfd = ud.normalize("NFD", c)
print(f"  After NFD         : {len(nfd)} code points")
for ch in nfd:
    print(f"      U+{ord(ch):04X}  {ud.name(ch)}")

print()
print("=" * 72)
print("2. 'têm' character by character")
print("=" * 72)
w = "têm"
print(f"  before : {w!r}  ->  " + " ".join(f"U+{ord(x):04X}" for x in w))
d = ud.normalize("NFD", w)
print(f"  NFD    : {d!r}  ->  " + " ".join(f"U+{ord(x):04X}" for x in d))
keep = "".join(x for x in d if not ud.combining(x))
print(f"  filter : {keep!r}  ->  " + " ".join(f"U+{ord(x):04X}" for x in keep))
print(f"  NFC    : {ud.normalize('NFC', keep)!r}")

print()
print("=" * 72)
print("3. How many such mappings does Unicode already contain?")
print("=" * 72)
n = sum(
    1
    for cp in range(0x2000)
    if ud.decomposition(chr(cp)).startswith(tuple("0123456789ABCDEF"))
)
print(f"  In the first 8192 code points alone: {n} characters with a stored decomposition")
