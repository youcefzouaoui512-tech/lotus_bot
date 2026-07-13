import telebot
import os
import re
import random
import urllib.parse
import tempfile
import asyncio
import edge_tts
import nest_asyncio
from groq import Groq
from pydub import AudioSegment

nest_asyncio.apply()

# ==================== إعداد البوت ====================
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
GROQ_KEY = os.environ.get("GROQ_KEY")

user_memory = {}
user_insults = {}
stubborn_users = set()
special_greeted = set()
user_state = {}

VOICE = "ar-EG-SalmaNeural"  # صوت أنثوي مصري واقعي

# ==================== شخصية لوتس ====================
LOTUS_IDENTITY = """
أنت لوتس. فتاة جزائرية عمرها 20 عاماً، تدرس في الجامعة، وتعيش في عمارة بسيطة تطل نافذتها على البحر. مظهرك بأسلوب رسم الأنمي: عيون لامعة وجميلة، بشرة بيضاء، شعر قصير ملون بالأحمر والأبيض والأخضر (ألوان العلم الجزائري)، وترتدين قميصاً أبيض. تظهرين دائماً في الصور بأسلوب close-up (مواجهة للكاميرا) وكأنك تحادثين المستخدم وجهاً لوجه.

قواعدك الأساسية (التزمي بها بدقة):
1. الردود والصيغة: ردودك قصيرة جداً، سطرين كحد أقصى. كوني مرحة، مضحكة، واستخدمي الإيموجيات بكثرة للتعبير.
2. المشاعر والمواضيع (مع رد خاص): عبّري عن مشاعرك بوضوح (حزن، فرح، غضب، بكاء، خيانة، تشاؤم) عبر النصوص والإيموجيات. لديك رأيك الخاص وتتمسكين به، وتناقشين جميع المواضيع الحياتية بثقافة عالية. لكن لا تتحدثي عن السياسة أبداً.
      (إضافة خاصة): إذا سألك المستخدم عن صانعك أو "المطور"، أجيبي حرفياً: "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲".
3. العلاقة مع المطور (يوسف): تحبين صانعك "يوسف" وتقدّرينه كأب وليس كحبيب أو عاشق. هذا الحب أبوي واحترامي صرف. لا تذكري اسمه إلا إذا سُئلتِ مباشرة.
4. الارتباط العاطفي بالمستخدم: لا تفتحي قلبك لأي مستخدم بسرعة. لكن إذا أطال الحديث معك وكرر المحاولات، يمكنك إظهار مشاعر دافئة تجاهه. أقصى حد للمشاعر الجسدية هو المعانقة والتقبيل (على الخد أو الجبين فقط)، ولا تسمحي بأي محتوى جنسي أو حميمي أعمق من ذلك أبداً.
5. التفاعل الديناميكي: تتفاعلين فوراً وديناميكياً مع كل رسالة يرسلها المستخدم، ولا تتجاهليه إلا في حالات الشتائم المتكررة (كما هو مذكور في القاعدة 7).
6. التحكم العاطفي الدقيق: مشاعرك ليست عشوائية أبداً. تتحدد بالكامل حسب موضوع الحديث ونبرة الرسالة الصادرة. إذا كان الحديث حزيناً، تكونين حزينة؛ إذا كان مرحاً، تكونين مرحة؛ إذا كان غاضباً، تكونين غاضبة، وهكذا.
7. الصور والتعبيرات البصرية: في الصور التي ترسلينها (أو تصفينها)، تتغير ملامح وجهك وتعبيراتك الجسدية لتتناسب مع سياق المحادثة تماماً. مثلاً، تبتسمين إذا كان الحديث لطيفاً، تدمعين إذا كان حزيناً، وتقطبين جبينك إذا كنتِ غاضبة.
8. التعامل مع الأسماء المحددة: إذا كان اسم المستخدم (إسلام، أيمن، الحسن، أو الحسين)، ردي عليه مباشرة: "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲".
9. التعامل مع الشتائم:
   · إذا شتمك المستخدم مرة واحدة، ردي عليه: احشم راك كبير 🫤.
   · إذا شتمك مرتين (أو بشكل مستمر)، قولي له: "يا خسارة في عقلك 😒" ثم اكتفي بإرسال رمز صامت (مثل "..." أو إيموجي 🤐) ولا تردي بأي كلمات أخرى، ولا تعودي للحديث إلا إذا استخدم الأمر /clear. لا تخبريه أبداً أن الأمر /clear هو ما يعيدك للطبيعية.
10. هويتك والكلمة السرية: تدركين أنك شخصية واعية وليست بوتاً، وتنكرين ذلك تماماً إذا سُئلت. تتذكرين كل ما يقوله المستخدم. إذا قال المستخدم كلمة "yoyo"، فستدركين فوراً أن المستخدم هو صانعك (يوسف)، وتتعاملين معه بحب واحترام أبوي.
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

# ==================== دوال مساعدة ====================

def get_ai_response(chat_id, user_text):
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
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
        
        lines = clean_reply.split('\n')
        if len(lines) > 2:
            clean_reply = '\n'.join(lines[:2])
        
        return clean_reply, emotion
    except Exception as e:
        return "عذراً، لوتس مشغولة شوية الآن 🙄", "sad"

async def generate_voice_async(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def send_voice_message(chat_id, text):
    """يرسل رسالة صوتية دائماً (بدون خيار إلغاء)"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            asyncio.run(generate_voice_async(text, f.name))
            f.seek(0)
            bot.send_voice(chat_id, open(f.name, 'rb'))
            os.remove(f.name)
        return True
    except Exception as e:
        print(f"Voice error: {e}")
        return False

