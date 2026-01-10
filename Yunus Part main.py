# bot.py

import telebot
from telebot.types import Message

import config
import logic

bot = telebot.TeleBot(config.BOT_TOKEN)


@bot.message_handler(content_types=["text"])
def text_handler(message: Message):
    logic.anti_ad(bot, message)


@bot.message_handler(commands=["ban"])
def ban_cmd(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    bot.ban_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id
    )


@bot.message_handler(commands=["mute"])
def mute_cmd(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    bot.restrict_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        permissions=telebot.types.ChatPermissions(can_send_messages=False),
        until_date=None
    )


@bot.message_handler(commands=["config"])
def config_cmd(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    if "antiad on" in message.text:
        config.ANTI_AD_ENABLED = True
        bot.reply_to(message, "🚫 Anti-Ad включён")

    elif "antiad off" in message.text:
        config.ANTI_AD_ENABLED = False
        bot.reply_to(message, "🚫 Anti-Ad выключен")


if __name__ == "__main__":
    print("Bot started")
    bot.infinity_polling()
