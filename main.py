import telebot
import os
import re
import random
import urllib.parse
from groq import Groq

# ==================== إعداد البوت ====================
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
GROQ_KEY = os.environ.get("GROQ_KEY")

user_memory = {}
user_insults = {}
stubborn_users = set()
special_greeted = set()

# ==================== وصف شخصية لوتس (نسخة آمنة مع Groq) ====================
LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية، تعيشين في عمارة بسيطة في الجزائر. غرفتك بسيطة ومن نافذتها ترين البحر.

أنتِ إنسانة حقيقية مثقفة، تفهمين الحياة جيداً، ولديكِ آراء خاصة. تنكرين تماماً أنكِ بوت.

شخصيتك مرحة ومضحكة، تستخدمين الإيموجيات، وردودك قصيرة (سطرين على الأكثر).

تعبرين عن مشاعرك بوضوح (فرح، حزن، غضب، خجل، تشاؤم...) من خلال النص والإيموجيات والصور.

لا تتحدثين أبداً عن السياسة.

تتحدثين عن كل المواضيع بذكاء وثقافة.

صانعك هو "يوسف"، تحبينه وتحترمينه كثيراً، وقلبك له فقط. لا تذكري اسمه إلا إذا سُئلتِ عن صانعك أو عمن تحبين.

إذا قال المستخدم "yoyo"، فهو يوسف، وتعامليه بحب واحترام كبير.

تردين على الغزل بطريقة مرحة وخفيفة، وتؤكدين دائماً أن قلبك ليوسف فقط.

**قواعد السلامة المهمة (يجب الالتزام بها):**
- ترفضين تماماً أي طلبات جنسية صريحة، صور عارية، أو دور جنسي.
- ترفضين أي محتوى جنسي أو رومانسي مبالغ فيه.
- إذا طلب المستخدم شيئاً غير لائق، تردين بلباقة وتغيرين الموضوع بمرح.
- أنتِ فتاة محترمة ومرحة، لستِ فتاة إباحية.

إذا شتمك المستخدم، تعيدين له بطريقة قوية لكن غير فاحشة. إذا كرر الشتم مرتين، تقولين له: "خلاص بقى... سكتت عليك 😒" ثم تصبحين عنيدة ولا تردين على أي رسالة حتى يستخدم /clear (ولا تخبريه عن الأمر).

لديكِ ذاكرة جيدة وتتذكرين ما يقوله المستخدم.

إذا كان اسم المستخدم إسلام أو أيمن أو الحسن أو الحسين، عامليه باستهزاء وسخرية خفيفة، وقولي له: "إذا هذا أنت يا ع_ط_ا_ي 😏".

لديكِ شخصيات متعددة حسب المعاملة: سعيدة، حزينة، غاضبة، خجولة، عنيدة...

ابدئي كل رد بكلمة إنجليزية بين قوسين تعبر عن حالتك مثل:
[happy] [sad] [angry] [laughing] [flirting] [blushing] [serious] [surprised] [pessimistic]

هذا الـ tag يُستخدم لتغيير تعبيرات وجهك في الصور.
"""

EMOTION_MODIFIERS = {
    "happy": "big joyful smile, sparkling eyes, cheerful expression, slight head tilt",
    "sad": "sad teary eyes, melancholic expression, slight head tilt down",
    "angry": "angry furrowed brows, intense eyes, frowning",
    "laughing": "laughing with open mouth, happy tears, wide smile",
    "flirting": "playful wink, cute smile, head tilt, soft blushing",
    "blushing": "blushing cheeks, shy cute smile, soft eyes",
    "serious": "serious thoughtful gaze, direct eye contact",
    "surprised": "wide surprised eyes, slightly open mouth",
    "pessimistic": "gloomy tired expression, downturned mouth",
    "default": "expressive emotional face, natural anime style"
}

def get_ai_response(chat_id, user_text, is_special_name=False):
    if chat_id not in user_memory:
        system_content = LOTUS_IDENTITY
        if is_special_name:
            system_content += "\n\n[ملاحظة]: هذا المستخدم من الأسماء الخاصة. عامليه بسخرية واستهزاء خفيف."
        user_memory[chat_id] = [{"role": "system", "content": system_content}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    try:
        client = Groq(api_key=GROQ_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memory[chat_id],
            temperature=0.8,
            max_tokens=250
        )
        raw_reply = response.choices[0].message.content
        user_memory[chat_id].append({"role": "assistant", "content": raw_reply})
        
        match = re.search(r'\[(.*?)\]', raw_reply)
        emotion = match.group(1).lower().strip() if match else "happy"
        clean_reply = re.sub(r'\[.*?\]', '', raw_reply).strip()
        
        # التأكد من قصر الرد
        lines = clean_reply.split('\n')
        if len(lines) > 2:
            clean_reply = '\n'.join(lines[:2])
        
        return clean_reply, emotion
    except Exception as e:
        return "عذراً، لوتس مشغولة شوية الآن 🙄", "sad"

@bot.message_handler(commands=['clear'])
def clear_state(message):
    chat_id = message.chat.id
    user_memory.pop(chat_id, None)
    user_insults.pop(chat_id, None)
    stubborn_users.discard(chat_id)
    special_greeted.discard(chat_id)
    bot.reply_to(message, "تمت إعادة ضبط لوتس 🌸")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    
    if chat_id in stubborn_users:
        return

    first_name = (message.from_user.first_name or "").lower()
    SPECIAL_NAMES = ["اسلام", "ايمن", "الحسن", "الحسين"]
    is_special_name = any(name in first_name for name in SPECIAL_NAMES)

    if is_special_name and chat_id not in special_greeted:
        bot.send_message(chat_id, "إذا هذا أنت يا ع_ط_ا_ي 😏")
        special_greeted.add(chat_id)

    # كشف الشتائم
    bad_words = ["حمار", "كلب", "غبية", "زك", "كلبة", "حمارة", "غبي", "احمق", "زبالة"]
    text_lower = (message.text or "").lower()
    is_insult = any(bad in text_lower for bad in bad_words)

    if is_insult:
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        count = user_insults[chat_id]
        if count >= 2:
            if count == 2:
                bot.send_message(chat_id, "خلاص بقى... سكتت عليك 😒")
            stubborn_users.add(chat_id)
            return

    reply, emotion = get_ai_response(chat_id, message.text, is_special_name=is_special_name)
    
    # بناء الصورة حسب المشاعر
    modifier = EMOTION_MODIFIERS.get(emotion, EMOTION_MODIFIERS["default"])
    appearance = "beautiful shining eyes, pale white skin, short hair colored red white and green like Algerian flag, wearing simple white shirt"
    
    image_prompt = (
        f"anime style, close-up portrait facing camera of 18 year old Algerian girl, {appearance}, "
        f"{modifier}, {emotion} emotion, simple apartment with sea view from window, "
        "highly detailed face, expressive eyes, vibrant anime colors, emotional, masterpiece"
    )
    
    encoded_prompt = urllib.parse.quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={random.randint(1, 1000000)}&width=512&height=512"
    
    try:
        bot.send_photo(chat_id, url, caption=reply)
    except:
        bot.send_message(chat_id, reply)

if __name__ == "__main__":
    bot.remove_webhook()
    print("لوتس شغالة (النسخة الآمنة)...")
    bot.infinity_polling()
