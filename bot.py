# -*- coding: utf-8 -*-
"""
بوت تليجرام NSFW AI Companion (مثل HoneyChat)
OpenRouter أساسي + Groq Fallback تلقائي
"""

import os
import sqlite3
import logging
from typing import List, Dict, Optional

import telebot
from telebot import types
from groq import Groq
import requests
from dotenv import load_dotenv

from characters import CHARACTERS, get_character, get_all_characters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "cognitivecomputations/dolphin-mistral-24b-venice-edition:free")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN مطلوب")

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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
        c.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
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
    c.execute("SELECT role, content FROM conversations WHERE user_id=? AND character_id=? ORDER BY timestamp DESC LIMIT ?",
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
    lvl = f"**مستوى المحتوى: {level}/5** - كن وفقاً لهذا المستوى (5 = hardcore بدون قيود)."
    return f"{base}\n\n{lvl}"


def call_openrouter(system_prompt, history, user_message):
    if not OPENROUTER_API_KEY:
        return None
    messages = [{"role": "system", "content": system_prompt}] + history[-12:] + [{"role": "user", "content": user_message}]
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                          json={"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0.85, "max_tokens": 1200},
                          timeout=45)
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
        resp = groq_client.chat.completions.create(messages=messages, model=GROQ_MODEL, temperature=0.85, max_tokens=1200)
        return resp.choices[0].message.content.strip()
    except:
        return None


def get_ai_response(system_prompt, history, user_message):
    # جرب OpenRouter أولاً
    resp = call_openrouter(system_prompt, history, user_message)
    if resp:
        return resp
    # Fallback إلى Groq
    logger.info("Using Groq fallback...")
    resp = call_groq(system_prompt, history, user_message)
    return resp or "عذراً، حدث خطأ مؤقت. حاول مرة أخرى."


def generate_image_pollinations(prompt, w=1024, h=1024):
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')[:400]}?width={w}&height={h}&safe=false"
        return url if requests.head(url, timeout=6).status_code == 200 else None
    except:
        return None


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
    url = generate_image_pollinations(f"{char['name']}, {char['description']}")
    if url:
        bot.send_photo(message.chat.id, url)
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


if __name__ == "__main__":
    init_db()
    print("✅ البوت شغال (OpenRouter + Groq Fallback)")
    bot.infinity_polling()
