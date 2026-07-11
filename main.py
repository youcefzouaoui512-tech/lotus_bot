import telebot
import os
import re
import asyncio
import edge_tts
from openai import OpenAI
import google.generativeai as genai
from groq import Groq
from collections import defaultdict

# 1. الإعدادات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# تأكد من إضافة مفاتيحك في متغيرات البيئة في Railway
deepseek = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
groq_client = Groq(api_key=os.environ.get("GROQ_KEY"))

bot = telebot.TeleBot(BOT_TOKEN)
conversation_memory = defaultdict(list)
user_voice_settings = defaultdict(lambda: False)

STORY_PROMPT = "أنتِ راوية قصص خفية ومباشرة. اختصري الأحداث، اكتبي فقرة واحدة، ولا تذكري اسمك. إذا كان المشهد يستحق، اختمي بـ [DRAW: وصف المشهد بالإنجليزية]."

# 2. الأوامر الأساسية
@bot.message_handler(commands=['start', 'voice_on', 'voice_off', 'clear'])
def handle_commands(message):
    if message.text == '/start':
        bot.reply_to(message, "بدأت القصة... لوتس تستمع إليك.")
    elif message.text == '/voice_on':
        user_voice_settings[message.chat.id] = True
        bot.reply_to(message, "🔊 تم تفعيل الصوت.")
    elif message.text == '/voice_off':
        user_voice_settings[message.chat.id] = False
        bot.reply_to(message, "🔇 تم إيقاف الصوت.")
    elif message.text == '/clear':
        conversation_memory[message.chat.id] = []
        bot.reply_to(message, "✨ تم مسح الذاكرة.")

# 3. دالة الدردشة الرئيسية (مع نظام الطوارئ)
@bot.message_handler(func=lambda msg: True)
def chat(message):
    if message.text.startswith('/'): return
    
    chat_id = message.chat.id
    user_input = message.text
    conversation_memory[chat_id].append({"role": "user", "content": user_input})
    
    story_reply = None
    
    # محاولة استخدام Gemini و DeepSeek (النظام الأساسي)
    try:
        gemini_resp = gemini_model.generate_content(f"حلل سياق القصة التالي باختصار: {user_input}")
        context_analysis = gemini_resp.text
        
        ds_resp = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": STORY_PROMPT + " تحليل السياق: " + context_analysis},
                {"role": "user", "content": "اكتب الحدث التالي."}
            ]
        )
        story_reply = ds_resp.choices[0].message.content
        
    except Exception as e:
        print(f"فشل النظام الأساسي (DeepSeek/Gemini): {e}. التبديل إلى Groq...")
        
        # محاولة الطوارئ (Groq)
        try:
            groq_resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": STORY_PROMPT},
                          {"role": "user", "content": user_input}]
            )
            story_reply = groq_resp.choices[0].message.content
        except Exception as groq_err:
            story_reply = "لوتس في صمت عميق حالياً... (عطل تقني)."

    # 4. معالجة الرد (صور وصوت)
    if story_reply:
        draw_match = re.search(r'\[DRAW:\s*(.*?)\]', story_reply, re.IGNORECASE)
        clean_reply = re.sub(r'\[DRAW:\s*.*?\]', '', story_reply, flags=re.IGNORECASE).strip()
        
        # إرسال الصورة إن وجدت
        if draw_match:
            prompt = draw_match.group(1).strip()
            image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
            bot.send_photo(chat_id, image_url, caption=clean_reply)
        else:
            bot.reply_to(message, clean_reply)
        
        # إرسال الصوت
        if user_voice_settings[chat_id]:
            try:
                tts = edge_tts.Communicate(clean_reply, "ar-SA-ZainabNeural")
                asyncio.run(tts.save("story.ogg"))
                with open("story.ogg", "rb") as audio:
                    bot.send_voice(chat_id, audio)
            except Exception as e:
                print(f"خطأ في الصوت: {e}")

        conversation_memory[chat_id].append({"role": "assistant", "content": clean_reply})

if __name__ == "__main__":
    bot.infinity_polling()
    
