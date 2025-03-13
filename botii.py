import telebot
import requests
import os
import logging
from flask import Flask, request
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK")  # Например: https://t.me/my_channel
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL вебхука

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и Flask
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# История сообщений
user_history = {}

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на канал."""
    try:
        chat_member = bot.get_chat_member(TELEGRAM_CHANNEL_LINK.replace("https://t.me/", "@"), user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

def ask_deepseek(user_id, prompt):
    """Запрашивает ответ у DeepSeek API."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}

    # История диалога
    if user_id not in user_history:
        user_history[user_id] = []
    
    user_history[user_id].append({"role": "user", "content": prompt})

    # Оставляем последние 10 сообщений
    if len(user_history[user_id]) > 10:
        user_history[user_id] = user_history[user_id][-10:]

    data = {
        "model": "deepseek-chat",
        "messages": user_history[user_id],
        "temperature": 0.4
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"]

        # Добавляем ответ в историю
        user_history[user_id].append({"role": "assistant", "content": ai_response})

        return ai_response
    except requests.exceptions.Timeout:
        return "⚠ DeepSeek API долго отвечает, попробуйте позже."
    except requests.exceptions.RequestException as e:
        return f"⚠ Ошибка запроса к DeepSeek API: {str(e)}"

@app.route("/", methods=["GET"])
def home():
    return "Бот работает! 🚀"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    """Получает обновления от Telegram и передает их боту."""
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    """Обрабатывает сообщения пользователей"""
    user_id = message.chat.id
    logger.info(f"Сообщение от {user_id}: {message.text}")

    if check_subscription(user_id):
        bot.send_chat_action(user_id, "typing")
        response = ask_deepseek(user_id, message.text)
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, f'⚠ Чтобы пользоваться ботом, подпишитесь на канал: <a href="{TELEGRAM_CHANNEL_LINK}">NEWS_GLG</a>', parse_mode="HTML")

# 🚀 Запуск бота
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        success = bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

        if success:
            logger.info(f"Webhook установлен: {WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")
        else:
            logger.error("Ошибка установки вебхука!")

        app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
