"""
send_daily_questions.py
Sends 10 JNCIA quiz questions to a Telegram chat.
Called by GitHub Actions on a schedule.

Usage:
    python send_daily_questions.py

Environment variables (set as GitHub Secrets):
    TELEGRAM_BOT_TOKEN  – bot token from @BotFather
    TELEGRAM_CHAT_ID    – target chat / channel ID
"""
import os
import json
import math
import requests
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────
# Credentials are read lazily (at runtime) so dry_run.py can import this module
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
QUESTIONS_PER_DAY = 10

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
Q_FILE     = os.path.join(BASE_DIR, "questions.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")   # tracks next question index

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_questions():
    with open(Q_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    # Default: start from the LAST question (reverse order)
    return {"index": -1}  # -1 = use total_q - 1 on first run


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_text(text, parse_mode="HTML"):
    api_base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    resp = requests.post(
        f"{api_base}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_photo(image_path, caption="", parse_mode="HTML"):
    api_base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    with open(image_path, "rb") as img:
        resp = requests.post(
            f"{api_base}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": parse_mode},
            files={"photo": img},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()


def get_answer_letters(q):
    """Return set of correct answer letters, e.g. {'B', 'D'}."""
    return set(q["answer"].strip().upper())


def get_option_letter(opt_text):
    """Extract leading letter from an option string like 'A. some text' or 'A some text'."""
    opt_text = opt_text.strip()
    if opt_text and len(opt_text) >= 1 and opt_text[0].isalpha():
        return opt_text[0].upper()
    return ""

def build_question_message(q, position, total=QUESTIONS_PER_DAY):
    """Build the text block for one question.
    Correct options → bold + ✅ prefix.
    Wrong options   → italic (visually dimmed).
    """
    qnum    = q["number"]
    body    = " ".join(q["body"])
    correct = get_answer_letters(q)

    option_lines = []
    for opt in q["options"]:
        letter = get_option_letter(opt)
        if letter and letter in correct:
            option_lines.append(f"<b>✅ {opt}</b>")
        else:
            option_lines.append(f"<i>{opt}</i>")
    options = "\n".join(option_lines)

    header   = f"📌 <b>Câu {position}/{total} — Question {qnum}</b>"
    img_note = "  🖼 <i>(kèm hình bên dưới)</i>" if q["images"] else ""
    text = (
        f"{header}{img_note}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{body}\n\n"
        f"{options}\n"
    )
    return text.strip()


def build_answer_message(q, position, total=QUESTIONS_PER_DAY):
    """Build the answer reveal block with full option text bolded."""
    qnum    = q["number"]
    correct = get_answer_letters(q)

    # Collect the full text of correct options
    answer_lines = []
    for opt in q["options"]:
        letter = get_option_letter(opt)
        if letter and letter in correct:
            answer_lines.append(f"👉 <code>{opt}</code>")

    # Fallback: just show letters if options weren't parsed correctly
    if not answer_lines:
        answer_lines = [f"👉 <code>{l}</code>" for l in sorted(correct)]

    answers_text = "\n".join(answer_lines)
    text = (
        f"🎯 <b>ĐÁP ÁN CHÍNH XÁC — Q{qnum}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>{answers_text}</blockquote>"
    )
    return text.strip()


def build_batch_header(high_q, low_q, today_str):
    return (
        f"📚 <b>JNCIA Daily Quiz</b> — {today_str}\n"
        f"🔢 Questions <b>{high_q} → {low_q}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
    questions = load_questions()
    total_q   = len(questions)
    state     = load_state()

    # -1 sentinel means "start from the very last question"
    if state["index"] == -1:
        state["index"] = total_q - 1

    idx = state["index"]  # points to the HIGHEST question index in this batch

    # Build batch in REVERSE order: idx, idx-1, ..., idx-9
    batch = []
    for offset in range(QUESTIONS_PER_DAY):
        pos_idx = (idx - offset) % total_q   # wraps around if needed
        batch.append(questions[pos_idx])

    today_str  = date.today().strftime("%d/%m/%Y")
    # batch[0] has the highest question number, batch[-1] the lowest
    high_qnum = batch[0]["number"]
    low_qnum  = batch[-1]["number"]

    # Send header (high → low)
    send_text(build_batch_header(high_qnum, low_qnum, today_str))

    # Send each question + answer
    for pos, q in enumerate(batch, start=1):
        q_text = build_question_message(q, pos)
        a_text = build_answer_message(q, pos)

        # If question has an image, send photo + question as caption
        if q["images"]:
            img_path = os.path.join(BASE_DIR, q["images"][0])
            if os.path.exists(img_path):
                # Send image with question as caption (caption limit 1024 chars)
                caption = q_text[:1020] if len(q_text) > 1020 else q_text
                send_photo(img_path, caption=caption)
            else:
                send_text(q_text)
        else:
            send_text(q_text)

        # Send answer
        send_text(a_text)

    # Next batch starts QUESTIONS_PER_DAY below current idx
    next_idx = (idx - QUESTIONS_PER_DAY) % total_q
    # How many questions remain before wrapping (going backwards)
    remaining = next_idx + 1  # next_idx is 0-based; +1 = number of questions left
    send_text(
        f"\U0001f4ca Đã gửi Questions {high_qnum}–{low_qnum} | "
        f"Còn {remaining} câu trong ngân hàng. "
        f"Chúc ôn thi tốt! \U0001f4aa"
    )

    # Persist state
    state["index"] = next_idx
    save_state(state)
    print(f"Done. Sent Questions {high_qnum}–{low_qnum}. Next index: {next_idx}")


if __name__ == "__main__":
    main()
