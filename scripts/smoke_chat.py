"""Manual smoke tests for Phase 3 POST /chat scenarios (in-process)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.serve.pipeline import answer_question

CASES = [
    ("Exit load of SBI Flexicap?", "factual", "groww.in"),
    ("Should I buy SBI Contra?", "advisory", "amfiindia.com"),
    ("Which is better, Large Cap or Flexicap?", "comparative", "amfiindia.com"),
    ("What was the 3-year return of SBI Large Cap?", "performance", "sbimf.com"),
    ("My PAN is ABCDE1234F what is exit load?", "pii", "amfiindia.com"),
    ("", "error", None),
]


def main() -> int:
    failed = 0
    for question, expect_intent, expect_host in CASES:
        if question == "":
            result = answer_question("")
            ok = result.get("error") == "question_required"
            print(f"EMPTY -> {json.dumps(result)} ok={ok}")
            if not ok:
                failed += 1
            continue
        result = answer_question(question)
        intent = result.get("intent")
        source = result.get("source") or ""
        host_ok = expect_host is None or expect_host in source
        intent_ok = intent == expect_intent
        ok = intent_ok and host_ok and "answer" in result
        print(
            f"Q: {question!r}\n"
            f"  intent={intent} expect={expect_intent} ok_intent={intent_ok}\n"
            f"  source={source}\n"
            f"  answer={result.get('answer', '')[:160]}\n"
            f"  ok={ok}\n"
        )
        if not ok:
            failed += 1
    print(f"failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
