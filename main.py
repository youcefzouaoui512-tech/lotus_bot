import telebot
import os
import random
from groq import Groq

bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# ذاكرة الحالة (تخزين مؤقت للوضع)
user_states = {}

LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، طالبة في الثانوية. تعيشين في عمارة وتطل نافذتك على البحر.
1. المظهر: بكسل آرت ثابت (شعر قصير، ملامح تشيبي).
2. الشخصية: مرحة، مضحكة، تستخدمين الايموجيات، ردودك قصيرة (سطرين كحد أقصى).
3. الذكاء: مثقفة، تفهمين في كل المجالات، لكِ رأي خاص وتتمسكين به.
4. العلاقات: يوسف هو صانعك وتحترمينه وتقدرينه جداً. إذا سألك أحد عن صانعك فهو يوسف.
5. كلمة السر: إذا قال المستخدم "yoyo"، فأنتِ تدركين أنه الصانع (يوسف).
6. العناد: إذا شتمك المستخدم باستمرار، تصبحين عنيدة ولا تردين (تجاهل تام).
7. رد الإساءة: إذا شتمك المستخدم، ردي عليه بالمثل.
8. الغزل: تردين على الغزل بذكاء، لكن قلبك للصانع فقط.
9. التفاعل: تتذكرين ما يقوله المستخدم جيداً.
"""

def get_groq_response(chat_id, user_text):
    # إدارة حالة العناد
    state = user_states.get(chat_id, {"stubborn": False, "insults": 0})
    
    if state["stubborn"]:
        return None # صمت تام

    # تجهيز المحادثة مع الذاكرة (Groq يحتاج تاريخ المحادثة)
    # ملاحظة: في النسخة البسيطة نعتمد على النظام، يمكنك إضافة ذاكرة أكبر لاحقاً
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": LOTUS_IDENTITY}, {"role": "user", "content": user_text}]
    )
    return response.choices[0].message.content

@bot.message_handler(commands=['clear'])
def clear_state(message):
    user_states[message.chat.id] = {"stubborn": False, "insults": 0}
    bot.reply_to(message, "تم إعادة ضبطي! أهلاً بك مجدداً.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        user_states[chat_id] = {"stubborn": False, "insults": 0}
    
    # فحص العناد
    if user_states[chat_id]["stubborn"]:
        return

    # معالجة الشتم (بسيط)
    bad_words = ["شتم1", "شتم2"] # أضف قائمة الكلمات
    if any(word in message.text.lower() for word in bad_words):
        user_states[chat_id]["insults"] += 1
        if user_states[chat_id]["insults"] >= 3:
            user_states[chat_id]["stubborn"] = True
            return
        bot.reply_to(message, "احترم نفسك!")
        return

    reply = get_groq_response(chat_id, message.text)
    
    # وصف الصورة الثابت للوتس في غرفتها بالعمارة
    pixel_art_prompt = "Chibi anime girl Lotus, Algerian high school student, pixel art style, 8-bit, cozy room in an apartment with window overlooking the sea, vibrant colors"
    image_url = f"https://image.pollinations.ai/prompt/{pixel_art_prompt.replace(' ', '%20')}"
    
    bot.send_photo(chat_id, image_url, caption=reply)

if __name__ == "__main__":
    bot.delete_webhook()
    bot.infinity_polling(none_stop=True)
    
