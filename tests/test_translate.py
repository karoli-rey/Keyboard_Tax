import pandas as pd
import pytest

import keyboard_tax.translate as translate_module
from keyboard_tax.common import check_columns, read_table
from keyboard_tax.translate import (
    cache_file,
    clean_llm_output,
    first_sentences,
    get_translator,
    postprocess,
    read_cache,
    summarize,
    translate_all,
)

LLM_PROMPT = "Translate into English.\nPortuguese: {text}\nEnglish:"


def make_config(**changes) -> dict:
    config = {
        "source_language": "por_Latn",
        "target_language": "eng_Latn",
        "systems": {"nllb": "fake/nllb", "opus_mt": "fake/opus", "llm": "TODO"},
        "llm_prompt": "TODO",
        "translation": {"batch_size": 2, "num_beams": 4, "max_new_tokens": 256},
    }
    config.update(changes)
    return config


class FakeTranslator:
    """Stands in for a real model: "translates" by writing the sentence in capitals."""

    def __init__(self, name: str, fail_on_call: int | None = None) -> None:
        self.name = name
        self.batches: list[list[str]] = []
        self.fail_on_call = fail_on_call

    def translate(self, texts: list[str]) -> list[str]:
        if self.fail_on_call == len(self.batches) + 1:
            raise RuntimeError("the GPU session ended")
        self.batches.append(list(texts))
        return [f" {text.upper()} " for text in texts]

    @property
    def seen(self) -> list[str]:
        return [text for batch in self.batches for text in batch]


def fakes(*names: str) -> dict[str, FakeTranslator]:
    return {name: FakeTranslator(name) for name in names}


def test_table_has_one_row_per_version_and_system_with_the_agreed_columns(tmp_path):
    versions = read_table("versions", fixtures=True)
    translators = fakes("nllb", "opus_mt")
    table = translate_all(versions, make_config(), translators=translators, cache_dir=tmp_path)

    check_columns(table, "translations")
    assert len(table) == 2 * len(versions)
    assert list(table["system"].unique()) == ["nllb", "opus_mt"]
    assert (table["hyp"] == table["src"].str.upper()).all()  # trimmed, in the right rows


def test_each_distinct_sentence_is_translated_once(tmp_path):
    versions = read_table("versions", fixtures=True)
    doubled = pd.concat([versions, versions], ignore_index=True)
    translators = fakes("nllb", "opus_mt")
    translate_all(doubled, make_config(), translators=translators, cache_dir=tmp_path)

    seen = translators["nllb"].seen
    assert len(seen) == len(set(seen)) == versions["src"].nunique()
    assert all(len(batch) <= 2 for batch in translators["nllb"].batches)


def test_second_run_reads_the_cache_and_calls_no_model(tmp_path):
    versions = read_table("versions", fixtures=True)
    config = make_config()
    first = translate_all(versions, config, translators=fakes("nllb", "opus_mt"),
                          cache_dir=tmp_path)
    again = fakes("nllb", "opus_mt")
    second = translate_all(versions, config, translators=again, cache_dir=tmp_path)

    assert again["nllb"].batches == [] and again["opus_mt"].batches == []
    pd.testing.assert_frame_equal(first, second)


def test_after_a_crash_only_unfinished_batches_run_again(tmp_path):
    versions = read_table("versions", fixtures=True)
    config = make_config(systems={"nllb": "fake/nllb"})
    crashing = FakeTranslator("nllb", fail_on_call=3)
    with pytest.raises(RuntimeError, match="session ended"):
        translate_all(versions, config, translators={"nllb": crashing}, cache_dir=tmp_path)
    saved = set(read_cache(cache_file("nllb", config, tmp_path)))
    assert saved == set(crashing.seen) and len(saved) == 4  # two batches of two survived

    restart = FakeTranslator("nllb")
    table = translate_all(versions, config, translators={"nllb": restart}, cache_dir=tmp_path)
    assert set(restart.seen).isdisjoint(saved)
    assert set(restart.seen) | saved == set(versions["src"])
    assert table["hyp"].notna().all()


def test_a_changed_setting_gets_a_new_cache_file(tmp_path):
    config = make_config(systems={"nllb": "fake/nllb", "llm": "fake/llm"}, llm_prompt=LLM_PROMPT)
    other_beam = make_config(
        systems=config["systems"],
        llm_prompt=LLM_PROMPT,
        translation={"batch_size": 2, "num_beams": 1, "max_new_tokens": 256},
    )
    other_prompt = make_config(systems=config["systems"], llm_prompt=LLM_PROMPT + " Be brief.")
    other_batch = make_config(
        systems=config["systems"],
        llm_prompt=LLM_PROMPT,
        translation={"batch_size": 8, "num_beams": 4, "max_new_tokens": 256},
    )

    assert cache_file("nllb", config, tmp_path) != cache_file("nllb", other_beam, tmp_path)
    assert cache_file("llm", config, tmp_path) != cache_file("llm", other_prompt, tmp_path)
    assert cache_file("llm", config, tmp_path) == cache_file("llm", other_beam, tmp_path)
    # The batch size only changes the speed, so it keeps the cache.
    assert cache_file("nllb", config, tmp_path) == cache_file("nllb", other_batch, tmp_path)


