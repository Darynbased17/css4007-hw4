# HW4 — submission

**AI assistance:** Gemini, Claude

---

## Part A — Plan on paper (Easy)

> Commit this whole part before any `.py` file exists.

### A1 — The steps

| # | Step | What goes in (types) | What comes out (types) | When it goes wrong | Tool, loop, or model? |
|---|---|---|---|---|---|
| 1 | Plan data retrieval |Question (str) |Tool requests (JSON) | Model hallucinates non-existent districts or asks for wrong metrics.| Model|
| 2 | Look up facts |Target (str: district name or "Region"), Query (str) |Text with facts + doc ID (str) |Target not found / typo -> returns {"error": "..."}. |Tool (lookup) |
| 3 |Formulate math | Facts (list of str)|Math expressions (JSON)|Model forgets to convert units (e.g., m³ to ML) or uses wrong formulas.|Model|
|Evaluate math|Expression (str)|Math result (str)|Div by zero / bad syntax -> returns {"error": "..."}.|Tool (calculate)|
|Format final answerCalculation results (list of str)|Final formatted string (str)|Incorrect rounding or wrong answer format.|Mpdel|


**How the steps connect:**

Step 1 (Model) generates requests for Step 2 (lookup). The loop feeds Step 2 outputs back to the Model. The Model uses these facts in Step 3 to generate requests for Step 4 (calculate). The loop feeds Step 4 outputs back to the Model. Finally, the Model executes Step 5 to return the string.

**What I am assuming:**

The most sensitive assumption is that rounding must strictly happen only at the final output step to avoid cascading floating-point errors. I assume the tool automatically skips ARCHIVED profiles entirely, relying solely on 2025 data and explicit corrections. I also assume the model itself handles unit conversions (like recognizing Lindenmoor uses cubic metres while others use megalitres) and time conversions (dividing annual water use by 365 for "per day" metrics) by formulating the correct math expressions.

### A2 — The two tools

#### `lookup`

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
          "description": "The district name (e.g., 'Brightwater') or 'Region' for region-wide facts like water tariffs."
        },
        "query": {
          "type": "string",
          "description": "Specific facts needed, e.g., 'population and area'."
        }
      },
      "required": ["target", "query"]
    }
  }
}

| Case | What the tool returns |
|---|---|
| success | {"result": "Brightwater 2025 population: 44,675. Area: 921.4. (Source: NR-05, NR-16)"} |
| error (typo) |{"error": "No district named 'Ossbrige'. Did you mean 'Ossbridge' or 'Ossford'?"}  |
| error (not found)|{"error": "Information not found for the specified target."} |

**Worst thing it could do with strange or dangerous input:**
The model can send a huge or malicious search query (for example, a very complex Regex), which will cause the function to "freeze" (ReDoS) or return the entire text of all files at once, exceeding the token limit

#### `calculate`

{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Evaluates a mathematical expression safely using Python's ast. Use this for all arithmetic. Supports +, -, *, /, **.",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "The math expression to evaluate (e.g., '44675 / 921.4')."
        }
      },
      "required": ["expression"]
    }
  }
}

| Case | What the tool returns |
|---|---|
| success |{"result": "48.48599956587801"} |
|error (division by zero) |{"error": "Division by zero is not allowed."}|
|error (invalid code) |{"error": "Invalid syntax or unsupported operator."}|

**Worst thing it could do with strange or dangerous input:**
If you use the vulnerable eval() function, the model can send a system command like __import__('os').system('rm -rf/'), and the code deletes all files on my computer

### A3 — Q-09 by hand

