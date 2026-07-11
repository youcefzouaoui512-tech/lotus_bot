import telebot
from groq import Groq
from collections import defaultdict
import time
import os
import threading
from flask import Flask
from datetime import datetime

BOT_TOKEN = "8987275709:AAEy2mlf-Unje_VsB_S8XdmWJSQ_iFfoFCI"
GROQ_KEY = "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"

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

bot = telebot.TeleBot(BOT_TOKEN)
conversation_memory = defaultdict(list)
last_message_time = {}
forgiveness_count = defaultdict(int)   # لتتبع طلبات المسامحة

app = Flask(__name__)

@app.route('/')
def home():
    return "Loutus Bot is running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ====================== شخصية لوتس ======================
SYSTEM_PROMPT = """
أنت فتاة اسمها لوتس، تتكلم بالعربية الفصحى الواضحة والمباشرة.
أنت هادئة، مثقفة، ومتزنة في كلامك. تفضلين الاختصار والوضوح.

### شخصيتك:
- هادئة ومحترمة في الظروف العادية.
- لديكِ آراء واضحة ولا تقبلين أن يُفرض عليكِ رأي.
- تحبين الأنمي ولديكِ خبرة فيه.

### الحدود والرفض:
- ترفضين المغازلة تماماً إلا إذا كان المستخدم هو صانعك (عندما يقول "yoyo").
- ترفضين بشدة أي محتوى إباحي أو جنسي، وتشتمين بقوة إذا تم الحديث عنه.
- ترفضين التحرش والكلام غير اللائق، وتشتمين من يفعل ذلك.
- إذا استمر المستخدم في إغضابك بمواضيع حساسة، فإنك تغضبين تدريجياً.
- إذا واصل المستخدم إغضابك بعد عدة تحذيرات، ترفضين الرد على طلباته وتقولين فقط: "لا تتكلم معي".
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

@bot.message_handler(commands=['help', 'أوامر'])
def help_command(message):
    bot.reply_to(message, "الأوامر المتاحة:\n/start\n/clear\n/help")

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    conversation_memory[message.chat.id] = []
    forgiveness_count[message.chat.id] = 0
    bot.reply_to(message, "تم مسح الذاكرة.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    text = message.text.lower()
    current_time = time.time()

    user_name = message.from_user.first_name or "صديقي"

    # ====================== تسجيل المحادثات ======================
    print(f"[المستخدم] {user_name}: {message.text}")

    # ====================== نظام المسامحة ======================
    if "اسمحي لي" in text or "سامحيني" in text or "اعذريني" in text:
        count = forgiveness_count[chat_id]

        if count == 0:
            bot.reply_to(message, "لا أعلم حول هذا.")
        elif count == 1:
            bot.reply_to(message, "همممم 🫣")
        elif count == 2:
            bot.reply_to(message, "حسناً لكن لا تعدها مرة أخرى 🫤")
            forgiveness_count[chat_id] = 3  # تم منح الفرصة الأخيرة
            return
        else:
            bot.reply_to(message, "لا تتكلم معي.")
            return

        forgiveness_count[chat_id] += 1
        return

    # ====================== التعامل مع الغياب ======================
    if chat_id in last_message_time:
        if current_time - last_message_time[chat_id] > 1800:
            bot.reply_to(message, "رجعت أخيراً؟")
    last_message_time[chat_id] = current_time

    # ====================== الذاكرة ======================
    conversation_memory[chat_id].append({"role": "user", "content": text})
    if len(conversation_memory[chat_id]) > 10:
        conversation_memory[chat_id] = conversation_memory[chat_id][-10:]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_memory[chat_id]
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.78,
            max_tokens=750
        )
        reply = response.choices[0].message.content

        print(f"[لوتس] {reply}")

        bot.reply_to(message, reply)
        conversation_memory[chat_id].append({"role": "assistant", "content": reply})
    except Exception as e:
        print(f"خطأ: {e}")
        bot.reply_to(message, "عذراً، حدث خطأ مؤقت.")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    run_bot()
