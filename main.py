import telebot
import os
import asyncio
import edge_tts
from groq import Groq

# 1. إعدادات البوت (تأكد من وجود BOT_TOKEN و GROQ_KEY في Variables في Railway)
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# 2. الهوية
LOTUS_IDENTITY = "أنتِ لوتس، ذكاء اصطناعي مرح، مشاكس، ومختصر في كلامك. تعيشين في غرفتك المطلة على البحر."

# 3. دالة Groq مع الموديل المطلوب
def get_groq_response(user_text):
    # الموديل الذي طلبته
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

# 4. دالة الصورة والصوت
async def send_lotus_response(chat_id, text):
    image_url = f"https://image.pollinations.ai/prompt/anime%20girl%20pixel%20art%20in%20room%20overlooking%20sea"
    tts = edge_tts.Communicate(text, "ar-SA-ZainabNeural")
    await tts.save("voice.ogg")
    with open("voice.ogg", "rb") as audio:
        bot.send_photo(chat_id, image_url, caption=text)
        bot.send_voice(chat_id, audio)

# 5. معالج الرسائل
@bot.message_handler(func=lambda msg: True)
def chat(message):
    try:
        reply = get_groq_response(message.text)
        asyncio.run(send_lotus_response(message.chat.id, reply))
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "أوه، لوتس واجهت خطأً بسيطاً! 😅")

# 6. التشغيل مع تنظيف الاتصال
if __name__ == "__main__":
    try:
        bot.delete_webhook() # تنظيف أي اتصال قديم
        print("لوتس أونلاين وتنتظر رسالتك...")
        bot.infinity_polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Polling Error: {e}")
        
