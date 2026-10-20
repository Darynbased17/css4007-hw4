import json
import os
import re
import time
from collections import Counter
from strategies import run_s1_direct, run_s2_think_and_vote, run_s3_tools

# Настройки для проверки
TEST_MODE = False # ПОСТАВЬ В False, КОГДА БУДЕШЬ ГОТОВ ПРОГНАТЬ ВСЕ 20!

# Цены для gpt-4o-mini (если преподаватель не дал конкретные тарифы для "gpt-5.6-luna",
# используем стандартные цены как прокси для расчета: $0.15/1M input, $0.60/1M output)
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60

def extract_answer(text):
    """Вытаскивает имя и число из строки 'ANSWER: name | 12.3'"""
    # Ищем с конца, так как модель может много рассуждать до этого
    match = re.search(r"ANSWER:\s*(.+?)\s*\|\s*([-\d.]+)", text)
    if match:
        name = match.group(1).strip()
        try:
            num = float(match.group(2))
            return name, num
        except ValueError:
            return name, None
    return None, None

def is_correct(pred_name, pred_num, true_name, true_num, decimals):
    """Строгое правило проверки ответа из задания B4"""
    if pred_name is None or pred_num is None:
        return False
    
    # Имя должно совпадать
    if pred_name.lower() != true_name.lower():
        return False
        
    # Число должно совпадать с учетом округления и допустимой разницы в 1 единицу последнего разряда
    pred_rounded = round(pred_num, decimals)
    true_rounded = round(true_num, decimals)
    
    diff = abs(pred_rounded - true_rounded)
    allowed_diff = (10 ** -decimals) + 1e-9 # +1e-9 для защиты от погрешности float
    
    return diff <= allowed_diff

def main():
    os.makedirs("outputs", exist_ok=True)
    
    with open("data/questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    if TEST_MODE:
        questions = questions[:2] # Берем только 2 вопроса для теста
        print("ВНИМАНИЕ: Включен TEST_MODE. Обрабатываются только 2 вопроса.")

    results_summary = {"S1": [], "S2": [], "S3": []}
    
    for q in questions:
        q_id = q["id"]
        true_name = q["answer"]
        true_val = q["value"]
        decimals = q["decimals"]
        
        print(f"--- Running {q_id} ---")
        
        # Запускаем S1
        print(" S1...", end="", flush=True)
        res_s1 = run_s1_direct(q["question"])
        p_name, p_num = extract_answer(res_s1["answer"])
        res_s1["correct"] = is_correct(p_name, p_num, true_name, true_val, decimals)
        print(" Done!")

        # Запускаем S2
        print(" S2...", end="", flush=True)
        res_s2 = run_s2_think_and_vote(q["question"], k=5)
        
        # Голосование для S2 (самый частый ответ)
        extracted_answers = [extract_answer(ans) for ans in res_s2["answers"]]
        valid_answers = [ans for ans in extracted_answers if ans[0] is not None]
        
        if valid_answers:
            most_common = Counter(valid_answers).most_common(1)[0][0]
            p_name2, p_num2 = most_common
            res_s2["answer"] = f"ANSWER: {p_name2} | {p_num2}"
        else:
            p_name2, p_num2 = None, None
            res_s2["answer"] = "UNANSWERED"
            
        res_s2["correct"] = is_correct(p_name2, p_num2, true_name, true_val, decimals)
        print(" Done!")

        # Запускаем S3
        print(" S3...", end="", flush=True)
        res_s3 = run_s3_tools(q["question"], max_rounds=10)
        p_name3, p_num3 = extract_answer(res_s3["answer"])
        
        if "hit round limit" in res_s3["answer"]:
            res_s3["correct"] = False
        else:
            res_s3["correct"] = is_correct(p_name3, p_num3, true_name, true_val, decimals)
        print(" Done!")

        # Сохраняем логи для вопроса
        log_data = {
            "question": q,
            "S1": res_s1,
            "S2": res_s2,
            "S3": res_s3
        }
        with open(f"outputs/{q_id}_log.json", "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
            
        results_summary["S1"].append(res_s1)
        results_summary["S2"].append(res_s2)
        results_summary["S3"].append(res_s3)

    # Печатаем итоги
    print("\n=== SUMMARY ===")
    for strat in ["S1", "S2", "S3"]:
        runs = results_summary[strat]
        correct = sum(1 for r in runs if r["correct"])
        unanswered = sum(1 for r in runs if r["answer"] == "UNANSWERED" or "hit round limit" in r["answer"])
        total_in = sum(r["input_tokens"] for r in runs)
        total_out = sum(r["output_tokens"] for r in runs)
        total_time = sum(r["time"] for r in runs)
        
        times = sorted(r["time"] for r in runs)
        median_time = times[len(times)//2] if times else 0
        
        cost = (total_in / 1_000_000 * COST_PER_1M_INPUT) + (total_out / 1_000_000 * COST_PER_1M_OUTPUT)
        
        print(f"{strat}: Correct: {correct}/{len(runs)} | Unanswered: {unanswered} | In: {total_in} | Out: {total_out} | Median Time: {median_time:.1f}s | Total Time: {total_time:.1f}s | Cost: ${cost:.6f}")

if __name__ == "__main__":
    main()