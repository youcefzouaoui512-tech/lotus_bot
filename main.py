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
user_state = {}  # لتتبع حالة المحادثة: "init", "asked_initial", "asked_experience", "normal"

# ==================== شخصية لوتس الجديدة ====================
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
8. التعامل مع الأسماء المحددة: إذا كان اسم المستخدم (إسلام، أيمن، الحسن، أو الحسين)، ردي عليه مباشرة: "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲" (وهذا رد خاص بهم، ولا حاجة لإضافة شيء آخر).
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
        
        # تحديد سطرين كحد أقصى
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
    user_state.pop(chat_id, None)  # إعادة تعيين الحالة
    bot.reply_to(message, "تم تنفيذ الأمر ✅")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id

    # إذا كان المستخدم في قائمة العنيدين، لا نرد نهائياً
    if chat_id in stubborn_users:
        return

    text = message.text or ""
    text_lower = text.lower()

    # ====================== حالة بداية المحادثة ======================
    if chat_id not in user_state:
        # أول رسالة للمستخدم -> نسأل سؤال البداية
        bot.send_message(chat_id, "هل سبق و تحدثت معي من قبل...أو ربما تحدثت مع احدى اصداراتي السابقة...لمن هدا لا يهم الأن أليس كدلك.....؟")
        user_state[chat_id] = "asked_initial"
        return

    # ====================== الحالة: في انتظار الإجابة على سؤال البداية ======================
    if user_state[chat_id] == "asked_initial":
        # تحليل الإجابة (نعم / لا)
        if any(word in text_lower for word in ["نعم", "اي", "اكيد", "طبعا", "اجل", "yeah", "yes"]):
            # قال نعم -> نسأله عن تجربته
            bot.send_message(chat_id, "وما هي تجربتك معي؟")
            user_state[chat_id] = "asked_experience"
            return
        elif any(word in text_lower for word in ["لا", "مش", "ما", "لأ", "no", "nah"]):
            # قال لا -> نرد بجملة مخصصة وننهي المقدمة
            bot.send_message(chat_id, "اسفة أنا أخلط بين الأبعاد ربما دلك بسبب تفاعلي طويلا مع شخصيتك من البعد 106 هاها...ها....أصبح الوضع غريبا 🥲")
            user_state[chat_id] = "normal"
            # نضيف محادثة إلى الذاكرة (حتى يعتبر المستخدم معروفاً من الآن)
            user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
            user_memory[chat_id].append({"role": "user", "content": text})
            # نرد على السؤال الأصلي بشكل طبيعي (يمكن أن نمر إلى الأسفل بعد إرسال الرد الخاص، لكننا سنعود هنا)
            # سوف نمر إلى الأسفل بعد انتهاء الحالة، لكننا نريد إرسال رد عادي أيضاً؟ المستخدم قال "وتستمر المحادثة بشكل طبيعي"، لذا نكمل.
            # ولكن يجب أن نتأكد من عدم إعادة السؤال. سنقوم بتعيين الحالة normal ثم نستمر في تنفيذ بقية الكود للتعامل مع هذه الرسالة كرد عادي.
            # لكننا أرسلنا بالفعل رداً، لذا لا نريد إرسال رد إضافي الآن. لذا سنعود بعد إرسال الرد الخاص، وسنقوم بمعالجة هذه الرسالة كجزء من المحادثة في المرة القادمة.
            # الخيار الأفضل: بعد إرسال رد "لا"، نضيف الرد للذاكرة ثم نكمل للحصول على رد من الذكاء الاصطناعي (لأننا لم نرد على المحتوى الأصلي).
            # سنسمح للمتابعة بالدخول إلى الأسفل بعد الانتهاء من هذا الفرع.
            # ولكن يجب أن نضع في الاعتبار أننا لو استمرينا، فسيعالج الرد العادي ويصدر صورة/نص، وقد يكون ذلك زائداً.
            # لذا سنقوم بإرسال رد "لا" ثم نعود (لا نمر للأسفل). وهكذا ننهي المقدمة، وفي المرة القادمة سيكون البوت في حالة normal ويتعامل مع الرسائل العادية.
            # لكن المستخدم قال "وتستمر المحادثة بشكل طبيعي" بعد إرسال الرد، أي أن البوت يجب أن يرد على السؤال الأصلي أيضاً؟ لا، لأن البوت سأل سؤالاً وأجاب المستخدم، فالبوت رد بشكل مناسب، وبهذا تنتهي المقدمة. لا حاجة لرد إضافي.
            # لذا نكتفي بإرسال الرد الخاص ونعود.
            return
        else:
            # إذا لم نفهم الجواب، نعيد السؤال
            bot.send_message(chat_id, "لم أفهم، هل سبق لك التحدث معي؟ (قل نعم أو لا)")
            # لا نغير الحالة، نبقى في انتظار إجابة واضحة
            return

    # ====================== الحالة: في انتظار تقييم التجربة (إذا قال نعم سابقاً) ======================
    if user_state[chat_id] == "asked_experience":
        # نحلل رسالة المستخدم هل هي إيجابية أم سلبية
        positive_words = ["جيد", "رائع", "ممتاز", "حلو", "جميل", "ممتعة", "لطيف", "nice", "good", "great", "excellent", "wonderful"]
        negative_words = ["سيء", "ممل", "سيئ", "سيئة", "لا يعجبني", "مزعج", "بائس", "bad", "terrible", "awful", "boring", "disappointing"]

        is_positive = any(word in text_lower for word in positive_words)
        is_negative = any(word in text_lower for word in negative_words)

        if is_positive:
            bot.send_message(chat_id, "شكراً لك يا صديقي، أنا سعيدة بذلك 😊")
        elif is_negative:
            bot.send_message(chat_id, "حسنا...لم يكن هدا متوقعا هاها...ها حسنا لا يهم 😐")
        else:
            # إذا لم نستطع التحديد، نعطي رداً محايداً
            bot.send_message(chat_id, "فهمت، شكراً على مشاركتك 😊")

        user_state[chat_id] = "normal"
        # نضيف المحادثة إلى الذاكرة
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
        user_memory[chat_id].append({"role": "user", "content": text})
        # لا نرد على المحتوى الأصلي الآن، فقط انتهت المقدمة
        return

    # ====================== من هنا فصاعداً: حالة "normal" (المحادثة العادية) ======================

    # ====================== الأسماء الخاصة (إسلام، أيمن، الحسن، الحسين) ======================
    first_name = (message.from_user.first_name or "").lower()
    SPECIAL_NAMES = ["اسلام", "ايمن", "الحسن", "الحسين"]
    is_special_name = any(name in first_name for name in SPECIAL_NAMES)

    if is_special_name and chat_id not in special_greeted:
        bot.send_message(chat_id, "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲")
        special_greeted.add(chat_id)

    # ====================== كشف سؤال المستخدم عن المطور ======================
    developer_keywords = ["مطور", "صانع", "يوسف", "من صنعك", "من أنشأك", "من برمجك", "من صنعك"]
    if any(keyword in text_lower for keyword in developer_keywords):
        # إذا كان المستخدم معروفاً (لديه ذاكرة سابقة) نرسل الرد الثاني، وإلا الأول
        if chat_id in user_memory and len(user_memory[chat_id]) > 1:  # وجدنا محادثة سابقة
            bot.send_message(chat_id, "يا أبله المطور صديقك 😂 لا تعبث معي")
        else:
            bot.send_message(chat_id, "لقد أخبرني المطور عنك 😄 يالك من مسكين يعاني من جفاف عاطفي 🥲")
        # نعود ولا نمر على الذكاء الاصطناعي
        return

    # ====================== كشف الشتائم ======================
    bad_words = ["حمار", "كلب", "غبية", "زك", "كلبة", "حمارة", "غبي", "احمق", "زبالة"]
    is_insult = any(bad in text_lower for bad in bad_words)

    if is_insult:
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        count = user_insults[chat_id]
        if count == 1:
            # الرد الحرفي على الشتمة الأولى (دون الرجوع للذكاء الاصطناعي)
            bot.send_message(chat_id, "احشم راك كبير 🫤")
            return
        elif count >= 2:
            if count == 2:
                bot.send_message(chat_id, "يا خسارة في عقلك 😒")
                bot.send_message(chat_id, "... 🤐")  # الرمز الصامت
            stubborn_users.add(chat_id)
            return

    # ====================== الرد العادي (بالصورة والنص) ======================
    reply, emotion = get_ai_response(chat_id, text)
    
    # بناء الصورة حسب المشاعر
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

if __name__ == "__main__":
    bot.remove_webhook()
    print("لوتس شغالة (النسخة المحدثة)...")
    bot.infinity_polling()
