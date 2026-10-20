import json
import time
import os
from openai import OpenAI
from tools import calculate, lookup, CORPUS
from dotenv import load_dotenv

load_dotenv()

# Возвращаем адрес OpenRouter! Без него ключ sk-or... не сработает.
client = OpenAI(
    base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENAI_API_KEY")
)

# Ставим модель строго по заданию
MODEL = "gpt-5.6-luna"

# Готовим текст всех документов для S1 и S2
ALL_DOCS_TEXT = "\n".join([f"[{d['id']}] {d['title']}: {d['text']}" for d in CORPUS])

# Строгий формат ответа, который требует преподаватель
SYSTEM_PROMPT = "You are a helpful assistant. Always end your final response with this exact format on a new line: ANSWER: <name or yes/no> | <number>"

# JSON-схемы наших инструментов из Части А
TOOLS_DEF = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Searches the database for district facts (population, area, budget) or regional facts (tariffs). Automatically ignores archived profiles and applies correction notices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The district name (e.g., 'Brightwater') or 'Region'.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Specific facts needed, e.g., 'population and area'.",
                    },
                },
                "required": ["target", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a mathematical expression safely. Use this for all arithmetic. Supports +, -, *, /, **.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate (e.g., '44675 / 921.4').",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


def run_s1_direct(question):
    """S1 - Direct: Все документы в промпте, один вызов."""
    start_time = time.time()

    prompt = f"Documents:\n{ALL_DOCS_TEXT}\n\nQuestion: {question}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.0
    )

    return {
        "answer": response.choices[0].message.content,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "time": time.time() - start_time,
        "log": [{"strategy": "S1", "content": response.choices[0].message.content}],
    }


def run_s2_think_and_vote(question, k=5):
    """S2 - Think and vote: Документы в промпте, 5 вызовов, выбираем частый ответ."""
    start_time = time.time()

    prompt = f"Documents:\n{ALL_DOCS_TEXT}\n\nQuestion: {question}\nReason step by step, then give the final answer."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    total_in_tokens = 0
    total_out_tokens = 0
    answers = []
    log = []

    # Делаем k запросов с температурой 0.7, чтобы ответы немного отличались
    for i in range(k):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.7
        )
        content = response.choices[0].message.content
        answers.append(content)
        log.append({f"sample_{i+1}": content})
        total_in_tokens += response.usage.prompt_tokens
        total_out_tokens += response.usage.completion_tokens

    return {
        "answers": answers,  # Сырые ответы, в run.py мы вытащим из них самый частый "ANSWER: ..."
        "input_tokens": total_in_tokens,
        "output_tokens": total_out_tokens,
        "time": time.time() - start_time,
        "log": log,
    }


def run_s3_tools(question, max_rounds=10):
    """S3 - Tools: Только инструменты, цикл до получения финального ответа."""
    start_time = time.time()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    total_in_tokens = 0
    total_out_tokens = 0
    log = []

    for round_num in range(max_rounds):
        round_start = time.time()
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS_DEF, temperature=0.0
        )

        msg = response.choices[0].message
        total_in_tokens += response.usage.prompt_tokens
        total_out_tokens += response.usage.completion_tokens

        messages.append(msg)

        # Если модель не вызвала инструменты, значит это финальный ответ
        if not msg.tool_calls:
            log.append(
                {
                    "round": round_num + 1,
                    "action": "final_answer",
                    "content": msg.content,
                }
            )
            return {
                "answer": msg.content,
                "input_tokens": total_in_tokens,
                "output_tokens": total_out_tokens,
                "time": time.time() - start_time,
                "log": log,
            }

        # Если вызвала инструменты, обрабатываем каждый
        for call in msg.tool_calls:
            call_start = time.time()
            func_name = call.function.name
            args_str = call.function.arguments

            log_entry = {
                "round": round_num + 1,
                "tool": func_name,
                "inputs": args_str,
            }

            try:
                args = json.loads(args_str)
                if func_name == "lookup":
                    result = lookup(args.get("target", ""), args.get("query", ""))
                elif func_name == "calculate":
                    result = calculate(args.get("expression", ""))
                else:
                    result = json.dumps({"error": "Unknown function"})
            except json.JSONDecodeError:
                result = json.dumps({"error": "Invalid JSON arguments"})

            log_entry["result"] = result
            log_entry["duration_sec"] = round(time.time() - call_start, 3)
            log.append(log_entry)

            # Добавляем ответ инструмента в историю сообщений
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": func_name,
                    "content": result,
                }
            )

    # Если мы превысили max_rounds
    return {
        "answer": "UNANSWERED (hit round limit)",
        "input_tokens": total_in_tokens,
        "output_tokens": total_out_tokens,
        "time": time.time() - start_time,
        "log": log,
    }
