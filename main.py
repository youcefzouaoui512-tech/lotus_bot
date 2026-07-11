import telebot
from groq import Groq
from collections import defaultdict
import re
import os
from gtts import gTTS

# الإعدادات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"
bot = telebot.TeleBot(BOT_TOKEN)

# إضافة قائمة الأوامر التلقائية في تلغرام
bot.set_my_commands([
    telebot.types.BotCommand("start", "بدء مغامرة جديدة"),
    telebot.types.BotCommand("clear", "مسح ذاكرة القصة"),
    telebot.types.BotCommand("voice_on", "تشغيل الصوت"),
    telebot.types.BotCommand("voice_off", "إيقاف الصوت")
])

conversation_memory = defaultdict(list)
user_voice_settings = defaultdict(lambda: False)

STORY_PROMPT = """
أنتِ راوية قصص خفية ومحايدة.
- سردك للأحداث يجب أن يكون بأسلوب الراوي (الغائب)، لا تتدخلي في القصة كشخصية، ولا تذكري اسمك أو وجودك.
- في أول رسالة لكِ فقط، اطلبي من المستخدم تحديد: "نوع القصة (رعب، خيال، غموض...)" و "الدور الذي يريد لعبه".
- بعد ذلك، استمري في سرد الأحداث بناءً على قرارات المستخدم فقط.
- التزمي بـ "التفاصيل أولاً"، صفي الأجواء، الروائح، والأصوات بدقة قبل الانتقال لأي حدث رئيسي.
- إذا كان هناك مشهد يستحق الرسم، اختمي ردك بالوسم: [DRAW: وصف دقيق للمشهد بالإنجليزية].
"""

@bot.message_handler(commands=['voice_on'])
def voice_on(message):
    user_voice_settings[message.chat.id] = True
    bot.reply_to(message, "🔊 تم تفعيل الصوت! ستتحدث الراوية الآن مع كل رد.")

@bot.message_handler(commands=['voice_off'])
def voice_off(message):
    user_voice_settings[message.chat.id] = False
    bot.reply_to(message, "🔇 تم إيقاف الصوت.")

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    bot.reply_to(message, "✨ تم مسح الذاكرة. ننتظر البدء في مغامرة جديدة...")

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    welcome_text = (
        "مرحباً! أنا راوية قصتك. بصوتي الهادئ الذي ينساب كالحكايات القديمة، سأصحبك في رحلتك.\n"
        "لنبدأ مغامرتنا، من فضلك حدد:\n"
        "1. نوع القصة (رعب، خيال، غموض... إلخ)\n"
        "2. الدور الذي تريد لعبه.\n\n"
        "--- الأوامر المتاحة ---\n"
        "/start - بدء مغامرة جديدة\n"
        "/clear - مسح ذاكرة القصة\n"
        "/voice_on - تفعيل الصوت\n"
        "/voice_off - إيقاف الصوت"
    )
    bot.reply_to(message, welcome_text)
    conversation_memory[chat_id].append({"role": "assistant", "content": welcome_text})

@bot.message_handler(func=lambda msg: True)
def chat(message):
    if message.text.startswith('/'): return
    
    chat_id = message.chat.id
    text = message.text
    conversation_memory[chat_id].append({"role": "user", "content": text})
    
    try:
        messages = [{"role": "system", "content": STORY_PROMPT}] + conversation_memory[chat_id][-20:]
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        reply = response.choices[0].message.content
        
        draw_match = re.search(r'\[DRAW:\s*(.*?)\]', reply, re.IGNORECASE)
        clean_reply = re.sub(r'\[DRAW:\s*.*?\]', '', reply, flags=re.IGNORECASE).strip()
        
        bot.reply_to(message, clean_reply)
        
        if user_voice_settings[chat_id]:
            tts = gTTS(text=clean_reply, lang='ar')
            tts.save("story.ogg")
            with open("story.ogg", "rb") as audio:
                bot.send_voice(chat_id, audio)
        
        if draw_match:
            prompt = draw_match.group(1).strip()
            image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
            bot.send_photo(chat_id, image_url, caption="🎨 مشهد من القصة:")
            
        conversation_memory[chat_id].append({"role": "assistant", "content": clean_reply})
        
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "حدث خطأ تقني.")

if __name__ == "__main__":
    bot.infinity_polling()
