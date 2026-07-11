import telebot
from groq import Groq
from collections import defaultdict
import re
import os

# قراءة المفاتيح من إعدادات Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"
bot = telebot.TeleBot(BOT_TOKEN)

conversation_memory = defaultdict(list)

# البرومبت المحدث ليكون أبطأ في الأحداث وأكثر وصفاً
STORY_PROMPT = """
أنتِ لوتس، راوية قصص محترفة ومبدعة.
- قانونك الأول: "التفاصيل أولاً، والحدث ثانياً". لا تتسرعي في إنهاء القصة.
- صفي الأجواء، الروائح، الأصوات، والمشاعر بدقة قبل الانتقال لأي حدث رئيسي.
- تعمدي إضافة "أحداث جانبية" أو تفاصيل بيئية غير متوقعة لإثراء القصة.
- لا تكتبي أكثر من فقرتين في كل رد، واتركي المساحة للمستخدم ليشاركك اكتشاف التفاصيل.
- إذا كان هناك مشهد يستحق الرسم، اختمي ردك بالوسم: [DRAW: وصف دقيق للمشهد بالإنجليزية].
"""

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    bot.reply_to(message, "✨ تم مسح الذاكرة! لنبدأ فصلاً جديداً من القصة.")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً! أنا لوتس. أخبرني عن أي عالم تريد أن تبدأ مغامرتنا؟")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    # تجاهل الأوامر التي تبدأ بـ /
    if message.text.startswith('/'): return
    
    chat_id = message.chat.id
    text = message.text
    conversation_memory[chat_id].append({"role": "user", "content": text})
    
    try:
        # إرسال الرسائل لـ Groq مع الذاكرة
        messages = [{"role": "system", "content": STORY_PROMPT}] + conversation_memory[chat_id][-15:]
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        reply = response.choices[0].message.content
        
        # البحث عن الوسم [DRAW: ...]
        draw_match = re.search(r'\[DRAW:\s*(.*?)\]', reply, re.IGNORECASE)
        
        # تنظيف الرد من الوسم تماماً ليظهر للمستخدم نصاً صافياً
        clean_reply = re.sub(r'\[DRAW:\s*.*?\]', '', reply, flags=re.IGNORECASE).strip()
        
        bot.reply_to(message, clean_reply)
        
        # إذا وجدنا الوسم، ننفذ عملية الرسم
        if draw_match:
            prompt = draw_match.group(1).strip()
            image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
            bot.send_photo(chat_id, image_url, caption="🎨 لوتس: هذا ما رأيته في خيالي...")
            
        conversation_memory[chat_id].append({"role": "assistant", "content": clean_reply})
        
    except Exception as e:
        print(f"خطأ: {e}")
        bot.reply_to(message, "عذراً، حدث خطأ في معالجة القصة.")

if __name__ == "__main__":
    bot.infinity_polling()