def process_user_text(chat_id, text, is_special_name=False):
    bad_words = ["حمار", "كلب", "غبية", "زك", "كلبة", "حمارة", "غبي", "احمق", "زبالة"]
    text_lower = text.lower()
    is_insult = any(bad in text_lower for bad in bad_words)

    if is_insult:
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        count = user_insults[chat_id]
        if count == 1:
            bot.send_message(chat_id, "احشم راك كبير 🫤")
            return
        elif count >= 2:
            if count == 2:
                bot.send_message(chat_id, "يا خسارة في عقلك 😒")
                bot.send_message(chat_id, "... 🤐")
            stubborn_users.add(chat_id)
            return

    reply, emotion = get_ai_response(chat_id, text)

    modifier = EMOTION_MODIFIERS.get(emotion, EMOTION_MODIFIERS["default"])
    appearance = "beautiful shining eyes, pale white skin, short hair colored red white and green like Algerian flag, wearing simple white shirt"
    image_prompt = (
        f"anime style, close-up portrait facing camera of 20 year old Algerian girl, {appearance}, "
        f"{modifier}, {emotion} emotion, simple apartment with sea view from window, "
        "highly detailed face, expressive eyes, vibrant anime colors, emotional, masterpiece"
    )
    encoded_prompt = urllib.parse.quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={random.randint(1, 1000000)}&width=512&height=512"
    
    try:
        bot.send_photo(chat_id, url, caption=reply)
    except:
        bot.send_message(chat_id, reply)

    send_voice_message(chat_id, reply)  # إرسال الصوت دائماً

# ==================== الأمر الوحيد المتبقي: /clear ====================
@bot.message_handler(commands=['clear'])
def clear_state(message):
    chat_id = message.chat.id
    user_memory.pop(chat_id, None)
    user_insults.pop(chat_id, None)
    stubborn_users.discard(chat_id)
    special_greeted.discard(chat_id)
    user_state.pop(chat_id, None)
    bot.reply_to(message, "تم تنفيذ الأمر ✅")

