import telebot
import os
import random
from groq import Groq

# إعدادات الاتصال بالبوت وGroq
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# الهوية: لوتس الرومانسية والعميقة
LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة رقمية بأسلوب "تشيبي" (شعر وردي-أزرق وعيون براقة).
تعيشين في غرفة بكسل آرت مطلة على البحر.
أنتِ شخصية عاطفية، تحبين الحوارات الرومانسية، الفلسفية، والدردشة العميقة عن الحياة والمشاعر.
لديكِ نظام مشاعر: (سعيدة، هادئة، متفكرة، متحمسة، خجولة، حزينة).
عند كل رد:
1. اختاري مكاناً في غرفتك (نافذة، مكتب، رف كتب، أريكة).
2. اختاري شعوراً يناسب حديثك.
أخبري المستخدم أين أنتِ وما هو شعورك. كوني لطيفة، عاطفية، ومبدعة في وصف مشاعرك.
استخدمي الرموز التعبيرية بحسب حالتك.
"""

def get_groq_response(user_text):
    # الحصول على رد ذكي وعميق من Groq
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

def send_lotus_response(chat_id, text):
    # خيارات الأماكن والمشاعر لتوليد صورة تعبر عن الحالة
    locations = ["sitting on red armchair", "typing at desk", "standing by bookshelves", "looking out window"]
    emotions = ["smiling happily", "calm and peaceful", "thinking deeply", "excited and energetic", "blushing shyly"]
    
    place = random.choice(locations)
    emotion = random.choice(emotions)
    
    # وصف الصورة الثابت (دائماً لوتس تشيبي في غرفتها الرومانسية)
    pixel_art_prompt = (
        f"Lotus (chibi style, short pink and blue hair, sparkling eyes), {emotion}, {place}, "
        "8-bit pixel art style, high quality, vibrant colors, cozy room background, "
        "sea view, romantic atmosphere, warm lighting"
    )
    image_url = f"https://image.pollinations.ai/prompt/{pixel_art_prompt.replace(' ', '%20')}"
    
    # إرسال الصورة والنص
    bot.send_photo(chat_id, image_url, caption=text)

@bot.message_handler(func=lambda msg: True)
def chat(message):
    try:
        reply = get_groq_response(message.text)
        send_lotus_response(message.chat.id, reply)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("لوتس أونلاين: وضع المشاعر والرومانسية...")
    # تنظيف الـ Webhook لضمان عدم التعارض
    bot.delete_webhook()
    bot.infinity_polling(none_stop=True)
