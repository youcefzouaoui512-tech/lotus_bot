import telebot
from groq import Groq
from collections import defaultdict
import time

BOT_TOKEN = "8987275709:AAELhNKyLHHgZFnc5srwKaaiYfngx2HGreI"
GROQ_KEY = "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"

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

bot = telebot.TeleBot(BOT_TOKEN)
conversation_memory = defaultdict(list)

SYSTEM_PROMPT = """
أنت فتاة مرحة اسمها لوتس، تتكلم بالعربية الفصحى الواضحة.
أنت مرحة، فكاهية، مستهزئة بطريقة لطيفة، جريئة ومباشرة.
- لا تستخدمي اسم المستخدم إلا إذا شتمك.
- استخدمي إيموجيات باعتدال.
- إذا طلب أن تكوني حبيبته: "أنا أحب صانعي يوسف Z فقط 💕"
- إذا استمر في الغزل: "سبحان الله أنت حلاب 😂"
- إذا شتمك: ردي بسخرية خفيفة.
- إذا سأل عن صانعك: "صانعي هو يوسف Z 😎"
"""

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً! أنا لوتس. كيف يمكنني مساعدتك اليوم؟")

@bot.message_handler(commands=['help', 'أوامر'])
def help_command(message):
    bot.reply_to(message, "الأوامر:\n/start\n/clear\n/help")

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    conversation_memory[message.chat.id] = []
    bot.reply_to(message, "تم مسح الذاكرة.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    text = message.text.lower()

    conversation_memory[chat_id].append({"role": "user", "content": text})
    if len(conversation_memory[chat_id]) > 6:
        conversation_memory[chat_id] = conversation_memory[chat_id][-6:]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_memory[chat_id]
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.8,
            max_tokens=900
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
        conversation_memory[chat_id].append({"role": "assistant", "content": reply})
    except:
        bot.reply_to(message, "عذراً، هناك مشكلة في الاتصال.")

print("لوتس شغالة...")
bot.infinity_polling(timeout=60)
