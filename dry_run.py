"""
dry_run.py – Preview what the bot would send today, without calling Telegram.
"""
import json, os, sys
# Force UTF-8 output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from send_daily_questions import (
    load_questions, load_state,
    build_batch_header, build_question_message, build_answer_message,
    QUESTIONS_PER_DAY
)
from datetime import date

questions  = load_questions()
total_q    = len(questions)
state      = load_state()

# Mirror the sentinel logic from main()
if state["index"] == -1:
    state["index"] = total_q - 1

idx = state["index"]

# Build batch in REVERSE order (highest question first)
batch = [questions[(idx - offset) % total_q] for offset in range(QUESTIONS_PER_DAY)]

today_str  = date.today().strftime("%d/%m/%Y")
high_qnum  = batch[0]["number"]
low_qnum   = batch[-1]["number"]
next_idx   = (idx - QUESTIONS_PER_DAY) % total_q

SEP = "=" * 55

print(SEP)
print(build_batch_header(high_qnum, low_qnum, today_str))
print(SEP)

for pos, q in enumerate(batch, start=1):
    print()
    if q["images"]:
        print("[IMAGE: %s]" % q["images"][0])
    print(build_question_message(q, pos))
    print()
    print(build_answer_message(q, pos))
    print("-" * 45)

print()
print("State after this run: index=%d (next batch starts at Q%d)" % (
    next_idx, questions[next_idx]["number"]
))
