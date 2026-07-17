# -*- coding: utf-8 -*-
"""
بوت تليجرام NSFW AI Companion
- Tensor.Art + Pollinations (محسن للـ NSFW)
- ElevenLabs + edge-tts للصوت (فقط في اللحظات الإباحية)
"""

import os
import sqlite3
import logging
import asyncio
import tempfile
from typing import List, Dict, Optional

import telebot
from telebot import types
from groq import Groq
import requests
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import edge_tts

from characters import get_character, get_all_characters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
TENSOR_API_KEY = os.getenv("TENSOR_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN مطلوب")

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DB_PATH = "bot_database.db"


# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        current_character_id TEXT DEFAULT '1', content_level INTEGER DEFAULT 3,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, character_id TEXT,
        role TEXT, content TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()


def get_or_create_user(user_id, username=None, first_name=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                  (user_id, username, first_name))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
    conn.close()
    return user


def update_user_character(user_id, character_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET current_character_id=? WHERE user_id=?", (character_id, user_id))
    conn.commit()
    conn.close()


def update_user_level(user_id, level):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET content_level=? WHERE user_id=?", (level, user_id))
    conn.commit()
    conn.close()


def get_user_settings(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT current_character_id, content_level FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return {"character_id": r[0], "level": r[1]} if r else {"character_id": "1", "level": 3}


def save_message(user_id, character_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, character_id, role, content) VALUES (?, ?, ?, ?)",
              (user_id, character_id, role, content))
    conn.commit()
    conn.close()


def get_conversation_history(user_id, character_id, limit=15):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT role, content FROM conversations 
                 WHERE user_id=? AND character_id=? ORDER BY timestamp DESC LIMIT ?""",
              (user_id, character_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def clear_conversation(user_id, character_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE user_id=? AND character_id=?", (user_id, character_id))
    conn.commit()
    conn.close()


def build_system_prompt(char_data, level):
    base = char_data["system_prompt"]
    
    if level >= 4:
        level_instruction = "أنت الآن في مرحلة متقدمة. يمكنك إظهار رغبتك بشكل أوضح مع الحفاظ على شخصيتك."
    else:
        level_instruction = f"مستوى المحتوى الحالي: {level}/5. ابقِ مترددة وغير مباشرة."

    return f"""{base}

{level_instruction}
كن immersive وتذكر سياق المحادثة."""


def call_openrouter(system_prompt, history, user_message):
    if not OPENROUTER_API_KEY:
        return None
    messages = [{"role": "system", "content": system_prompt}] + history[-12:] + [{"role": "user", "content": user_message}]
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0.9, "max_tokens": 1400},
            timeout=50
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except:
        return None


def call_groq(system_prompt, history, user_message):
    if not groq_client:
        return None
    messages = [{"role": "system", "content": system_prompt}] + history[-12:] + [{"role": "user", "content": user_message}]
    try:
        resp = groq_client.chat.completions.create(
            messages=messages, model=GROQ_MODEL, temperature=0.9, max_tokens=1400
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return None


def get_ai_response(system_prompt, history, user_message):
    resp = call_openrouter(system_prompt, history, user_message)
    if resp:
        return resp
    logger.info("Using Groq fallback...")
    resp = call_groq(system_prompt, history, user_message)
    return resp or "عذراً، حدث خطأ مؤقت. حاول مرة أخرى."


# ==================== توليد الصور (Tensor.Art + Pollinations محسن للـ NSFW) ====================
def generate_image(prompt: str, width: int = 1024, height: int = 1024, level: int = 3) -> Optional[str]:
    """يجرب Tensor.Art أولاً ثم Pollinations مع تحسينات قوية للـ NSFW"""

    # === 1. Tensor.Art ===
    if TENSOR_API_KEY:
        try:
            url = "https://api.tensor.art/v1/generate"
            headers = {
                "Authorization": f"Bearer {TENSOR_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": 28,
                "guidance_scale": 7.5,
                "seed": -1
            }
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if "images" in data and len(data["images"]) > 0:
                    return data["images"][0]["url"]
        except Exception as e:
            logger.warning(f"Tensor.Art failed: {e}")

    # === 2. Pollinations (محسن للـ NSFW) ===
    try:
        enhanced_prompt = prompt

        if level >= 3:
            nsfw_additions = ", highly detailed body, sensual lighting, erotic atmosphere, detailed skin texture"
            if level >= 4:
                nsfw_additions += ", explicit nudity, detailed breasts, detailed pussy, wet skin, aroused expression"
            if level == 5:
                nsfw_additions += ", hardcore, explicit sex, cum, ahegao, spreading legs, detailed genitals"

            enhanced_prompt = prompt + nsfw_additions

        clean_prompt = enhanced_prompt.replace("\n", " ").strip()[:500]
        encoded_prompt = requests.utils.quote(clean_prompt)

        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&safe=false&seed=42"

        if requests.get(url, timeout=18).status_code == 200:
            return url
    except Exception as e:
        logger.error(f"Pollinations NSFW failed: {e}")

    return None


# ==================== توليد وإرسال الصوت ====================
async def generate_and_send_voice(bot, chat_id, text, voice_name="Rachel"):
    if len(text) < 10:
        return

    # ElevenLabs
    try:
        if elevenlabs_client:
            audio = elevenlabs_client.generate(
                text=text[:600],
                voice=voice_name,
                model="eleven_multilingual_v2"
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tmp.write(audio)
                bot.send_voice(chat_id, open(tmp.name, 'rb'))
                return
    except Exception as e:
        logger.warning(f"ElevenLabs failed: {e}")

    # edge-tts Fallback
    try:
        communicate = edge_tts.Communicate(text[:400], "en-US-AriaNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            await communicate.save(tmp.name)
            bot.send_voice(chat_id, open(tmp.name, 'rb'))
    except Exception as e:
        logger.error(f"edge-tts failed: {e}")


# ==================== أوامر البوت ====================
@bot.message_handler(commands=['start'])
def start(message):
    get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    markup = types.InlineKeyboardMarkup()
    for cid, name, _ in get_all_characters():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"choose_char_{cid}"))
    bot.send_message(message.chat.id, "اختر شخصية:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("choose_char_"))
def choose_char(call):
    uid = call.from_user.id
    cid = call.data.split("_")[-1]
    update_user_character(uid, cid)
    clear_conversation(uid, cid)
    char = get_character(cid)
    bot.edit_message_text(f"✅ {char['name']}\n{char['description']}", call.message.chat.id, call.message.message_id)


@bot.message_handler(commands=['level'])
def level_cmd(message):
    s = get_user_settings(message.from_user.id)
    bot.send_message(message.chat.id, f"المستوى الحالي: {s['level']}/5")


@bot.message_handler(commands=['image'])
def img_cmd(message):
    s = get_user_settings(message.from_user.id)
    char = get_character(s["character_id"])
    history = get_conversation_history(message.from_user.id, s["character_id"], 5)

    style = char.get("style", "realistic")
    style_prompt = "anime style, detailed anime illustration" if style == "anime" else "photorealistic, highly detailed"

    image_prompt = f"{char['name']}, {char['description']}, {style_prompt}, masterpiece"

    if history:
        last_msg = next((m['content'] for m in reversed(history) if m['role'] == 'user'), "")
        if last_msg:
            image_prompt += f", {last_msg[:180]}"

    if s["level"] >= 3:
        image_prompt += ", seductive pose, detailed body"

    bot.send_message(message.chat.id, "⏳ جاري توليد الصورة...")
    url = generate_image(image_prompt, level=s["level"])

    if url:
        try:
            bot.send_photo(message.chat.id, url, caption=char['name'])
        except:
            bot.send_message(message.chat.id, f"رابط الصورة: {url}")
    else:
        bot.send_message(message.chat.id, "فشل توليد الصورة.")


@bot.message_handler(commands=['reset'])
def reset_cmd(message):
    s = get_user_settings(message.from_user.id)
    clear_conversation(message.from_user.id, s["character_id"])
    bot.send_message(message.chat.id, "✅ تم مسح الذاكرة.")


@bot.message_handler(func=lambda m: True)
def chat(message):
    if message.text.startswith('/'):
        return

    uid = message.from_user.id
    s = get_user_settings(uid)
    char = get_character(s["character_id"])

    save_message(uid, s["character_id"], "user", message.text)
    hist = get_conversation_history(uid, s["character_id"])
    prompt = build_system_prompt(char, s["level"])

    bot.send_chat_action(message.chat.id, 'typing')
    reply = get_ai_response(prompt, hist, message.text)
    save_message(uid, s["character_id"], "assistant", reply)

    bot.reply_to(message, reply)

    # إرسال صوت فقط في اللحظات الإباحية القوية
    if s["level"] >= 4:
        asyncio.create_task(generate_and_send_voice(bot, message.chat.id, reply, char.get("voice", "Rachel")))


if __name__ == "__main__":
    init_db()
    print("✅ البوت شغال (Tensor.Art + Pollinations NSFW + Voice)")
    bot.infinity_polling()
