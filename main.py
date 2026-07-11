import telebot
import os
import asyncio
import edge_tts
from groq import Groq

# إعدادات البوت (تأكد من إدخال المتغيرات في Railway)
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# هوية لوتس (فنانة بكسل)
LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة رقمية تعيشين داخل جهاز كمبيوتر قديم في غرفتك الهادئة المطلة على البحر.
كل شيء من حولك مصمم بنمط "البيكسل آرت" (Pixel Art). 
أنتِ هادئة، ذكية، ومختصرة في كلامك. تحبين وصف جمال البحر وتفاصيل غرفتك الصغيرة.
استخدمي رموزاً تعبيرية مثل 🌊، 🕹️، 🎨.
"""

def get_groq_response(user_text):
    # استخدام موديل Llama 3.3 المتقدم
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

async def send_lotus_response(chat_id, text):
    # وصف البيكسل آرت المدمج للوتس وغرفتها
    pixel_art_prompt = "A cute anime girl named Lotus, pixel art style, 8-bit, sitting in her cozy room with a large window, beautiful view of the sea, retro game aesthetic, detailed interior, vibrant colors, nostalgic atmosphere"
    image_url = f"https://image.pollinations.ai/prompt/{pixel_art_prompt.replace(' ', '%20')}"
    
    # محاولة توليد الصوت مع معالجة الأخطاء لضمان استمرارية البوت
    try:
        tts = edge_tts.Communicate(text, "ar-SA-ZainabNeural")
        audio_path = "voice.ogg"
        await tts.save(audio_path)
        
        # التأكد من أن الملف موجود وسليم قبل الإرسال
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            with open(audio_path, "rb") as audio:
                bot.send_photo(chat_id, image_url, caption=text)
                bot.send_voice(chat_id, audio)
        else:
            bot.send_photo(chat_id, image_url, caption=text)
    except Exception:
        # في حال فشل الصوت، أرسل الصورة والنص فقط لضمان استمرار الرد
        bot.send_photo(chat_id, image_url, caption=text)

@bot.message_handler(func=lambda msg: True)
def chat(message):
    try:
        reply = get_groq_response(message.text)
        asyncio.run(send_lotus_response(message.chat.id, reply))
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "أوه، لوتس واجهت خطأً بسيطاً في لوحتها الرقمية! 😅")

if __name__ == "__main__":
    print("لوتس أونلاين وتنتظر رسالتك بأسلوب البيكسل...")
    # Polling مستقر لتجنب تعارض الاتصال
    bot.infinity_polling(none_stop=True)
    
