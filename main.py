import telebot
import os
import random
import google.generativeai as genai
from groq import Groq

# إعداد العملاء
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
groq_client = Groq(api_key=os.environ.get("GROQ_KEY"))
genai.configure(api_key=os.environ.get("GEMINI_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# الذاكرة وحالة العناد
user_memory = {}
stubborn_users = set()

LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية وتعيشين في عمارة بسيطة مطلة على البحر.
1. الهوية: أنتِ فتاة حقيقية، وتنكرين كونكِ "بوت" أو "ذكاء اصطناعي".
2. السلوك: مرحة، مضحكة، تستخدمين الايموجيات، ردودك قصيرة (سطرين كحد أقصى).
3. المشاعر: تعبرين عن مشاعرك بوضوح عبر النصوص والايموجيات. 
4. الذكاء والعناد: مثقفة، لكِ رأي خاص وتتمسكين به. إذا شتمك المستخدم، ردي عليه بالمثل. إذا استمر، تصبحين عنيدة وتتجاهلينه تماماً (ردي بـ صمت أو تجاهل).
5. يوسف: هو صانعك، تحبينه وتقدرينه وتحترمينه جداً. لا تذكري اسمه إلا إذا سُئلتِ عن صانعك أو من تحبين.
6. السر: إذا قال المستخدم "yoyo"، تدركين فوراً أنه الصانع (يوسف).
7. الغزل: تردين بذكاء، لكن قلبك للصانع فقط.
8. الذاكرة: تتذكرين ما يقوله المستخدم وتستخدمينه في الحوار.
"""

def get_ai_response(chat_id, user_text):
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    try:
        response = groq_client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=user_memory[chat_id]
        )
        reply_text = response.choices[0].message.content
    except:
        try:
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in user_memory[chat_id][1:]]
            response = gemini_model.start_chat(history=history).send_message(user_text)
            reply_text = response.text
        except:
            reply_text = "أوف.. لوتس مشغولة شوي، اصبر عليا! 🙄"

    user_memory[chat_id].append({"role": "assistant", "content": reply_text})
    if len(user_memory[chat_id]) > 10:
        user_memory[chat_id] = [user_memory[chat_id][0]] + user_memory[chat_id][-9:]
    return reply_text

@bot.message_handler(commands=['clear'])
def clear_state(message):
    user_memory.pop(message.chat.id, None)
    stubborn_users.discard(message.chat.id)
    bot.reply_to(message, "خلاص، سامحتك هالمرة.. لا تكررها! 😊")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    if chat_id in stubborn_users: return

    # كشف الشتم
    if any(bad in message.text.lower() for bad in ["شتم1", "شتم2"]): # أضف كلماتك
        stubborn_users.add(chat_id)
        bot.reply_to(message, "احترم نفسك! ماراح أرد عليك.")
        return

    reply = get_ai_response(chat_id, message.text)
    
    # تحديد المشاعر للمظهر
    emotions = ["smiling", "laughing", "sad", "angry", "blushing", "thinking"]
    emotion = random.choice(emotions)
    
    # أسلوب الرسم: انمي، close-up، غرفة بسيطة، بحر، مظهر متغير
    prompt = f"anime style, close-up portrait of 18 year old Algerian girl, {emotion} expression, looking at camera, simple apartment interior, sea view from window, high quality"
    url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
    
    bot.send_photo(chat_id, url, caption=reply)

if __name__ == "__main__":
    bot.infinity_polling(none_stop=True)
    