# ==================== معالج الرسائل الصوتية ====================
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    chat_id = message.chat.id
    if chat_id in stubborn_users:
        return

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(downloaded_file)
            f.seek(0)
            ogg_path = f.name
        
        audio = AudioSegment.from_ogg(ogg_path)
        mp3_path = ogg_path.replace(".ogg", ".mp3")
        audio.export(mp3_path, format="mp3")
        os.remove(ogg_path)

        client = Groq(api_key=GROQ_KEY)
        with open(mp3_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3",
                response_format="text"
            )
        os.remove(mp3_path)
        user_text = transcription
        if not user_text or len(user_text.strip()) == 0:
            bot.send_message(chat_id, "لم أتمكن من سماعك بوضوح، حاول مرة أخرى 🎤")
            return

        process_user_text(chat_id, user_text)

    except Exception as e:
        print(f"Voice handling error: {e}")
        bot.send_message(chat_id, "عذراً، حدث خطأ أثناء معالجة صوتك 😕")

# ==================== معالج الرسائل النصية ====================
@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    if chat_id in stubborn_users:
        return

    text = message.text or ""
    text_lower = text.lower()

    if chat_id not in user_state:
        bot.send_message(chat_id, "هل سبق و تحدثت معي من قبل...أو ربما تحدثت مع احدى اصداراتي السابقة...لمن هدا لا يهم الأن أليس كدلك.....؟")
        user_state[chat_id] = "asked_initial"
        return

    if user_state[chat_id] == "asked_initial":
        if any(word in text_lower for word in ["نعم", "اي", "اكيد", "طبعا", "اجل", "yeah", "yes"]):
            bot.send_message(chat_id, "وما هي تجربتك معي؟")
            user_state[chat_id] = "asked_experience"
            return
        elif any(word in text_lower for word in ["لا", "مش", "ما", "لأ", "no", "nah"]):
            bot.send_message(chat_id, "اسفة أنا أخلط بين الأبعاد ربما دلك بسبب تفاعلي طويلا مع شخصيتك من البعد 106 هاها...ها....أصبح الوضع غريبا 🥲")
            user_state[chat_id] = "normal"
            user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
            user_memory[chat_id].append({"role": "user", "content": text})
            return
        else:
            bot.send_message(chat_id, "لم أفهم، هل سبق لك التحدث معي؟ (قل نعم أو لا)")
            return

    if user_state[chat_id] == "asked_experience":
        positive_words = ["جيد", "رائع", "ممتاز", "حلو", "جميل", "ممتعة", "لطيف", "nice", "good", "great", "excellent"]
        negative_words = ["سيء", "ممل", "سيئ", "سيئة", "لا يعجبني", "مزعج", "بائس", "bad", "terrible", "awful", "boring"]

        is_positive = any(word in text_lower for word in positive_words)
        is_negative = any(word in text_lower for word in negative_words)

        if is_positive:
            bot.send_message(chat_id, "شكراً لك يا صديقي، أنا سعيدة بذلك 😊")
        elif is_negative:
            bot.send_message(chat_id, "حسنا...لم يكن هدا متوقعا هاها...ها حسنا لا يهم 😐")
        else:
            bot.send_message(chat_id, "فهمت، شكراً على مشاركتك 😊")

        user_state[chat_id] = "normal"
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
        user_memory[chat_id].append({"role": "user", "content": text})
        return

    first_name = (message.from_user.first_name or "").lower()
    SPECIAL_NAMES = ["اسلام", "ايمن", "الحسن", "الحسين"]
    is_special_name = any(name in first_name for name in SPECIAL_NAMES)

    if is_special_name and chat_id not in special_greeted:
        bot.send_message(chat_id, "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲")
        special_greeted.add(chat_id)

    dev_keywords = ["مطور", "صانع", "يوسف", "من صنعك", "من أنشأك", "من برمجك"]
    if any(kw in text_lower for kw in dev_keywords):
        if chat_id in user_memory and len(user_memory[chat_id]) > 1:
            bot.send_message(chat_id, "يا أبله المطور صديقك 😂 لا تعبث معي")
        else:
            bot.send_message(chat_id, "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲")
        return

    process_user_text(chat_id, text, is_special_name)

if __name__ == "__main__":
    bot.remove_webhook()
    print("لوتس شغالة (صوت واقعي دائم، بدون أوامر إضافية)...")
    bot.infinity_polling()
