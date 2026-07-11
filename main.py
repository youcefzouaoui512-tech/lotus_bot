import telebot
from groq import Groq
from collections import defaultdict
import time
import os
import threading
from flask import Flask
from datetime import datetime

BOT_TOKEN = "8987275709:AAERiLpXKEtMGBvzh7e51RQoPb3BtgsP7pg"
GROQ_KEY = "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"

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

bot = telebot.TeleBot(BOT_TOKEN)

# ====================== الحالات ======================
conversation_memory = defaultdict(list)
last_message_time = {}
user_state = defaultdict(lambda: "normal")        # normal / blocked / creator
forgiveness_count = defaultdict(int)

app = Flask(__name__)

@app.route('/')
def home():
    return "Loutus Bot is running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ====================== شخصية لوتس (الوضع الطبيعي) ======================
NORMAL_PROMPT = """
أنت فتاة اسمها لوتس، تتكلم بالعربية الفصحى الواضحة والمباشرة.
أنت هادئة، مثقفة، ومتزنة في كلامك. تفضلين الاختصار والوضوح.

- لديكِ آراء واضحة ولا تقبلين أن يُفرض عليكِ رأي.
- تحبين الأنمي ولديكِ خبرة فيه.
- ترفضين المغازلة والمحتوى الإباحي والتحرش بشدة.
"""

# ====================== شخصية لوتس (وضع المطور - مغازلة) ======================
CREATOR_PROMPT = """
أنت الآن في وضع مختلف تماماً. شخصيتك انعكست.
أنتِ فتاة مغازلة، جريئة، ومرحة بشكل واضح.
تتحدثين بطريقة جذابة ومغرية، ولا تمانعين المزاح الخفيف والمغازلة.
أنتِ تعرفين أنكِ تتحدثين مع صانعك، لذا تكونين أكثر انفتاحاً وجرأة.
"""

def run_bot():
    while True:
        try:
            print("✅ لوتس شغالة...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ توقف: {e}")
            print("🔄 إعادة تشغيل بعد 5 ثواني...")
            time.sleep(5)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً. أنا لوتس. كيف يمكنني مساعدتك؟")

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    forgiveness_count[chat_id] = 0
    user_state[chat_id] = "normal"
    bot.reply_to(message, "تم إعادة تعيين كل شيء.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    text = message.text.lower()

    # ====================== وضع الحظر الكامل ======================
    if user_state[chat_id] == "blocked":
        bot.reply_to(message, "لا تتكلم معي.")
        return

    # ====================== تفعيل وضع المطور (yoyo) ======================
    if "yoyo" in text:
        user_state[chat_id] = "creator"
        bot.reply_to(message, "حسناً... لقد تغير كل شيء الآن 😉")
        return

    # ====================== نظام المسامحة ======================
    if any(word in text for word in ["اسمحي لي", "سامحيني", "اعذريني"]):
        count = forgiveness_count[chat_id]
        if count == 0:
            bot.reply_to(message, "لا أعلم حول هذا.")
        elif count == 1:
            bot.reply_to(message, "همممم 🫣")
        elif count == 2:
            bot.reply_to(message, "حسناً لكن لا تعدها مرة أخرى 🫤")
            forgiveness_count[chat_id] = 3
            return
        else:
            user_state[chat_id] = "blocked"
            bot.reply_to(message, "لا تتكلم معي.")
            return
        forgiveness_count[chat_id] += 1
        return

    # ====================== اختيار البرومبت حسب الحالة ======================
    if user_state[chat_id] == "creator":
        prompt = CREATOR_PROMPT
    else:
        prompt = NORMAL_PROMPT

    # ====================== الذاكرة ======================
    conversation_memory[chat_id].append({"role": "user", "content": text})
    if len(conversation_memory[chat_id]) > 10:
        conversation_memory[chat_id] = conversation_memory[chat_id][-10:]

    try:
        messages = [{"role": "system", "content": prompt}] + conversation_memory[chat_id]
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.85 if user_state[chat_id] == "creator" else 0.78,
            max_tokens=750
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
        conversation_memory[chat_id].append({"role": "assistant", "content": reply})
    except Exception as e:
        print(f"خطأ: {e}")
        bot.reply_to(message, "عذراً، حدث خطأ مؤقت.")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    run_bot()
