import pandas as pd

from keyboard_tax.challenge import draft_challenge_set, review_sheet
from keyboard_tax.common import read_table

POWER = pd.DataFrame(
    [["força", "noun: force", "force|strength", "gallows"]],
    columns=["word", "correct_reading", "correct_pattern", "wrong_pattern"],
)


def versions_for(sent_id: int, clean: str, damaged: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sent_id": [sent_id, sent_id],
            "version": ["clean", "b_only"],
            "src": [clean, damaged],
            "n_a": [0, 0],
            "n_b": [0, 1],
            "n_chars": [0, 1],
        }
    )


def test_draft_from_fixtures_matches_the_example_challenge_set():
    draft = draft_challenge_set(
        read_table("challenge_words", fixtures=True),
        read_table("sentences", fixtures=True),
        read_table("versions", fixtures=True),
    )
    expected = read_table("challenge_set", fixtures=True)
    pd.testing.assert_frame_equal(draft, expected)


def test_keeps_a_sentence_where_the_reference_has_the_right_reading():
    sentences = pd.DataFrame(
        {"sent_id": [7], "pt": ["A força é grande."], "en": ["The force is great."]}
    )
    versions = versions_for(7, "A força é grande.", "A forca e grande.")
    assert draft_challenge_set(POWER, sentences, versions)["sent_id"].tolist() == [7]


def test_drops_a_sentence_whose_reference_cannot_tell_the_readings_apart():
    sentences = pd.DataFrame({"sent_id": [7], "pt": ["A força é grande."], "en": ["It is big."]})
    versions = versions_for(7, "A força é grande.", "A forca e grande.")
    assert draft_challenge_set(POWER, sentences, versions).empty


def test_drops_a_sentence_where_no_version_lost_the_accent():
    sentences = pd.DataFrame({"sent_id": [7], "pt": ["A força é grande."], "en": ["The force."]})
    versions = versions_for(7, "A força é grande.", "A força e grande.")
    assert draft_challenge_set(POWER, sentences, versions).empty


def test_review_sheet_adds_both_sentences():
    challenge = read_table("challenge_set", fixtures=True)
    sheet = review_sheet(challenge, read_table("sentences", fixtures=True))
    assert sheet.loc[0, "en"] == "His grandfather could not come to the party."
    assert "pt" in sheet.columns
