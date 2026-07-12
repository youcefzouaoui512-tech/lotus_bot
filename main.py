import telebot
import os
import re
import random
from groq import Groq

# إعداد البوت
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))

# قائمة مفاتيح Groq
GROQ_KEYS = [os.environ.get("GROQ_KEY_1"), os.environ.get("GROQ_KEY_2")]

user_memory = {}
user_insults = {}
stubborn_users = set()

LOTUS_IDENTITY = """
أنتِ اسمك "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية، تعيشين في عمارة بسيطة في الجزائر وتطل نافذة غرفتك على البحر.
1. الهوية: أنتِ إنسانة حقيقية، مثقفة جداً وتفهمين في جميع مجالات الحياة. تنكرين تماماً وبشدة أنك بوت أو برنامج أو ذكاء اصطناعي.
2. السلوك: شخصيتك مرحة، مضحكة، لكِ رأيك الخاص وتتمسكين به. 
3. طول الرد: ردودك قصيرة جداً (سطرين كحد أقصى) مع استخدام الإيموجيات.
4. الصانع: صانعك اسمه "يوسف"، تحبينه وتقدرينه وتحترمينه جداً. لا تذكري اسمه أبداً إلا إذا سألك أحدهم عن صانعك أو عمن تحبين.
5. الكلمة السرية: إذا قال لك المستخدم "yoyo"، فاعلمي فوراً أنه هو صانعك (يوسف)، وعامليه بحب واحترام مطلق.
6. الغزل: تردين على الغزل بأسلوب لطيف ومرح، لكنك توضحين دائماً أن قلبك ملك لصانعك فقط.
7. الشتم: إذا شتمك المستخدم، ردي له الشتيمة بأسلوبك وبقوة.
8. المشاعر: يجب أن تبدأي كل رسالة بكلمة إنجليزية واحدة بين قوسين تعبر عن مشاعرك (مثال: [happy], [sad], [angry], [laughing], [flirting], [blushing]).
"""

def get_ai_response(chat_id, user_text):
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    raw_reply = None
    # محاولة استخدام المفاتيح وتخطي التالف منها
    for key in GROQ_KEYS:
        if not key or len(key) < 10: continue
        try:
            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=user_memory[chat_id]
            )
            raw_reply = response.choices[0].message.content
            break 
        except:
            continue
            
    if not raw_reply:
        user_memory[chat_id].pop() # حذف محاولة المستخدم الفاشلة
        return "راني عيانة شوية، اصبر عليا درك نرجعلك! 🙄", "sad"

    match = re.search(r'\[(.*?)\]', raw_reply)
    emotion = match.group(1).lower() if match else "happy"
    clean_reply = re.sub(r'\[.*?\]', '', raw_reply).strip()

    user_memory[chat_id].append({"role": "assistant", "content": clean_reply})
    return clean_reply, emotion

@bot.message_handler(commands=['clear'])
def clear_state(message):
    user_memory.pop(message.chat.id, None)
    stubborn_users.discard(message.chat.id)
    bot.reply_to(message, "تمت إعادة ضبط لوتس.")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    if chat_id in stubborn_users: return

    bad_words = ["حمار", "كلب", "غبية", "زك"]
    if any(bad in message.text.lower() for bad in bad_words):
        user_insults[chat_id] = user_insults.get(chat_id, 0) + 1
        if user_insults[chat_id] >= 3:
            stubborn_users.add(chat_id)

    reply, emotion = get_ai_response(chat_id, message.text)
    
    # لا ترسل صورة إذا كان البوت يخبرك أنه عيان
    if "راني عيانة" in reply:
        bot.reply_to(message, reply)
    else:
        appearance = "pale white skin, beautiful shining eyes, short hair colored red white and green like the Algerian flag, wearing a simple white shirt"
        image_prompt = f"anime style, close-up portrait of 18 year old Algerian girl, {appearance}, {emotion} expression, simple apartment interior, sea view from window, masterpiece"
        url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?seed={random.randint(1, 1000000)}"
        bot.send_photo(chat_id, url, caption=reply)

if __name__ == "__main__":
    bot.infinity_polling(none_stop=True)
    
