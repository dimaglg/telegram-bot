import telebot
import requests
import os
from flask import Flask, request
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Настройки бота и API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK")  # Пример: https://t.me/my_channel
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL для вебхука

# Подключаем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Создаем Flask-приложение
app = Flask(__name__)

# Храним историю сообщений пользователей
user_history = {}

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на канал."""
    try:
        chat_member = bot.get_chat_member(TELEGRAM_CHANNEL_LINK.replace("https://t.me/", "@"), user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def ask_deepseek(user_id, prompt):
    """Запрашивает ответ у DeepSeek API с учетом истории чата."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}

    # Добавляем сообщение в историю пользователя
    if user_id not in user_history:
        user_history[user_id] = []

    user_history[user_id].append({"role": "user", "content": prompt})

    # Оставляем только последние 10 сообщений для экономии токенов
    if len(user_history[user_id]) > 10:
        user_history[user_id] = user_history[user_id][-10:]

    data = {
        "model": "deepseek-chat",
        "messages": user_history[user_id],
        "temperature": 0.4
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"]

        # Добавляем ответ ИИ в историю
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
    """Обрабатывает сообщения пользователей с учетом контекста"""
    user_id = message.chat.id
    print(f"Получено сообщение от {user_id}: {message.text}")

    if check_subscription(user_id):
        bot.send_chat_action(user_id, "typing")  # Показывает статус "пишет..."
        response = ask_deepseek(user_id, message.text)
        print(f"Ответ от ИИ: {response}")  # Отладка
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, f'⚠ Чтобы пользоваться ботом, подпишитесь на канал: <a href="{TELEGRAM_CHANNEL_LINK}">NEWS_GLG</a>', parse_mode="HTML")

# 🚀 **Запуск бота**
if __name__ == "__main__":
    try:
        # Удаляем старый webhook
        bot.remove_webhook()

        # Ставим новый webhook
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

        print(f"Бот запущен! Webhook установлен: {WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
