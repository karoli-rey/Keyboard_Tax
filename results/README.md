# results/

The numbers that `results.ipynb` reads. Written by `python -m keyboard_tax.analyze --save-results`.
No sentences are stored here: FLORES+ asks that its text stays behind its login.

| File | Content |
|---|---|
| `scores.csv` | chrF and COMET for each of the 9,870 translations (`sent_id`, `version`, `system`) |
| `corpus_scores.csv` | BLEU, chrF and mean COMET per version and system |
| `version_counts.csv` | per sentence and version: Class A words, Class B words and letters changed |
| `targeted_check.csv` | challenge set: right / wrong / unclear per item, version and system |
| `targeted_summary.csv`, `targeted_by_loss.csv` | the check summed up, overall and by what the word loses |
| `bleu_vs_targeted.csv` | BLEU against the targeted check on the challenge sentences (H5) |
| `contrasts_without_e.csv`, `contrasts_without_other_script.csv` | the robustness reruns |