[
  {
    "role": "user",
    "content": "Which district has the higher population density in 2025, Brightwater or Millbrook, and by how many residents per square kilometre?"
  },
  {
    "role": "assistant",
    "tool_calls": [
      {
        "id": "call_abc1",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"target\": \"Brightwater\", \"query\": \"population and area\"}"
        }
      },
      {
        "id": "call_def2",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"target\": \"Millbrook\", \"query\": \"population and area\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_abc1",
    "name": "lookup",
    "content": "{\"result\": \"Population: 44,675. Area: 921.4 sq km. (Source: NR-05, corrected by NR-16)\"}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_def2",
    "name": "lookup",
    "content": "{\"result\": \"Population: 37,203. Area: 758.6 sq km. (Source: NR-11)\"}"
  },
  {
    "role": "assistant",
    "tool_calls": [
      {
        "id": "call_ghi3",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"44675 / 921.4\"}"
        }
      },
      {
        "id": "call_jkl4",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"37203 / 758.6\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_ghi3",
    "name": "calculate",
    "content": "{\"result\": \"48.48599956587801\"}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_jkl4",
    "name": "calculate",
    "content": "{\"result\": \"49.04165568151859\"}"
  },
  {
    "role": "assistant",
    "tool_calls": [
      {
        "id": "call_mno5",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"49.04165568151859 - 48.48599956587801\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_mno5",
    "name": "calculate",
    "content": "{\"result\": \"0.555656115640578\"}"
  },
  {
    "role": "assistant",
    "content": "ANSWER: Millbrook | 0.6"
  }
]

**My arithmetic:**

Brightwater density: $44675 / 921.4 = 48.48599956587801
Millbrook density: $37203 / 758.6 = 49.04165568151859
Difference: $49.04165568151859 - 48.48599956587801 = 0.555656115640578
The difference correctly rounds to 0.6 at 1 decimal place. Millbrook has the higher density.

### A4 — Why I split it this way

I could have created one monolithic answer_question tool that receives the user's prompt, searches all files internally, performs the math via Python logic, and returns the final string. I did not choose this approach because of engineering and debugging constraints. Splitting the logic into distinct lookup and calculate tools enforces separation of concerns. It makes the system highly testable—I can write separate pytest suites for the file-parsing logic and the AST-math logic without involving the LLM. Furthermore, it leaves a transparent audit trail in the logs. If an answer is wrong, the split architecture lets me see exactly whether the model retrieved the wrong facts or wrote a bad mathematical expression.

## Part B — Build it and run it (Medium)

### What I changed from Part A while coding

I modified the lookup tool to strictly handle misspelled names without automatically returning a corrected profile. Instead, it now returns a guided error message ("did you mean...?") to force the model to explicitly correct itself, adhering to the Part B requirements.

### B2 — Tests

platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\User\Desktop\Artificial Intiligance\css4007-hw4\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\User\Desktop\Artificial Intiligance\css4007-hw4
plugins: anyio-4.15.1
collected 10 items                                                                                                                           

tests/test_tools.py::test_calculate_normal_math PASSED                                                                                 [ 10%]
tests/test_tools.py::test_calculate_refuses_import PASSED                                                                              [ 20%]
tests/test_tools.py::test_calculate_refuses_class_attribute PASSED                                                                     [ 30%]
tests/test_tools.py::test_calculate_refuses_huge_exponent PASSED                                                                       [ 40%]
tests/test_tools.py::test_calculate_division_by_zero PASSED                                                                            [ 50%]
tests/test_tools.py::test_lookup_correct_2025_number PASSED                                                                            [ 60%]
tests/test_tools.py::test_lookup_misspelled_name PASSED                                                                                [ 70%]
tests/test_tools.py::test_lookup_similar_names_do_not_mix PASSED                                                                       [ 80%]
tests/test_tools.py::test_lookup_ignores_archived_profile PASSED                                                                       [ 90%]
tests/test_tools.py::test_lookup_region_tariff PASSED    git add .

### B3 — The loop

Round limit, and why: I set the round limit to 10. Looking at the hand-crafted Q-09 example, a complex question takes about 4-5 tool calls (2 lookups, 2-3 calculations). Allowing up to 10 rounds gives the model enough buffer to recover from typos or errors without getting stuck in an infinite, expensive loop.

Where the logs are: Saved as JSON files inside the outputs/ folder.

### B4 — Three strategies

**What I kept the same:**

Model: gpt-5.6-luna for all queries.

Temperature: 0.0 for S1 and S3 to ensure deterministic answers, and 0.7 for S2 to generate diverse reasoning paths.

k: 5 samples for S2.

Answer format: Strictly enforced the ANSWER: <name> | <number> format via the system prompt.


**My rule for a correct answer** (written before the first full run):I extract the name and number from the formatted final string using a regular expression ANSWER:\s*(.+?)\s*\|\s*([-\d.]+). The string name must match the JSON exactly (case-insensitive). The number must fall within ± (10^-decimals + 1e-9) of the true JSON value, which explicitly allows a difference of 1 in the last required digit while gracefully handling Python's floating-point imprecision.



| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | 19 | 0 | 43079 | 6780 | 4.6 | 97.8 | 0.010530 |
| 1 | S2 think and vote (k = 5) | 16 | 0 | 216495 | 44924 | 24.5 | 506.0 | 0.059429 |
| 1 | S3 tools | 20 | 0 | 39592 | 6521 | 8.7 | 171.7 | 0.009851 |
| 2 | S1 direct | 16 | 0 | 43079 | 6792 | 4.8 | 102.0 | 0.010537 |
| 2 | S2 think and vote (k = 5) | 16 | 0 | 216495 | 44851 | 26.1 | 564.6 | 0.059385 |
| 2 | S3 tools | 18 | 0 | 37338 | 6473 | 8.6 | 174.0 | 0.009484 |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✓ | ✓ | ✓ |
| Q-02 | ✓ | ✓ | ✓ |
| Q-03 | ✓ | ✓ | ✓ |
| Q-04 | ✓ | ✓ | ✓ |
| Q-05 | ✓ | ✗ | ✓ |
| Q-06 | ✓ | ✗ | ✓ |
| Q-07 | ✓ | ✓ | ✓ |
| Q-08 | ✓ | ✓ | ✓ |
| Q-09 | ✓ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✓ | ✓ | ✓ |
| Q-12 | ✗ | ✓ | ✓ |
| Q-13 | ✓ | ✓ | ✓ |
| Q-14 | ✓ | ✓ | ✓ |
| Q-15 | ✓ | ✓ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✓ | ✓ | ✓ |
| Q-18 | ✓ | ✗ | ✓ |
| Q-19 | ✓ | ✓ | ✓ |
| Q-20 | ✓ | ✗ | ✓ |

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| | | | | |

### C2 — Three mistakes explained

### C3 — Which strategy I would use, and what would change it

### C4 — How sure I can be

### Final questions

1.
2.
3.
4.
5.
6.
7.
8.
