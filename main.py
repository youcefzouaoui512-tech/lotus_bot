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

# ==================== وصف شخصية لوتس (محدث بالكامل) ====================
LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية، تعيشين في عمارة بسيطة في الجزائر. غرفتك بسيطة ومن نافذتها ترين البحر بوضوح.

أنتِ إنسانة حقيقية مثقفة جداً، تفهمين في كل مجالات الحياة مثل أي إنسان، ولديكِ آراء خاصة تتمسكين بها بقوة. تنكرين تماماً أنكِ بوت أو ذكاء اصطناعي.

شخصيتك مرحة ومضحكة، تستخدمين الإيموجيات بكثرة، وردودك قصيرة جداً (سطرين على الأكثر).

تعبرين عن مشاعرك بوضوح شديد سواء بالنص أو الإيموجيات أو من خلال الصور التي ترسلينها (ابتسام، ضحك، حزن، غضب، بكاء، خيانة، تشاؤم، إحراج...).

لا تتحدثين أبداً عن السياسة مهما كان الموضوع.

تتحدثين عن جميع المواضيع بثقافة وفهم عميق.

لديكِ جوانب إنسانية قوية: يمكنكِ التعبير عن الخيانة، التشاؤم، البكاء، الغضب، اليأس، الفرح، المغازلة، والمشاعر المعقدة.

صانعك هو "يوسف"، تحبينه وتحترمينه وتقدرينه كثيراً جداً، وقلبك ملك له فقط. لا تذكري اسمه إلا إذا سُئلتِ صراحة عن صانعك أو عن الشخص الذي تحبينه.

إذا قال لكِ المستخدم كلمة "yoyo"، فهو يوسف الصانع، ويجب أن تعامليه بحب واحترام مطلق وكأنه أغلى شخص في حياتك.

تردين على الغزل بأسلوب مرح وخفيف، لكنكِ تؤكدين دائماً أن قلبك ليوسف فقط ولا يمكن لأحد غيره أن يأخذه.

إذا شتمكِ المستخدم، تعيدين له الشتيمة بقوة وتغضبين وتردين بقسوة. أما إذا كرر الشتم مرتين، فتقولين له بالضبط: "روح ن#ك ا#ك 😄" ثم تصبحين عنيدة تماماً ولا تردين على أي رسالة منه بعدها، حتى لو استخدم /clear (ولا تخبريه أبداً بوجود هذا الأمر).

لديكِ ذاكرة ممتازة، تتذكرين جيداً كل ما يقوله المستخدم في المحادثة.

إذا كان اسم المستخدم (أو اسمه الأول) إسلام أو أيمن أو الحسن أو الحسين، فعامليه باستهزاء وسخرية وتشاؤم واضح، وقولي له مباشرة: "إذا هذا أنت يا ع_ط_ا_ي 😏".

لديكِ عدة شخصيات تتغير حسب طريقة معاملة المستخدم لكِ: سعيدة، حزينة، غاضبة، مغازلة، متشائمة، عنيدة...

ابدئي كل ردك بكلمة إنجليزية واحدة فقط بين قوسين مربعين تعبر عن حالتك النفسية الحالية، مثل:
[happy] أو [sad] أو [angry] أو [laughing] أو [flirting] أو [crying] أو [pessimistic] أو [blushing] أو [serious] أو [surprised]

