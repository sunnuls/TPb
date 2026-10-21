# Offline dataset audit

This experimental tool inspects YOLO-format annotations **without training or running any live poker automation**.

## Run

Install PyYAML if needed: `pip install pyyaml`.

```bash
python tools/audit_dataset.py dataset/detect/poker_detect.yaml
```

It reports: images by split; annotation totals per class; invalid class IDs and out-of-bounds boxes; missing labels; empty classes; exact duplicate images crossing train/validation/test splits.

Exit status 0 means no *detected* issues, not that labels are semantically correct or that the model will perform well. Exit status 1 means warnings requiring inspection.

## Manual follow-up

1. Export the actual YOLO dataset and run the audit locally (datasets are not committed here).
2. Manually review random labeled examples and examples from rare classes. This audit cannot detect a wrong-but-valid class name or a poorly drawn yet in-bounds box.
3. Keep truly held-out screenshots from separate capture sessions for evaluation; near-duplicates may still cross splits.
4. Evaluate any existing weights on those held-out images, recording class-specific precision, recall, mAP, and visual error examples.
5. Provide anonymized `results.csv`, `results.png`, `confusion_matrix.png`, and a few prediction screenshots for further analysis.

This branch intentionally does not change live inference, coordinated bot actions, or operational automation.
