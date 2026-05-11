# JNCIA Daily Quiz Bot 📚

Telegram bot that sends **10 JNCIA exam questions per day** (with answers) via GitHub Actions.

## 📂 Folder structure

```
JNCIA_Only_Dapan/
├── .github/
│   └── workflows/
│       └── daily_quiz.yml      ← GitHub Actions schedule
├── images/                     ← exhibit images extracted from docx
├── JNCIA.docx                  ← question bank (source of truth)
├── questions.json              ← parsed question bank (auto-generated)
├── image_map.json              ← question→image mapping
├── state.json                  ← tracks which question to send next
├── parse_questions.py          ← run locally to regenerate questions.json
├── extract_images.py           ← run locally to re-extract images
├── send_daily_questions.py     ← main bot script (called by Actions)
└── requirements.txt
```

## 🚀 Setup (one-time)

### 1. Create Telegram Bot
1. Chat with [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the **bot token**

### 2. Get Chat ID
- For a **group/channel**: add your bot, send a message, then open  
  `https://api.telegram.org/bot<TOKEN>/getUpdates`  
  and look for `"chat":{"id": ...}`
- For a **personal chat**: use [@userinfobot](https://t.me/userinfobot)

### 3. Add GitHub Secrets
In your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name          | Value                                          |
|----------------------|------------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | `8499058668:AAGZaZpcMzm0RZ2CD6y43KkbPA4nmPrRA6I` |
| `TELEGRAM_CHAT_ID`   | `6733680300`                                   |

### 4. Push everything to GitHub
```bash
git init
git add .
git commit -m "feat: JNCIA daily quiz bot"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

### 5. Enable Actions (if needed)
Go to your repo → **Actions** tab → click **"I understand my workflows, go ahead and enable them"**.

## ⏰ Schedule

| Time (ICT / UTC+7) | Cron (UTC)       | What happens              |
|--------------------|------------------|---------------------------|
| 09:00              | `0 2 * * *`      | 10 questions + answers    |

> GitHub Actions may delay up to ~5 min. The cron is set slightly early to compensate.

## 🔄 State management

`state.json` stores the index of the next question to send. After each run the bot commits the updated file back to the repo automatically. After all 106 questions are sent, it wraps back to Question 1.

## 🖼 Questions with images (exhibits)

Questions **1, 9, 24, 35, 47, 52, 61, 67, 82, 92, 93, 102** contain exhibit images. The bot sends the image as a Telegram photo with the question text as caption.

## 🛠 Re-generating the question bank

If you update `JNCIA.docx`:
```bash
python extract_images.py   # re-extract images
python parse_questions.py  # re-generate questions.json
git add questions.json image_map.json images/
git commit -m "chore: update question bank"
git push
```

## 🧪 Manual test run

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python send_daily_questions.py
```
