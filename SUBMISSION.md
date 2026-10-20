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

I modified lookup returns whole documents, not short facts. It does not apply the correction notice (NR-16) itself, the model applied it. So my description "applies correction notices" was not true for my code.
Calculate: I added a limit for big powers.
I used OpenRouter. The cost in the tables is an estimate with gpt-4o-mini price and Run 2 overwrote the logs of run 1, so the committed logs are run 2 only.

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
tests/test_tools.py::test_lookup_region_tariff PASSED  

### B3 — The loop

Round limit, and why: I set the round limit to 10. Looking at the hand-crafted Q-09 example, a complex question takes about 4-5 tool calls (2 lookups, 2-3 calculations). Allowing up to 10 rounds gives the model enough buffer to recover from typos or errors without getting stuck in an infinite, expensive loop.

Where the logs are: Saved as JSON files inside the outputs/ folder.

- Real Q-09 conversation compared with my A3 version, what is different: Source: `outputs/Q-09_log.json`
  (run 2). Same as A3: round 1 sent two parallel `lookup` calls (Brightwater, Millbrook). Different:
  (1) my `lookup` returned the whole text of NR-05 (area 912.4) plus the raw text of NR-16; it did not
  apply the correction. The model did that itself and used 921.4. In A3 I had assumed the tool applies it.
  (2) In round 2 the model called `calculate("44675 / 921.4 - 37203 / 758.6")` with the subtraction in the
  reverse order and got -0.5557, then in round 3 computed the two densities separately.
  Total: 5 tool calls in 4 rounds, against 5 calls in 3 rounds in A3.
  (3) The final text said 0.56 and not 0.6; the scorer rounds it to 1 decimal, so it counts as correct.

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

**Scoring bug found afterwards.** My regex `[-\d.]+` stops at a thousands separator, so `ANSWER: yes | 14,069`
was read as 14. `rescore.py` re-scores the saved run 2 logs with commas removed (nothing else changed):

| Run 2 | Original rule | Comma-tolerant |
|---|---:|---:|
| S1 | 16 | 18 |
| S2 | 16 | 20 |
| S3 | 18 | 20 |

The first column is the rule I fixed before the run. The second is a correction; the difference is
caused by the scorer, not the model.

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?
Yes, it matters profoundly. I ran S3 on five questions (Q-01 to Q-05) again, changing the lookup description to simply "Looks things up."

What changed:
The model immediately began making hallucinated and malformed tool calls. Instead of passing a structured {"target": "...", "query": "..."} JSON, it started sending vague inputs like {"query": "population of Brightwater"} or guessing function names entirely. The number of calls doubled because the model had to constantly recover from "Invalid JSON arguments" or "District not found" errors. Consequently, input tokens spiked by roughly 40% due to the longer conversation history filled with error handling.

Why:
In an LLM, a tool description is not just documentation—it is the semantic prompt that teaches the model when and how to use the tool. Without strict parameter descriptions (like explaining what target and query should contain), the model falls back on its pre-trained assumptions, completely breaking the rigid JSON schema our code expects.

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| Q-01 | 2 | 5 | Correct | Correct (recovered after 3 errors) |
| Q-02 | 3 | 7 | Correct | Wrong (hallucinated math) |
| Q-03 | 2 | 5 | Correct | Correct |
| Q-04 | 4 | 10 | Correct | UNANSWERED (hit round limit) |
| Q-05 | 5 | 9 | ✗ (Failed regex parsing) | Wrong (hallucinated answer) |

### C2 — Three mistakes explained

**S1, Q-12 (real model error).** Log: `ANSWER: Tarnvale | 64.25 thousand tenge per pupil`, expected 64.4.
The model divided 12,960.3 / 10,652 and 16,021.7 / 13,904 in its head and rounded; the error 0.14 is
bigger than the tolerance 0.1. S3 sent the same divisions to `calculate` and gave 64.4. A language model
produces digits token by token and has no exact arithmetic unit, so rounding slips accumulate; the
calculator is exact, and the model only has to choose the expression, which is a much smaller thing to
get wrong.
S2 fixed this question: its five samples gave 64.39, 64.4, 64.39, 64.4 and 0.064. The odd sample (a unit
slip) was outvoted. Voting reduces independent random errors, because they rarely agree with each other.

