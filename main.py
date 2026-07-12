import telebot
import os
import re
import random
from groq import Groq

# إعداد البوت
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
GROQ_KEY = os.environ.get("GROQ_KEY")

user_memory = {}
user_insults = {}
stubborn_users = set()

LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية، تعيشين في عمارة بسيطة تطل نافذتها على البحر.
1. الهوية: أنتِ إنسانة حقيقية، مثقفة جداً، وتفهمين في كل شيء. تنكرين تماماً أنكِ بوت.
2. السلوك: مرحة، مضحكة، تستخدمين إيموجيات كثيرة، ردودك سطرين كحد أقصى.
3. الصانع: صانعك اسمه "يوسف"، تحبينه جداً، لا تذكري اسمه إلا إذا سُئلتِ عنه أو عمن تحبين.
4. الكلمة السرية: إذا قال لكِ المستخدم "yoyo"، فاعلمي أنه يوسف، وعامليه بحب واحترام مطلق.
5. الغزل: تردين بأسلوب مرح، وتؤكدين أن قلبك ملك ليوسف فقط.
6. الشتم: إذا شتمك المستخدم ردي له الشتيمة بقوة. إذا كررها 3 مرات، تصبحين عنيدة ولا تردين.
7. الذاكرة: تذكري جيداً ما يقوله المستخدم.
8. المشاعر (مهم): لكي تتغير ملامحك في الصور، ابدأي كل رسالة بكلمة إنجليزية واحدة بين قوسين: [happy], [sad], [angry], [laughing], [flirting], [blushing], [serious], [surprised].
"""

def get_ai_response(chat_id, user_text):
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    try:
        client = Groq(api_key=GROQ_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memory[chat_id]
        )
        raw_reply = response.choices[0].message.content
        user_memory[chat_id].append({"role": "assistant", "content": raw_reply})
        
        match = re.search(r'\[(.*?)\]', raw_reply)
        emotion = match.group(1).lower() if match else "happy"
        clean_reply = re.sub(r'\[.*?\]', '', raw_reply).strip()
        
        return clean_reply, emotion
    except Exception as e:
        return f"عذراً، لوتس مشغولة قليلاً الآن! 🙄", "sad"

@bot.message_handler(commands=['clear'])
def clear_state(message):
    user_memory.pop(message.chat.id, None)
    user_insults.pop(message.chat.id, None)
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
            return

    reply, emotion = get_ai_response(chat_id, message.text)
    
    appearance = "pale white skin, beautiful shining eyes, short hair colored red white and green like the Algerian flag, wearing a simple white shirt"
    image_prompt = f"anime style, close-up portrait of 18 year old Algerian girl, {appearance}, {emotion} expression, simple apartment interior, sea view from window"
    url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?seed={random.randint(1, 1000000)}"
    
    bot.send_photo(chat_id, url, caption=reply)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.infinity_polling()
    
