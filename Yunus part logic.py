# logic.py

import re
import time
from collections import defaultdict
from telebot.types import ChatPermissions

import config

URL_RE = re.compile(r"(http|https)://|t\.me/|bit\.ly", re.I)
USERNAME_RE = re.compile(r"@\w{4,}")

message_cache = defaultdict(list)
warnings = defaultdict(int)


# ===== УТИЛИТЫ =====
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def is_spam(user_id: int, text: str) -> bool:
    now = time.time()
    history = message_cache[user_id]

    history.append((text, now))
    message_cache[user_id] = [
        (t, ts) for t, ts in history
        if now - ts < config.SPAM_WINDOW
    ]

    same = [t for t, _ in message_cache[user_id] if t == text]
    return len(same) >= config.SPAM_LIMIT


def add_warning(bot, message, reason: str):
    user_id = message.from_user.id
    warnings[user_id] += 1

    if warnings[user_id] >= config.MAX_WARNINGS:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.send_message(
            message.chat.id,
            f"⛔ Пользователь забанен ({reason})"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"⚠️ Предупреждение {warnings[user_id]}/{config.MAX_WARNINGS}\nПричина: {reason}"
        )


# ===== АНТИ-РЕКЛАМА =====
def anti_ad(bot, message):
    if not config.ANTI_AD_ENABLED:
        return

    if is_admin(message.from_user.id):
        return

    text = (message.text or "").lower()

    if URL_RE.search(text):
        bot.delete_message(message.chat.id, message.message_id)
        add_warning(bot, message, "Реклама (ссылка)")
        return

    if USERNAME_RE.search(text):
        bot.delete_message(message.chat.id, message.message_id)
        add_warning(bot, message, "Реклама (@username)")
        return

    for word in config.STOP_WORDS:
        if word in text:
            bot.delete_message(message.chat.id, message.message_id)
            add_warning(bot, message, f"Запрещённое слово: {word}")
            return

    if is_spam(message.from_user.id, text):
        bot.delete_message(message.chat.id, message.message_id)
        bot.restrict_chat_member(
            message.chat.id,
            message.from_user.id,
            ChatPermissions(can_send_messages=False),
            until_date=int(time.time()) + config.MUTE_TIME
        )
        add_warning(bot, message, "Флуд")
        return
    
