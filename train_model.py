"""Trains the token-labelling extractor on data/synthetic_train.json and saves models/extractor.joblib.

Usage:  python train_model.py
"""
import json
import time
from collections import Counter
from pathlib import Path

from navigator import extract_ml

ROOT = Path(__file__).resolve().parent


def main():
    train = json.loads((ROOT / "data" / "synthetic_train.json").read_text())
    test = json.loads((ROOT / "data" / "synthetic_test.json").read_text())
    t0 = time.time()
    model = extract_ml.train(train)
    extract_ml.save(model)
    print(f"trained on {len(train)} reports in {time.time() - t0:.0f}s -> {extract_ml.MODEL_PATH.relative_to(ROOT)}")

    # token-level check on the held-out synthetic reports (labels other than O)
    hit, tot = Counter(), Counter()
    for r in test:
        gold = extract_ml.token_labels(r["text"], r["spans"])
        _, feats = extract_ml.featurize(r["text"])
        pred = model["clf"].predict(model["vec"].transform(feats))
        for g, p in zip(gold, pred):
            if g != "O":
                tot[g] += 1
                hit[g] += g == p
    print(f"token label accuracy on test (non-O): {sum(hit.values()) / sum(tot.values()):.3f}")
    worst = sorted(tot, key=lambda k: hit[k] / tot[k])[:8]
    print("weakest labels:", ", ".join(f"{k} {hit[k] / tot[k]:.2f}" for k in worst))


if __name__ == "__main__":
    main()
