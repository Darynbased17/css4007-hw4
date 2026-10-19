# HW4 — submission

**AI assistance:** Gemini

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

<!-- what changed in your plan, and why. "None" is an answer too. -->

### B2 — Tests

```text
<!-- pytest output -->
```

### B3 — The loop

- Round limit, and why:
- Where the logs are:
- Real Q-09 conversation compared with my A3 version, what is different:

### B4 — Three strategies

**What I kept the same:**

<!-- model, temperature, k, prompts, answer format, anything else -->

**My rule for a correct answer** (written before the first full run):

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | | | | | | | |
| 1 | S2 think and vote (k = ) | | | | | | | |
| 1 | S3 tools | | | | | | | |
| 2 | S1 direct | | | | | | | |
| 2 | S2 think and vote (k = ) | | | | | | | |
| 2 | S3 tools | | | | | | | |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | | | |
| Q-02 | | | |
| Q-03 | | | |
| Q-04 | | | |
| Q-05 | | | |
| Q-06 | | | |
| Q-07 | | | |
| Q-08 | | | |
| Q-09 | | | |
| Q-10 | | | |
| Q-11 | | | |
| Q-12 | | | |
| Q-13 | | | |
| Q-14 | | | |
| Q-15 | | | |
| Q-16 | | | |
| Q-17 | | | |
| Q-18 | | | |
| Q-19 | | | |
| Q-20 | | | |

---

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
