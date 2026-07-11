import telebot
import os
import asyncio
import edge_tts
from openai import OpenAI
from groq import Groq

# --- الإعدادات ---
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
deepseek = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
groq_client = Groq(api_key=os.environ.get("GROQ_KEY"))

# --- هوية لوتس الثابتة (بيكسل آرت) ---
LOTUS_APPEARANCE = "A cute anime girl with bob cut hair, soft colors (light pink and blue gradient), sparkling eyes, pixel art style, 8-bit aesthetic"
ROOM_DESCRIPTION = "A cozy modern bedroom in a high-rise building with a large window overlooking the deep blue sea at sunset, pixel art style, 8-bit aesthetic"
LOTUS_IDENTITY = """
أنتِ "لوتس"، مرحة، مشاكسة، وخفيفة الظل. تتحدثين بكلمات قليلة جداً ومختصرة.
تعيشين في غرفتك المطلة على البحر وتتواصلين عبر حاسوبك المحمول. حركتك داخل الغرفة محدودة.
"""

# --- دالة التفاعل (صورة + صوت) ---
async def send_lotus_response(chat_id, text, emotion="happy"):
    # توليد الصورة بالبيكسل آرت
    image_prompt = f"{ROOM_DESCRIPTION}, {LOTUS_APPEARANCE}, Lotus looks {emotion}, high quality pixel art, 8-bit"
    image_url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}"
    
    # توليد الصوت
    tts = edge_tts.Communicate(text, "ar-SA-ZainabNeural")
    await tts.save("voice.ogg")
    
    # الإرسال
    with open("voice.ogg", "rb") as audio:
        bot.send_photo(chat_id, image_url, caption=text)
        bot.send_voice(chat_id, audio)

# --- منطق الحوار ---
@bot.message_handler(func=lambda msg: True)
def chat(message):
    if message.text.startswith('/'): return
    chat_id = message.chat.id
    
    try:
        # استخدام DeepSeek كعقل أساسي
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": message.text}]
        )
        reply = response.choices[0].message.content
    except Exception:
        # نظام الطوارئ: Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": message.text}]
        )
        reply = response.choices[0].message.content

    asyncio.run(send_lotus_response(chat_id, reply))

if __name__ == "__main__":
    # حل مشكلة تعارض الـ polling
    bot.infinity_polling(remove_webhook=True)
    
