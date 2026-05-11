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
import html
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

def build_combined_message(q, position, total=QUESTIONS_PER_DAY):
    """Build a single, highly prominent message for memorization.
    - Question body: Bold
    - Wrong options: Italic (dimmed)
    - Correct options: Blockquote + Code + Emoji
    - Escapes HTML to prevent Telegram 400 Bad Request.
    """
    qnum    = q["number"]
    body    = html.escape(" ".join(q["body"]))
    correct = get_answer_letters(q)

    wrong_lines = []
    correct_lines = []
    for opt in q["options"]:
        letter = get_option_letter(opt)
        opt_esc = html.escape(opt)
        if letter and letter in correct:
            correct_lines.append(f"👉 <code>{opt_esc}</code>")
        else:
            wrong_lines.append(f"<i>{opt_esc}</i>")

    if not correct_lines:
        correct_lines = [f"👉 <code>{l}</code>" for l in sorted(correct)]

    wrong_text = "\n".join(wrong_lines)
    correct_text = "\n".join(correct_lines)

    header   = f"📌 <b>Câu {position}/{total} — Question {qnum}</b>"
    img_note = "  🖼 <i>(xem hình bên trên)</i>" if q["images"] else ""

    text = f"{header}{img_note}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"<b>{body}</b>\n\n"
    
    if wrong_text:
        text += f"{wrong_text}\n\n"
        
    text += f"🎯 <b>ĐÁP ÁN CHÍNH XÁC:</b>\n"
    text += f"<blockquote>{correct_text}</blockquote>"
    
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

    # Send each question
    for pos, q in enumerate(batch, start=1):
        msg_text = build_combined_message(q, pos)

        # If question has an image, send photo first, then text message
        if q["images"]:
            img_path = os.path.join(BASE_DIR, q["images"][0])
            if os.path.exists(img_path):
                send_photo(img_path)
                
        send_text(msg_text)

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