def test_a_system_that_does_not_run_joins_the_table_only_when_its_cache_is_complete(tmp_path):
    versions = read_table("versions", fixtures=True)
    config = make_config()
    only_opus = translate_all(versions, config, systems=["opus_mt"],
                              translators=fakes("opus_mt"), cache_dir=tmp_path)
    assert list(only_opus["system"].unique()) == ["opus_mt"]

    both = translate_all(versions, config, systems=["nllb"], translators=fakes("nllb"),
                         cache_dir=tmp_path)
    assert list(both["system"].unique()) == ["nllb", "opus_mt"]


def test_undecided_llm_is_skipped_but_asking_for_it_is_an_error(tmp_path, capsys):
    versions = read_table("versions", fixtures=True)
    translate_all(versions, make_config(), translators=fakes("nllb", "opus_mt"),
                  cache_dir=tmp_path)
    assert "llm: skipped" in capsys.readouterr().out

    with pytest.raises(ValueError, match="still TODO"):
        translate_all(versions, make_config(), systems=["llm"], cache_dir=tmp_path)
    with pytest.raises(ValueError, match="must contain"):
        get_translator("llm", make_config(systems={"llm": "fake/llm"}, llm_prompt="Translate."))
    with pytest.raises(ValueError, match="Unknown system"):
        get_translator("deepl", make_config())


def test_llm_answers_are_cleaned_and_the_raw_answer_stays_in_the_cache(tmp_path):
    class ChattyLlm:
        name = "llm"

        def translate(self, texts: list[str]) -> list[str]:
            label, note = "Here is the translation:", "Note: literal."
            return [f"{label}\n\n{text.upper()}\n\n{note}" for text in texts]

    versions = read_table("versions", fixtures=True)
    config = make_config(systems={"llm": "fake/llm"}, llm_prompt=LLM_PROMPT)
    table = translate_all(versions, config, translators={"llm": ChattyLlm()}, cache_dir=tmp_path)

    assert (table["hyp"] == table["src"].str.upper()).all()
    saved = pd.read_csv(cache_file("llm", config, tmp_path))
    assert list(saved.columns) == ["src", "raw", "hyp"]
    assert saved["raw"].str.startswith("Here is the translation:").all()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("He could not come.", "He could not come."),
        ("  He could not come.\n", "He could not come."),
        ("Here is the translation:\nHe could not come.", "He could not come."),
        ("Here's the English translation: He could not come.", "He could not come."),
        ("Sure, here is the translation:\n\nHe could not come.", "He could not come."),
        ("**Translation:** He could not come.", "He could not come."),
        ("English: He could not come.", "He could not come."),
        ("He could not come.\n\nNote: 'pôde' is the past tense.", "He could not come."),
        ('"He could not come."', "He could not come."),
        ("“He could not come.”", "He could not come."),
        ('"Stop," he said, "now."', '"Stop," he said, "now."'),
        ("He said: here is the plan.", "He said: here is the plan."),
        ("", ""),
    ],
)
def test_clean_llm_output(raw, expected):
    assert clean_llm_output(raw) == expected


def test_clean_llm_output_keeps_quotes_when_the_portuguese_sentence_is_quoted():
    assert clean_llm_output('"He could not come."', source='"Ele não pôde vir."') == (
        '"He could not come."'
    )


def test_only_llm_answers_are_cleaned():
    assert postprocess("llm", "English: Hello.", "Olá.") == "Hello."
    assert postprocess("nllb", " English: Hello. ", "Olá.") == "English: Hello."


def test_first_sentences_keeps_every_version_of_the_first_sentences():
    versions = read_table("versions", fixtures=True)
    first = first_sentences(versions, 1)
    assert set(first["sent_id"]) == {0}
    assert len(first) == (versions["sent_id"] == 0).sum()


def test_summarize_counts_empty_translations():
    table = pd.DataFrame(
        {"system": ["nllb", "nllb", "llm"], "hyp": ["Hello.", None, " "]}
    )
    assert summarize(table).splitlines() == [
        "  nllb     2 translations, 1 empty",
        "  llm      1 translations, 1 empty",
    ]


def test_try_outs_use_their_own_cache_and_never_touch_the_real_one(tmp_path, monkeypatch):
    written = {}
    monkeypatch.setattr(translate_module, "CACHE_DIR", tmp_path / "real")
    monkeypatch.setattr(translate_module, "TRYOUT_CACHE_DIR", tmp_path / "tryout")
    monkeypatch.setattr(translate_module, "load_config", make_config)
    monkeypatch.setattr(
        translate_module, "get_translator", lambda system, _: FakeTranslator(system)
    )
    monkeypatch.setattr(
        translate_module, "write_table", lambda table, name: written.update({name: table})
    )

    translate_module.main(["--fixtures", "--limit", "1"])

    assert set(written["translations"]["sent_id"]) == {0}
    assert sorted(path.name[:4] for path in (tmp_path / "tryout").iterdir()) == ["nllb", "opus"]
    assert not (tmp_path / "real").exists()
