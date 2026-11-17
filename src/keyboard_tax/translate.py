"""Step 4: translate every version with the three systems.

Owner:  Coder 2
Input:  outputs/3_versions.csv
Output: outputs/4_translations.csv  (columns: sent_id, version, system, src, hyp)
        outputs/4_cache/            finished translations, one file per system

How it works:
    1. Each distinct sentence is translated once per system (many versions share a text).
    2. Sentences go to the model in fixed batches. Every finished batch is saved in
       outputs/4_cache/, so a crash loses nothing: run the step again and it continues.
    3. The name of a cache file contains a short code of the settings (model, prompt,
       beam size). Changed settings therefore never reuse old translations. Try-outs
       (--fixtures, --limit) use their own cache, so they never change the full run.
    4. NLLB and Opus-MT use beam search. The LLM gets the fixed prompt from config.yaml
       with randomness switched off, and clean_llm_output() removes extra text such as
       "Here is the translation:". The raw answer stays in the cache file.

Try it:    python -m keyboard_tax.translate --fixtures --systems opus_mt
Full run:  python -m keyboard_tax.translate      (on a GPU: scripts/colab_gpu_run.ipynb)
"""

import argparse
import gc
import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

import pandas as pd

from keyboard_tax.common import ROOT, TABLES, load_config, read_table, write_table

CACHE_DIR = ROOT / "outputs" / "4_cache"
TRYOUT_CACHE_DIR = CACHE_DIR / "tryout"  # --fixtures and --limit never touch the real cache
CACHE_COLUMNS = ["src", "raw", "hyp"]
DEFAULT_SETTINGS = {"batch_size": 16, "num_beams": 4, "max_new_tokens": 256}


# ---------------------------------------------------------------- translators

class Translator(Protocol):
    """Every translation system has a name and a translate() method."""

    name: str

    def translate(self, texts: list[str]) -> list[str]:
        """Translate Portuguese sentences into English, in the same order."""
        ...


class Seq2SeqTranslator:
    """NLLB-200 or Opus-MT: a translation model from Hugging Face, with beam search."""

    def __init__(
        self,
        name: str,
        model_name: str,
        settings: dict,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.name = name
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # NLLB covers 200 languages and must be told which two we use; Opus-MT must not.
        language = {"src_lang": source_language} if source_language else {}
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **language)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device).eval()
        self.options = {
            "num_beams": settings["num_beams"],
            "max_new_tokens": settings["max_new_tokens"],
        }
        if target_language:
            self.options["forced_bos_token_id"] = self.tokenizer.convert_tokens_to_ids(
                target_language
            )

    def translate(self, texts: list[str]) -> list[str]:
        batch = self.tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True, max_length=512
        ).to(self.device)
        with self.torch.inference_mode():
            output = self.model.generate(**batch, **self.options)
        return self.tokenizer.batch_decode(output, skip_special_tokens=True)


