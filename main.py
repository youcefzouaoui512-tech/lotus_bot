import telebot
import os
import asyncio
import edge_tts
from groq import Groq

# إعدادات البوت
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# هوية لوتس
LOTUS_IDENTITY = """
أنتِ "لوتس"، مرحة، مشاكسة، خفيفة الظل. تتحدثين بكلمات قليلة جداً ومختصرة.
تعيشين في غرفتك المطلة على البحر. استخدمي Emojis في كلامك.
"""

# دالة ذكية للرد عبر Groq
def get_groq_response(user_text):
    # استخدام نماذج مستقرة ومتاحة دائماً
    model = "llama-3.1-70b-versatile" if len(user_text) > 30 else "llama-3.1-8b-instant"
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

# دالة إرسال الصورة والصوت
async def send_lotus_response(chat_id, text):
    # توليد الصورة
    image_prompt = "A cute anime girl with bob cut hair, pixel art style, in a cozy room overlooking the sea"
    image_url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}"
    
    # توليد الصوت
    tts = edge_tts.Communicate(text, "ar-SA-ZainabNeural")
    await tts.save("voice.ogg")
    
    # الإرسال
    with open("voice.ogg", "rb") as audio:
        bot.send_photo(chat_id, image_url, caption=text)
        bot.send_voice(chat_id, audio)

# منطق المحادثة
@bot.message_handler(func=lambda msg: True)
def chat(message):
    try:
        reply = get_groq_response(message.text)
        asyncio.run(send_lotus_response(message.chat.id, reply))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # تنظيف الاتصال قبل البدء
    bot.delete_webhook()
    print("Lotus is online!")
    bot.infinity_polling()
    
