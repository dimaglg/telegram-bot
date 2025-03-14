from flask import Flask
import telebot
import requests
import os
import time
from dotenv import load_dotenv
import threading

# Загружаем переменные окружения
load_dotenv()

# Настройки бота и API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверяем, загружены ли переменные
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_LINK or not DEEPSEEK_API_KEY:
    print("⚠ Ошибка: не загружены переменные окружения! Проверь файл .env")
    exit(1)

# Подключаем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Flask-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает! 🚀"

# Функция для проверки подписки пользователя
def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(f"@{TELEGRAM_CHANNEL_LINK.split('/')[-1]}", user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

# Функция общения с DeepSeek API
def ask_deepseek(user_id, prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}

    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        return response_json.get("choices", [{}])[0].get("message", {}).get("content", "⚠ Ошибка ответа от DeepSeek.")
    except requests.exceptions.RequestException as e:
        return f"⚠ Ошибка запроса: {str(e)}"

# Обработчик сообщений от пользователей
@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = message.chat.id
    print(f"Получено сообщение от {user_id}: {message.text}")

    if check_subscription(user_id):
        bot.send_chat_action(user_id, "typing")
        response = ask_deepseek(user_id, message.text)
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, f'⚠ Чтобы пользоваться ботом, подпишитесь на канал: <a href="{TELEGRAM_CHANNEL_LINK}">NEWS_GLG</a>', parse_mode="HTML")

# Запуск бота в отдельном потоке
def run_bot():
    while True:
        try:
            print("Бот запущен!")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Render требует открытый порт
    app.run(host="0.0.0.0", port=port)