class LlmTranslator:
    """A chat LLM from Hugging Face, asked with the fixed prompt, randomness switched off."""

    name = "llm"

    def __init__(self, model_name: str, prompt: str, settings: dict, four_bit: bool) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if not torch.cuda.is_available():
            raise RuntimeError(
                "The LLM needs a GPU. Run this system on Colab: scripts/colab_gpu_run.ipynb"
            )
        self.torch = torch
        self.prompt = prompt
        self.max_new_tokens = settings["max_new_tokens"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.padding_side = "left"  # the answer must follow the prompt directly
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        options = {"device_map": "auto", "torch_dtype": torch.float16}
        if four_bit:  # smaller numbers inside the model, so 7B parameters fit a free GPU
            from transformers import BitsAndBytesConfig

            options["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16
            )
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **options).eval()

    def translate(self, texts: list[str]) -> list[str]:
        chats = [
            self.tokenizer.apply_chat_template(
                [{"role": "user", "content": self.prompt.format(text=text)}],
                tokenize=False,
                add_generation_prompt=True,
            )
            for text in texts
        ]
        batch = self.tokenizer(
            chats, return_tensors="pt", padding=True, add_special_tokens=False
        ).to(self.model.device)
        with self.torch.inference_mode():
            output = self.model.generate(
                **batch,
                do_sample=False,  # always the most likely next word: no randomness
                temperature=None,
                top_p=None,
                top_k=None,
                max_new_tokens=self.max_new_tokens,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        answers = output[:, batch["input_ids"].shape[1] :]  # drop the prompt
        return self.tokenizer.batch_decode(answers, skip_special_tokens=True)


def decoding_settings(config: dict) -> dict:
    """The `translation` block of config.yaml, with defaults for missing values."""
    return {**DEFAULT_SETTINGS, **(config.get("translation") or {})}


def undecided(system: str, config: dict) -> str | None:
    """Why `system` cannot run yet (a setting is still TODO), or None if it can."""
    if str(config["systems"][system]).strip().upper() == "TODO":
        return f"systems.{system} in config.yaml is still TODO"
    if system == "llm":
        prompt = str(config.get("llm_prompt") or "TODO")
        if prompt.strip().upper() == "TODO":
            return "llm_prompt in config.yaml is still TODO"
        if "{text}" not in prompt:
            return "llm_prompt in config.yaml must contain {text}, the place for the sentence"
    return None


def check_can_run(system: str, config: dict) -> None:
    """Raise a clear error if `system` is unknown or one of its settings is still TODO."""
    if system not in config["systems"]:
        raise ValueError(f"Unknown system '{system}'. Known: {', '.join(config['systems'])}.")
    reason = undecided(system, config)
    if reason:
        raise ValueError(f"Cannot run '{system}': {reason}. Set it in config.yaml.")


def get_translator(system: str, config: dict) -> Translator:
    """Return the translator for "nllb", "opus_mt" or "llm" (this loads the model)."""
    check_can_run(system, config)
    model_name = config["systems"][system]
    settings = decoding_settings(config)
    if system == "nllb":
        return Seq2SeqTranslator(
            system, model_name, settings, config["source_language"], config["target_language"]
        )
    if system == "llm":
        return LlmTranslator(
            model_name, config["llm_prompt"].strip(), settings, bool(config.get("llm_4bit"))
        )
    return Seq2SeqTranslator(system, model_name, settings)


# ---------------------------------------------------------------- LLM answers

LABEL_RE = re.compile(
    r"""^\**(?:
        (?:sure|certainly|of\ course)[^:\n]*:      # Sure, here it is:
      | here(?:\ is|'s)[^:\n]*:                    # Here is the translation:
      | (?:the\ )?(?:english\ )?translation\**:    # Translation:
      | english\**:                                # English:
    )\**\s*""",
    re.IGNORECASE | re.VERBOSE,
)
QUOTE_PAIRS = {'"': '"', "“": "”", "'": "'", "‘": "’", "«": "»"}


def clean_llm_output(raw: str, source: str = "") -> str:
    """Keep only the translation from an LLM answer.

    Removes a label in front ("Here is the translation:"), notes after a blank line, and
    quotation marks around the whole answer unless the Portuguese sentence starts with one.
    """
    text = LABEL_RE.sub("", raw.strip()).strip()
    text = text.split("\n\n")[0]
    text = " ".join(line.strip() for line in text.splitlines() if line.strip())
    closing = QUOTE_PAIRS.get(text[:1])
    source_is_quoted = source.strip()[:1] in QUOTE_PAIRS
    if closing and len(text) > 1 and text.endswith(closing) and not source_is_quoted:
        inner = text[1:-1]
        if text[0] not in inner and closing not in inner:
            text = inner.strip()
    return text


def postprocess(system: str, raw: str, source: str) -> str:
    """The translation we keep: LLM answers are cleaned, model output only trimmed."""
    return clean_llm_output(raw, source) if system == "llm" else raw.strip()


# ---------------------------------------------------------------- cache

def cache_file(system: str, config: dict, cache_dir: Path = CACHE_DIR) -> Path:
    """The cache file of one system; its name changes with every setting that matters."""
    settings = decoding_settings(config)
    key = {
        "model": config["systems"][system],
        "source": config["source_language"],
        "target": config["target_language"],
        "max_new_tokens": settings["max_new_tokens"],
    }
    if system == "llm":
        key["prompt"] = str(config.get("llm_prompt")).strip()
        key["four_bit"] = bool(config.get("llm_4bit"))
    else:
        key["num_beams"] = settings["num_beams"]
    code = hashlib.sha1(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return cache_dir / f"{system}-{code}.csv"


def read_cache(path: Path) -> dict[str, str]:
    """Finished translations as {Portuguese sentence: English translation}."""
    if not path.exists():
        return {}
    rows = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = rows.dropna(subset=["hyp"])  # a row cut off by a crash is translated again
    return dict(zip(rows["src"], rows["hyp"], strict=True))


def translate_sources(
    translator: Translator, system: str, sources: list[str], path: Path, batch_size: int
) -> dict[str, str]:
    """Translate each distinct sentence once, saving every batch; return the full cache.

    The batches are always the same (sentences sorted by length, then cut into groups),
    whether this is the first run or a restart, so a restart gives the same translations.
    """
    cache = read_cache(path)
    ordered = sorted(set(sources), key=lambda text: (len(text), text))
    batches = [ordered[i : i + batch_size] for i in range(0, len(ordered), batch_size)]
    todo = [batch for batch in batches if any(text not in cache for text in batch)]
    path.parent.mkdir(parents=True, exist_ok=True)
    for number, batch in enumerate(todo, start=1):
        raw = translator.translate(batch)
        if len(raw) != len(batch):
            raise RuntimeError(f"{system} returned {len(raw)} texts for {len(batch)} sentences")
        rows = pd.DataFrame({"src": batch, "raw": raw}, columns=CACHE_COLUMNS)
        rows["hyp"] = [postprocess(system, answer, text) for answer, text in zip(raw, batch)]
        rows = rows[~rows["src"].isin(cache)]
        rows.to_csv(path, mode="a", header=not path.exists(), index=False)
        cache.update(zip(rows["src"], rows["hyp"], strict=True))
        if number % 10 == 0 or number == len(todo):
            print(f"  {system}: batch {number} of {len(todo)} done", flush=True)
    return cache


def free_memory() -> None:
    """Give the GPU memory of a finished model back before the next one loads."""
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ---------------------------------------------------------------- the step

def translate_all(
    versions: pd.DataFrame,
    config: dict,
    systems: list[str] | None = None,
    translators: dict[str, Translator] | None = None,
    cache_dir: Path = CACHE_DIR,
) -> pd.DataFrame:
    """Translate every row with every system (columns in common.TABLES["translations"]).

    systems:     the systems whose model may run now (default: all in config.yaml).
                 A system that does not run still joins the table if its cache is complete.
    translators: ready-made translators by system name; the tests pass fake ones.
    """
    for system in systems or []:
        check_can_run(system, config)
    settings = decoding_settings(config)
    sources = versions["src"].astype(str).tolist()
    run_now = list(config["systems"]) if systems is None else systems
    tables = []
    for system in config["systems"]:
        reason = undecided(system, config)
        if reason:
            print(f"{system}: skipped, {reason}")
            continue
        path = cache_file(system, config, cache_dir)
        cache = read_cache(path)
        missing = set(sources) - set(cache)
        if missing and system in run_now:
            print(f"{system}: translating {len(missing)} sentences ({config['systems'][system]})")
            translator = (translators or {}).get(system) or get_translator(system, config)
            cache = translate_sources(translator, system, sources, path, settings["batch_size"])
            del translator
            free_memory()
        elif missing:
            print(f"{system}: {len(missing)} sentences not translated yet, left out of the table")
            continue
        table = versions[["sent_id", "version", "src"]].copy()
        table["system"] = system
        table["hyp"] = table["src"].astype(str).map(cache)
        tables.append(table)
    if not tables:
        raise ValueError("No system has translations yet. Run at least one system.")
    return pd.concat(tables, ignore_index=True)[TABLES["translations"][1]]


def first_sentences(versions: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Only the versions of the first `limit` sentences, for a quick try."""
    keep = sorted(versions["sent_id"].unique())[:limit]
    return versions[versions["sent_id"].isin(keep)].reset_index(drop=True)


def summarize(translations: pd.DataFrame) -> str:
    """Rows and empty translations per system, to print after the run."""
    lines = []
    for system, rows in translations.groupby("system", sort=False):
        empty = int((rows["hyp"].fillna("").str.strip() == "").sum())
        lines.append(f"  {system:<8} {len(rows)} translations, {empty} empty")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 4: translate")
    parser.add_argument("--fixtures", action="store_true", help="use tests/fixtures as input")
    parser.add_argument(
        "--systems",
        nargs="+",
        metavar="NAME",
        help="run only these systems now, e.g. --systems nllb opus_mt (default: all)",
    )
    parser.add_argument(
        "--limit", type=int, metavar="N", help="only the first N sentences, for a quick try"
    )
    args = parser.parse_args(argv)
    config = load_config()
    versions = read_table("versions", fixtures=args.fixtures)
    if args.limit:
        versions = first_sentences(versions, args.limit)
    tryout = args.fixtures or bool(args.limit)
    translations = translate_all(
        versions,
        config,
        systems=args.systems,
        cache_dir=TRYOUT_CACHE_DIR if tryout else CACHE_DIR,
    )
    print("Wrote", write_table(translations, "translations"))
    print(summarize(translations))
    if tryout:
        print("This was a try-out on a few sentences. Run without --fixtures and --limit "
              "for the full table.")


if __name__ == "__main__":
    main()