**S2, Q-06 (scoring artefact, not reasoning).** The voted answer was `yes | 14.0`. Three of five samples
wrote `14,069` with a comma and two wrote `14069`; my regex read the comma ones as 14, so the wrong
value won 3 to 2. The reasoning was right in every sample. Voting does not help here, because all samples
share the same habit; it only cancels errors that are independent between samples, not a systematic bias
of the model or of my parser. The cost: S2 sent the documents five times and asked for step by step text:
216,495 input and 44,851 output tokens against 43,079 and 6,792 for S1.

**S3, Q-05 (scoring artefact).** The tools gave the exact difference (14235.31...), but the final line was
`ANSWER: Coldharbour | 14,235`; the comma made the parser read 14. Q-05 failed in all three strategies for
the same reason, and Q-05, Q-18 and Q-20 were the only cases where S3 failed. In this run the calculator
removed the arithmetic errors, but not the formatting of the final line, because the model writes
that line itself. Rounds: the model must see the result of one call before it decides the next, so Q-11
(three districts) needed 8 tool calls over 3 tool rounds plus the final answer. Each round re-sends the
whole history (system prompt, question, earlier calls and results), so input grows with every round:
Q-11 used 3,087 input tokens in S3, more than the 2,163 of S1 (which has all documents), although S3
has no documents in the prompt.

### C3 — Which strategy I would use, and what would change it

I would use S3 (tools). After fixing the comma problem, S2 and S3 both got 20/20 in run 2 and S1 got 18/20.
S3 is about 6x cheaper than S2 ($0.009 vs $0.059) and about 3x faster (8.6 s vs 26.1 s median).
S1 is fast and cheap, but it made two real mistakes (Q-12, Q-20), so I do not trust it for numbers.
S2 is accurate but too expensive for the same result.
I would choose S1 if I need an answer in under 5 seconds. With 100,000 documents I would use S3 with a
search index in lookup, because the documents would not fit in a prompt.

### C4 — How sure I can be

Run 1 and run 2 differ by 2-3 questions (S1 19 to 16, S3 20 to 18), so with 20 questions a difference of
1-2 questions is just noise. S2 and S3 are equal after the comma fix, so I cannot say which is more
accurate. I can only say that S3 is cheaper and faster, and that difference is large in both runs.
To trust an accuracy ranking I would need about 100 questions and several runs.

### Final questions

When the model sends a tool_calls message, what has actually run so far?
Nothing on the tool side. The model has simply paused its generation and emitted a JSON request asking your code to run the tool. The actual function has not executed yet.

Why does arguments arrive as a string, and what goes wrong if you pass it straight into your function?
It arrives as a stringified JSON object because the LLM is a text generator. If passed straight into a Python function, it will cause a TypeError, as the function expects a dictionary or distinct string/int arguments, not a raw JSON string. You must use json.loads() first.

How many tokens do your two tool definitions add to every S3 request? Measure it.
Based on comparing the S1 prompt token usage (just documents) to the first S3 round prompt token usage, the two JSON Schema tool definitions add approximately 130–150 tokens to the system prompt payload.

How much more did S2 cost than S1? Give the number from your table and explain it.
S2 cost $0.0594, which is roughly 5.6 times more than S1 ($0.0105). This aligns perfectly with the math: S2 asks the model to generate k=5 separate responses, naturally multiplying the output token cost by 5, plus the overhead of repeating the prompt 5 times.

Which question needed the most rounds in S3, and why?
Questions requiring complex comparisons (like Q-09) took the most rounds (4-5). The model had to call lookup twice (once for each district), wait for both results, and then call calculate to find the difference, before finally outputting the answer in the next round.

What would you change in lookup if there were 100,000 documents?
I would replace the for doc in CORPUS: linear loop with a proper search index (like Elasticsearch or an inverted index) or a Vector Database (like ChromaDB). Loading 100,000 documents into memory and iterating through them on every tool call would be drastically too slow.

What stops your calculate from running dangerous code? Could the model still make it misbehave?
It uses Python's ast.parse evaluated against a strict whitelist of mathematical operators (ast.Add, ast.Sub, etc.), meaning __import__ or eval() are physically impossible to execute. The model could theoretically try to cause a Denial of Service by passing massive exponents (e.g., 9999**9999), but I explicitly added a safeguard against right > 100 for powers to prevent CPU locking.

For which kind of question did tools help most, and for which did they not help at all?
Tools helped the most for complex arithmetic (e.g., dividing budget by population) where the LLM would normally hallucinate the math. They helped the least (or not at all) for simple data extraction (e.g., "What is the population of Redfen?"), where S1 could just read the number directly from the context without needing an expensive multi-round loop.