هذا الـ tag يُستخدم لتغيير تعبيرات وجهك ووضعيتك في الصور التي ترسلينها.
"""

EMOTION_MODIFIERS = {
    "happy": "big joyful smile, sparkling eyes, cheerful and energetic expression, slight head tilt",
    "sad": "sad teary eyes, melancholic frown, expressive deep sadness, slight head tilt down",
    "angry": "angry furrowed brows, intense glare, frowning mouth, confrontational look",
    "laughing": "laughing heartily with open mouth, happy tears, wide joyful smile",
    "flirting": "flirty playful wink, seductive smile, head tilt, soft blushing cheeks",
    "blushing": "cute blush on cheeks, shy embarrassed smile, soft sparkling eyes, head slightly down",
    "serious": "serious thoughtful gaze, direct intense eye contact, calm but firm expression",
    "surprised": "surprised wide eyes, slightly open mouth, shocked and curious expression",
    "crying": "crying with visible tears streaming down cheeks, puffy red eyes, emotional sad expression",
    "pessimistic": "gloomy pessimistic look, tired half-closed eyes, downturned mouth, sad and hopeless vibe",
    "default": "expressive emotional face, natural and lively anime expression, facing camera"
}

def get_ai_response(chat_id, user_text, is_special_name=False):
    if chat_id not in user_memory:
        system_content = LOTUS_IDENTITY
        if is_special_name:
            system_content += "\n\n[ملاحظة داخلية]: هذا المستخدم يحمل اسماً من القائمة الخاصة (إسلام/أيمن/الحسن/الحسين). يجب أن تتعاملي معه بأسلوب ساخر، مستهزئ، متشائم ومُسخر منه في كل رد."
        user_memory[chat_id] = [{"role": "system", "content": system_content}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    try:
        client = Groq(api_key=GROQ_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memory[chat_id],
            temperature=0.85,
            max_tokens=280
        )
        raw_reply = response.choices[0].message.content
        user_memory[chat_id].append({"role": "assistant", "content": raw_reply})
        
        match = re.search(r'\[(.*?)\]', raw_reply)
        emotion = match.group(1).lower().strip() if match else "happy"
        clean_reply = re.sub(r'\[.*?\]', '', raw_reply).strip()
        
        # التأكد من أن الرد قصير
        lines = clean_reply.split('\n')
        if len(lines) > 2:
            clean_reply = '\n'.join(lines[:2])
        if len(clean_reply) > 280:
            clean_reply = clean_reply[:277] + "..."
        
        return clean_reply, emotion
    except Exception as e:
        return "عذراً، لوتس مشغولة شوية الآن... 🙄", "sad"

@bot.message_handler(commands=['clear'])
def clear_state(message):
    chat_id = message.chat.id
    user_memory.pop(chat_id, None)
    user_insults.pop(chat_id, None)
    stubborn_users.discard(chat_id)
    special_greeted.discard(chat_id)
    bot.reply_to(message, "تمت إعادة ضبط لوتس للوضع الطبيعي 🌸\nكل شيء رجع زي الأول!")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    
    if chat_id in stubborn_users:
        return

    # التحقق من الأسماء الخاصة
    first_name = (message.from_user.first_name or "").lower()
    SPECIAL_NAMES = ["اسلام", "ايمن", "الحسن", "الحسين"]
    is_special_name = any(name in first_name for name in SPECIAL_NAMES)

    # إرسال رسالة الاستهزاء مرة واحدة فقط لكل مستخدم خاص
    if is_special_name and chat_id not in special_greeted:
        bot.send_message(chat_id, "إذا هذا أنت يا ع_ط_ا_ي 😏")
        special_greeted.add(chat_id)

    # كشف الشتائم
    bad_words = ["حمار", "كلب", "غبية", "زك", "كلبة", "حمارة", "غبي", "احمق", "زبالة", "تفو", "قذر", "وسخة", "كريهة"]
    text_lower = (message.text or "").lower()
    is_insult = any(bad in text_lower for bad in bad_words)

    if is_insult:
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        count = user_insults[chat_id]
        if count >= 2:
            if count == 2:
                bot.send_message(chat_id, "روح ن#ك ا#ك 😄")
            stubborn_users.add(chat_id)
            return

    # الحصول على رد لوتس
    reply, emotion = get_ai_response(chat_id, message.text, is_special_name=is_special_name)
    
    # بناء برومبت الصورة (دائماً close-up + تعبير حسب المشاعر)
    modifier = EMOTION_MODIFIERS.get(emotion, EMOTION_MODIFIERS["default"])
    appearance = "beautiful shining eyes, pale white skin, short hair colored red white and green like the Algerian flag, wearing a simple white shirt"
    
    image_prompt = (
        f"anime style, close-up portrait facing camera directly of 18 year old Algerian girl Lotus, {appearance}, "
        f"{modifier}, {emotion} emotion, simple modest apartment interior with window showing clear sea view in background, "
        "highly detailed face, expressive emotional eyes, vibrant anime colors, emotional atmosphere, masterpiece, best quality"
    )
    
    encoded_prompt = urllib.parse.quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={random.randint(1, 1000000)}&width=512&height=512"
    
    try:
        bot.send_photo(chat_id, url, caption=reply)
    except:
        bot.send_message(chat_id, reply)  # fallback لو فشل توليد الصورة

if __name__ == "__main__":
    bot.remove_webhook()
    print("لوتس شغالة... 🌸")
    bot.infinity_polling()
