import ast
import operator
import json
import os
import difflib

def load_corpus():
    corpus = []
    filepath = os.path.join(os.path.dirname(__file__), 'data', 'corpus.jsonl')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    corpus.append(json.loads(line))
    except FileNotFoundError:
        pass
    return corpus

CORPUS = load_corpus()

def calculate(expression: str) -> str:
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            op_type = type(node.op)

            if op_type not in allowed_operators:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")

            if op_type == ast.Pow:
                if right > 100 or left > 1000000:
                    raise ValueError("Exponent too large. Computation refused.")

            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero is not allowed.")

            return allowed_operators[op_type](left, right)
            
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in allowed_operators:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            return allowed_operators[op_type](operand)
        else:
            raise TypeError("Invalid syntax. Only basic math is allowed.")

    try:
        tree = ast.parse(expression, mode='eval')
        result = eval_node(tree.body)
        return json.dumps({"result": str(result)})
    except ZeroDivisionError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Invalid expression. {str(e)}"})

def lookup(target: str, query: str) -> str:
    districts = [
        "Ossbridge", "Ossford", "Tarnvale", "Kelmarsh", "Brightwater",
        "Stonecairn", "Harrowfield", "Lindenmoor", "Redfen", "Ashgrove",
        "Millbrook", "Coldharbour"
    ]
    
    target_clean = target.strip()
    search_target = target_clean

    if target_clean.lower() != "region":
        matched_district = next((d for d in districts if d.lower() == target_clean.lower()), None)
        
        if not matched_district:
            guesses = difflib.get_close_matches(target_clean, districts, n=2, cutoff=0.4)
            if guesses:
                guess_str = " or ".join(f"'{g}'" for g in guesses)
                return json.dumps({"error": f"no district named {target_clean}; did you mean {guess_str}?"})
            return json.dumps({"error": f"District '{target_clean}' not found."})
        
        search_target = matched_district

    results = []
    
    for doc in CORPUS:
        title = doc.get('title', '')
        text = doc.get('text', '')
        doc_id = doc.get('id', '')
        
        if "ARCHIVED" in title or "ARCHIVED" in text:
            continue
            
        if search_target.lower() == "region":
            if "tariff" in title.lower() or "region" in title.lower() or "region" in text.lower():
                results.append(f"[{doc_id}] {title}: {text}")
        else:
            if search_target.lower() in title.lower() or search_target.lower() in text.lower():
                results.append(f"[{doc_id}] {title}: {text}")

    if not results:
        return json.dumps({"error": "No relevant information found."})
        
    final_text = " | ".join(results)
    return json.dumps({"result": final_text})