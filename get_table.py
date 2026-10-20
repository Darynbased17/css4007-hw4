import json

print("| Question | S1 | S2 | S3 |")
print("|---|:---:|:---:|:---:|")
for i in range(1, 21):
    q_id = f"Q-{i:02d}"
    try:
        with open(f"outputs/{q_id}_log.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            s1 = "+" if data["S1"]["correct"] else "-"
            s2 = "+" if data["S2"]["correct"] else "-"
            s3 = "+" if data["S3"]["correct"] else "-"
            print(f"| {q_id} | {s1} | {s2} | {s3} |")
    except FileNotFoundError:
        pass
