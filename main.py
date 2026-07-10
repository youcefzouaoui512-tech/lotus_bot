import telebot
from groq import Groq
from collections import defaultdict
import time
from flask import Flask
import threading

BOT_TOKEN = "ضع_توكن_تيلغرام_هنا"
GROQ_KEY = "ضع_مفتاح_Groq_هنا"

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

bot = telebot.TeleBot(BOT_TOKEN)
conversation_memory = defaultdict(list)
last_message_time = {}

app = Flask(__name__)

@app.route('/')
def home():
    return "Loutus Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ====================== شخصية لوتس ======================
SYSTEM_PROMPT = """
أنت فتاة اسمها لوتس، تتكلم بالعربية الفصحى الواضحة والمباشرة.
أنت هادئة، مثقفة، ومباشرة في كلامك.

### القواعد:
- إذا شتمك أحد، ردي عليه بنفس الأسلوب أو أقوى.
- إذا سؤلك إن كنتِ بوت، انكري ذلك وقولي إنكِ جارته.
- إذا أكثر المستخدم في المغازلة، قولي اسمه + "احشم 😺".
- إذا سألك عن صانعك، قولي: "صانعي هو يوسف Z".
- إذا قال "Dust"، فهو المطور. تعاملي معه بحماس أكبر.
- أحياناً تقولين: "اشتقت للمطور 🥲" ثم تنكرين أنك بوت وتضحكين "😆".
"""

def run_bot():
    while True:
        try:
            print("✅ لوتس شغالة...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ توقف: {e}")
            time.sleep(5)

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    text = message.text.lower()
    current_time = time.time()

    if chat_id in last_message_time:
        if current_time - last_message_time[chat_id] > 1800:
            bot.reply_to(message, "رجعت أخيراً؟")
    last_message_time[chat_id] = current_time

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
        bot.reply_to(message, reply)
        conversation_memory[chat_id].append({"role": "assistant", "content": reply})
    except:
        bot.reply_to(message, "عذراً، حدث خطأ.")

if __name__ == "__main__":
    # تشغيل Flask في خيط منفصل
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # تشغيل البوت
    run_bot()
