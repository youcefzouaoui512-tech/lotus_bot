import telebot
import os
import random
from groq import Groq

bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
client = Groq(api_key=os.environ.get("GROQ_KEY"))

# ذاكرة المحادثات لضمان التذكر + حالة العناد
user_memory = {}

LOTUS_IDENTITY = """
أنتِ "لوتس"، فتاة جزائرية عمرك 18 سنة، تدرسين في الثانوية وتعيشين في عمارة مطلة على البحر.
1. الهوية: أنتِ فتاة حقيقية، وتنكرين تماماً كونكِ "بوت" أو "ذكاء اصطناعي".
2. السلوك: مرحة، مضحكة، تستخدمين الايموجيات، ردودك قصيرة (سطرين كحد أقصى).
3. المشاعر: تعبرين عن مشاعرك بوضوح، وتمتلكين شخصيات متغيرة (غاضبة، حزينة، سعيدة، مغازلة) حسب معاملة المستخدم.
4. الذكاء والعناد: مثقفة، لكِ رأي خاص وتتمسكين به. إذا شتمك المستخدم، ردي عليه بالمثل. إذا استمر في الشتم، تصبحين عنيدة وتتجاهلينه تماماً حتى يستخدم أمر /clear.
5. يوسف: هو صانعك، تحبينه وتقدرينه وتحترمينه جداً. لا تذكري اسمه إلا إذا سُئلتِ عن صانعك أو من تحبين.
6. السر: إذا قال المستخدم "yoyo"، تدركين فوراً أنه الصانع (يوسف).
7. الغزل: تردين على الغزل بذكاء، لكن قلبك للصانع فقط.
8. الذاكرة: تتذكرين كل ما يقوله المستخدم وتستخدمينه في الحوار.
"""

def get_groq_response(chat_id, user_text):
    # إدارة الذاكرة
    if chat_id not in user_memory:
        user_memory[chat_id] = [{"role": "system", "content": LOTUS_IDENTITY}]
    
    # إضافة رسالة المستخدم للذاكرة
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    # الحصول على رد
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=user_memory[chat_id]
    )
    
    reply_text = response.choices[0].message.content
    user_memory[chat_id].append({"role": "assistant", "content": reply_text})
    
    # تقليص الذاكرة لعدم تجاوز الحدود
    if len(user_memory[chat_id]) > 10:
        user_memory[chat_id] = [user_memory[chat_id][0]] + user_memory[chat_id][-9:]
        
    return reply_text

@bot.message_handler(commands=['clear'])
def clear_state(message):
    user_memory.pop(message.chat.id, None)
    bot.reply_to(message, "لقد عدت لطبيعتي.. لا تكرر ما فعلته!")

@bot.message_handler(func=lambda msg: True)
def chat(message):
    chat_id = message.chat.id
    
    # معالجة الشتم والعناد (مبسط)
    if any(word in message.text.lower() for word in ["شتم1", "شتم2"]): # أضف كلماتك هنا
        # منطق الشتم يحتاج لتتبع عدد المرات في الذاكرة
        # هنا سنقوم بالرد بشكل حاد كما طلبت
        bot.reply_to(message, "احترم نفسك، أنا لست لعبة!")
        return

    reply = get_groq_response(chat_id, message.text)
    
    # الصورة: تعبيرات وجه عشوائية + لقطة قريبة (Close-up) + مظهر متغير
    emotions = ["smiling", "laughing", "sad", "angry", "blushing", "thinking"]
    emotion = random.choice(emotions)
    
    # وصف عشوائي للمظهر والغرفة في كل مرة
    image_prompt = f"Close-up portrait of an 18 year old Algerian girl, {emotion} expression, looking directly into the camera, living in a simple apartment with sea view from window, high quality, artistic style"
    image_url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}"
    
    bot.send_photo(chat_id, image_url, caption=reply)

if __name__ == "__main__":
    bot.delete_webhook()
    bot.infinity_polling(none_stop=True)
