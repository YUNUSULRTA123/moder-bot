from collections import defaultdict
import re
import time
import sqlite3
from datetime import datetime, timedelta
from telebot.types import ChatPermissions
import config

ROLES = {
    "newbie": "👶 Новичок",
    "member": "🧑 Участник",
    "active": "⭐ Активный",
    "moder": "🛡️ Модератор"
}

URL_RE = re.compile(r"(http|https)://|t\.me/|bit\.ly", re.I)
USERNAME_RE = re.compile(r"@\w{4,}")

class BotModer:
    def __init__(self, db_path="roles.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._create_tables()

        self.message_cache = defaultdict(list)
        self.warnings = defaultdict(int)

    def _create_tables(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            messages INTEGER DEFAULT 0,
            join_date TEXT,
            role TEXT DEFAULT 'newbie'
        )
        """)
        self.conn.commit()

    def add_user(self, user_id):
        self.cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not self.cur.fetchone():
            self.cur.execute(
                "INSERT INTO users (user_id, join_date) VALUES (?, ?)",
                (user_id, datetime.utcnow().isoformat())
            )
            self.conn.commit()

    def get_user(self, user_id):
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return self.cur.fetchone()

    def set_role(self, user_id, role_key):
        self.cur.execute("UPDATE users SET role=? WHERE user_id=?", (role_key, user_id))
        self.conn.commit()

    def add_message(self, user_id):
        self.cur.execute("UPDATE users SET messages = messages + 1 WHERE user_id=?", (user_id,))
        self.conn.commit()

    def auto_update_role(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        _, messages, join_date, role = user
        join_date = datetime.fromisoformat(join_date)

        if role == "newbie" and messages >= 50:
            self.set_role(user_id, "member")
            return ROLES["member"]
        
        if role == "member" and datetime.utcnow() - join_date >= timedelta(days=7):
            self.set_role(user_id, "active")
            return ROLES["active"]
        return None

    def make_moder(self, user_id):
        self.set_role(user_id, "moder")
        return ROLES["moder"]

    def remove_role(self, user_id):
        self.set_role(user_id, "newbie")
        return ROLES["newbie"]

    def is_admin(self, user_id: int) -> bool:
        return user_id in config.ADMIN_IDS

    # ===== СПАМ =====
    def is_spam(self, user_id: int, text: str) -> bool:
        now = time.time()
        history = self.message_cache[user_id]

        history.append((text, now))
        self.message_cache[user_id] = [
            (t, ts) for t, ts in history
            if now - ts < config.SPAM_WINDOW
        ]

        same = [t for t, _ in self.message_cache[user_id] if t == text]
        return len(same) >= config.SPAM_LIMIT

    # ===== ПРЕДУПРЕЖДЕНИЯ =====
    def add_warning(self, bot, message, reason: str):
        user_id = message.from_user.id
        self.warnings[user_id] += 1

        if self.warnings[user_id] >= config.MAX_WARNINGS:
            bot.ban_chat_member(message.chat.id, user_id)
            bot.send_message(
                message.chat.id,
                f"⛔ Пользователь забанен ({reason})"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"⚠️ Предупреждение {self.warnings[user_id]}/{config.MAX_WARNINGS}\nПричина: {reason}"
            )

    # ===== АНТИ-РЕКЛАМА =====
    def anti_ad(self, bot, message):
        if not config.ANTI_AD_ENABLED:
            return

        if self.is_admin(message.from_user.id):
            return

        text = (message.text or "").lower()

        if URL_RE.search(text):
            bot.delete_message(message.chat.id, message.message_id)
            self.add_warning(bot, message, "Реклама (ссылка)")
            return

        if USERNAME_RE.search(text):
            bot.delete_message(message.chat.id, message.message_id)
            self.add_warning(bot, message, "Реклама (@username)")
            return

        for word in config.STOP_WORDS:
            if word in text:
                bot.delete_message(message.chat.id, message.message_id)
                self.add_warning(bot, message, f"Запрещённое слово: {word}")
                return

        if self.is_spam(message.from_user.id, text):
            bot.delete_message(message.chat.id, message.message_id)
            bot.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + config.MUTE_TIME
            )
            self.add_warning(bot, message, "Флуд")
            return
