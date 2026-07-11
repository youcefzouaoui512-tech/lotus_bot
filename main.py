import telebot
from groq import Groq
from collections import defaultdict
import re
import os
from gtts import gTTS

# قراءة المفاتيح من متغيرات النظام (System Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"
bot = telebot.TeleBot(BOT_TOKEN)

conversation_memory = defaultdict(list)

STORY_PROMPT = """
أنتِ لوتس، راوية قصص محترفة ومبدعة.
- ابني قصة تفاعلية مع المستخدم، وتحدثي بصيغة المتكلم.
- إذا طلب المستخدم منكِ رسم أي شيء، قومي بإنهاء ردكِ دائماً بالوسم التالي: [DRAW: وصف دقيق للمشهد بالإنجليزية].
- لا تضعي أي نص بعد الوسم.
- إذا لم يطلب المستخدم رسماً، لا تضعي الوسم.
"""

@bot.message_handler(commands=['clear'])
def clear_memory(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    bot.reply_to(message, "✨ تم مسح الذاكرة! لوتس مستعدة لبدء قصة جديدة.")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً! أنا لوتس. أخبرني عن أي عالم تريد أن نبدأ مغامرتنا؟")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    if message.text.startswith('/'): return
    
    chat_id = message.chat.id
    text = message.text
    conversation_memory[chat_id].append({"role": "user", "content": text})
    
    try:
        messages = [{"role": "system", "content": STORY_PROMPT}] + conversation_memory[chat_id][-15:]
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        reply = response.choices[0].message.content
        
        draw_match = re.search(r'\[DRAW: (.*?)\]', reply)
        clean_reply = reply.replace(draw_match.group(0), "") if draw_match else reply
        bot.reply_to(message, clean_reply)
        
        if draw_match:
            prompt = draw_match.group(1)
            image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
            bot.send_photo(chat_id, image_url, caption="🎨 لوتس: هذا هو المشهد الذي طلبته!")
            
        conversation_memory[chat_id].append({"role": "assistant", "content": clean_reply})
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
    
