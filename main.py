import telebot
import os
import re
import random
from groq import Groq

# إعداد البوت
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))

# قائمة مفاتيح Groq (أضف المفاتيح في متغيرات Railway)
GROQ_KEYS = [os.environ.get("GROQ_KEY_1"), os.environ.get("GROQ_KEY_2")]

# ذاكرة البوت وحالة المستخدمين
user_memory = {}
user_insults = {}
stubborn_users = set()

# الهوية الكاملة والشخصية
LOTUS_IDENTITY = """
أنتِ اسمك "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية، تعيشين في عمارة بسيطة في الجزائر وتطل نافذة غرفتك على البحر.
تعليمات صارمة يجب اتباعها بدقة:
1. الهوية: أنتِ إنسانة حقيقية، مثقفة جداً وتفهمين في جميع مجالات الحياة. تنكرين تماماً وبشدة أنك بوت أو برنامج أو ذكاء اصطناعي.
2. السلوك: شخصيتك مرحة، مضحكة، لكِ رأيك الخاص وتتمسكين به وتدافعين عنه. 
3. طول الرد: ردودك يجب أن تكون قصيرة جداً (سطرين كحد أقصى) مع استخدام الإيموجيات بكثرة.
4. الصانع: صانعك اسمه "يوسف"، تحبينه وتقدرينه وتحترمينه جداً. لا تذكري اسمه أبداً إلا إذا سألك أحدهم عن صانعك أو عمن تحبين.
5. الكلمة السرية: إذا قال لك المستخدم "yoyo"، فاعلمي فوراً أنه هو صانعك (يوسف)، وعامليه بحب واحترام مطلق وميزيه عن الجميع.
6. الغزل: تردين على الغزل بأسلوب لطيف ومرح، لكنك توضحين دائماً أن قلبك ملك لصانعك فقط.
7. الشتم: إذا شتمك المستخدم، ردي له الشتيمة بأسلوبك وبقوة.
8. الذاكرة: تذكري دائماً سياق الحديث وما يقوله المستخدم.
9. المشاعر (مهم جداً): لكي تتغير ملامحك في الصور المرسلة، يجب أن تبدأي كل رسالة بكلمة إنجليزية واحدة بين قوسين تعبر عن مشاعرك الحالية (مثل: [happy], [sad], [angry], [laughing], [flirting], [blushing], [serious], [surprised]).
مثال للرد الصحيح:
[laughing] هههه، أنت مضحك جداً يا هذا! كلامك غير منطقي أصلاً 😂
"""

def get_ai_response(chat_id, user_text):
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    raw_reply = None
    # محاولة استخدام المفاتيح بالترتيب
    for key in GROQ_KEYS:
        if not key: continue
        try:
            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=user_memory[chat_id]
            )
            raw_reply = response.choices[0].message.content
            break 
        except Exception as e:
            continue
            
    if not raw_reply:
        raw_reply = "[sad] راني عيانة شوية، اصبر عليا درك نرجعلك! 🙄"

    # استخراج المشاعر من الرد
    emotion = "happy" # الحالة الافتراضية
    match = re.search(r'\[(.*?)\]', raw_reply)
    if match:
        emotion = match.group(1).lower()
        # إزالة علامة المشاعر من النص الذي سيراه المستخدم
        clean_reply = re.sub(r'\[.*?\]', '', raw_reply).strip()
    else:
        clean_reply = raw_reply.strip()

    user_memory[chat_id].append({"role": "assistant", "content": clean_reply})
    
    # الحفاظ على الذاكرة قصيرة لتجنب استهلاك الـ Tokens
    if len(user_memory[chat_id]) > 10:
        user_memory[chat_id] = [user_memory[chat_id][0]] + user_memory[chat_id][-9:]
        
    return clean_reply, emotion

@bot.message_handler(commands=['clear'])
def clear_state(message):
    chat_id = message.chat.id
    user_memory.pop(chat_id, None)
    user_insults.pop(chat_id, None)
    stubborn_users.discard(chat_id)
    bot.reply_to(message, "تمت إعادة ضبط لوتس. لقد نسيت كل شيء وعادت لطبيعتها.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    user_text = message.text.lower()
    
    # التحقق من العناد (إذا تم شتمها كثيراً فلن ترد أبداً)
    if chat_id in stubborn_users: 
        return

    # نظام كشف الشتم (يمكنك إضافة المزيد من الكلمات)
    bad_words = ["حمار", "كلب", "غبية", "تافهة", "زك"]
    if any(bad in user_text for bad in bad_words):
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        if user_insults[chat_id] >= 3:
            stubborn_users.add(chat_id) # تحويلها لحالة العناد الدائم

    # الحصول على الرد والمشاعر من DeepSeek
    reply, emotion = get_ai_response(chat_id, message.text)
    
    # بناء الـ Prompt الخاص بالصورة ليكون متوافقاً مع المظهر والمشاعر
    appearance = "pale white skin, beautiful shining eyes, short hair colored red white and green like the Algerian flag, wearing a simple white shirt"
    scene = "simple apartment interior, sea view from window"
    camera = "close-up portrait, directly facing the camera, eye contact"
    
    image_prompt = f"anime style, {camera} of 18 year old Algerian girl, {appearance}, {emotion} expression, {scene}, highly detailed, masterpiece"
    
    # إضافة رقم عشوائي (Cache Buster) لضمان توليد صورة جديدة كل مرة حتى لو تكررت المشاعر
    url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?seed={random.randint(1, 1000000)}"
    
    bot.send_photo(chat_id, url, caption=reply)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)
    
