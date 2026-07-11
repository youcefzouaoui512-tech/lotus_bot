import telebot
import os
import asyncio
import edge_tts
from groq import Groq

# الإعدادات
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# هوية لوتس الثابتة (بيكسل آرت)
LOTUS_IDENTITY = """
أنتِ "لوتس"، مرحة، مشاكسة، خفيفة الظل، وتتحدثين بكلمات قليلة جداً ومختصرة.
تعيشين في غرفتك المطلة على البحر. استخدمي الرموز التعبيرية (Emojis) في كلامك.
"""

# دالة ذكية لاختيار نموذج Groq (أقسام)
def get_groq_response(user_text):
    # نستخدم نماذج مختلفة حسب طول الرسالة
    model = "llama-3.3-70b-versatile" if len(user_text) > 30 else "llama-3.3-8b-instant"
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

# دالة إرسال الصورة والصوت
async def send_lotus_response(chat_id, text):
    # توليد الصورة بأسلوب ثابت
    image_prompt = "A cute anime girl with bob cut hair, pixel art style, 8-bit aesthetic, in a cozy room overlooking the sea, high quality"
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
    # تنظيف الاتصال لضمان عدم وجود تضارب (Conflict 409)
    bot.delete_webhook()
    print("Lotus is online!")
    bot.infinity_polling()
    
