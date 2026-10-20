r"""Re-score saved logs in outputs/ WITHOUT calling the API.

Original rule (run.py): regex ANSWER:\s*(.+?)\s*\|\s*([-\d.]+) -> "14,069" is read as 14.
Tolerant rule (this file): same rule, but thousands separators (14,069) are removed
before the regex runs. Nothing else changes: name must match, number within 1 unit
of the last required digit.
"""

import glob
import json
import re
from collections import Counter

THOUSANDS = re.compile(r"(?<=\d),(?=\d{3})")
PATTERN = re.compile(r"ANSWER:\s*(.+?)\s*\|\s*([-\d.]+)")


def extract(text, tolerant):
    if tolerant:
        text = THOUSANDS.sub("", text)
    m = PATTERN.search(text)
    if not m:
        return None, None
    try:
        return m.group(1).strip(), float(m.group(2))
    except ValueError:
        return m.group(1).strip(), None


def is_correct(name, num, q):
    if name is None or num is None:
        return False
    if name.lower() != q["answer"].lower():
        return False
    d = q["decimals"]
    return abs(round(num, d) - round(q["value"], d)) <= 10**-d + 1e-9


def score(result, strategy, q, tolerant):
    if strategy == "S3" and "hit round limit" in result["answer"]:
        return False
    if strategy == "S2":
        answers = [extract(a, tolerant) for a in result["answers"]]
        answers = [a for a in answers if a[0] is not None]
        if not answers:
            return False
        name, num = Counter(answers).most_common(1)[0][0]
    else:
        name, num = extract(result["answer"], tolerant)
    return is_correct(name, num, q)


def main():
    totals = {s: {"original": 0, "tolerant": 0} for s in ("S1", "S2", "S3")}
    print("| Question | S1 | S2 | S3 |  (✓ ok, ✗ wrong, ✓* ok only after comma fix)")
    for path in sorted(glob.glob("outputs/Q-*_log.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        q, cells = data["question"], []
        for s in ("S1", "S2", "S3"):
            orig = score(data[s], s, q, tolerant=False)
            tol = score(data[s], s, q, tolerant=True)
            totals[s]["original"] += orig
            totals[s]["tolerant"] += tol
            cells.append("✓" if orig else ("✓*" if tol else "✗"))
        print(f"| {q['id']} | " + " | ".join(cells) + " |")
    print()
    for s, t in totals.items():
        print(
            f"{s}: original rule {t['original']}/20, comma-tolerant {t['tolerant']}/20"
        )


if __name__ == "__main__":
    main()
