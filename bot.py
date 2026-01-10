import telebot
from telebot.types import Message, ChatPermissions
import config
import logic
from logic import BotModer

bot = telebot.TeleBot(config.BOT_TOKEN)
moder = BotModer()


# ----------------------------
# АНТИ-РЕКЛАМА
# ----------------------------
@bot.message_handler(content_types=["text"])
def text_handler(message: Message):
    logic.anti_ad(bot, message)


# ----------------------------
# БАН И МЬЮТ
# ----------------------------
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id in config.ADMIN_IDS


@bot.message_handler(commands=["ban"])
def ban_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message:
        return

    bot.ban_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id
    )


@bot.message_handler(commands=["mute"])
def mute_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message:
        return

    bot.restrict_chat_member(
        message.chat.id,
        message.reply_to_message.from_user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=None
    )


# ----------------------------
# КОНФИГ
# ----------------------------
@bot.message_handler(commands=["config"])
def config_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = message.text.lower()
    if "antiad on" in text:
        config.ANTI_AD_ENABLED = True
        bot.reply_to(message, "🚫 Anti-Ad включён")
    elif "antiad off" in text:
        config.ANTI_AD_ENABLED = False
        bot.reply_to(message, "🚫 Anti-Ad выключен")


# ----------------------------
# РОЛИ
# ----------------------------
@bot.message_handler(commands=['role'])
def set_role(message: Message):
    if not message.reply_to_message:
        return bot.reply_to(message, "Команда должна быть ответом на сообщение пользователя.")

    target = message.reply_to_message.from_user
    args = message.text.split()

    if len(args) < 2:
        return bot.reply_to(message, "Использование: /role Модератор")

    role_name = args[1].lower()

    if role_name == "модератор":
        new_role = moder.make_moder(target.id)
        bot.reply_to(message, f"{target.first_name} назначен {new_role}!")
    else:
        bot.reply_to(message, "Неизвестная роль.")


@bot.message_handler(commands=['remove_role'])
def remove_role(message: Message):
    if not message.reply_to_message:
        return bot.reply_to(message, "Команда должна быть ответом на сообщение пользователя.")

    target = message.reply_to_message.from_user
    new_role = moder.remove_role(target.id)
    bot.reply_to(message, f"Роль пользователя {target.first_name} сброшена до {new_role}.")


# ----------------------------
# АВТОМАТИЧЕСКАЯ ОБРАБОТКА СООБЩЕНИЙ
# ----------------------------
@bot.message_handler(func=lambda m: True)
def handle_msg(message: Message):
    user_id = message.from_user.id

    moder.add_user(user_id)
    moder.add_message(user_id)
    new_role = moder.auto_update_role(user_id)

    if new_role:
        bot.reply_to(message, f"{message.from_user.first_name} теперь {new_role}!")


# ----------------------------
# ЗАПУСК БОТА
# ----------------------------
if __name__ == "__main__":
    print("Bot started")
    bot.infinity_polling()
