import telebot
import requests
import os
from dotenv import load_dotenv
from flask import Flask, request

# Загружаем переменные из .env
load_dotenv(dotenv_path="dsb.env")

# Настройки бота и API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK")  # Пример: https://t.me/my_channel
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Подключаем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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
        response = requests.post(url, json=data, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"]

        # Добавляем ответ ИИ в историю
        user_history[user_id].append({"role": "assistant", "content": ai_response})

        return ai_response
    except requests.exceptions.Timeout:
        return "⚠ DeepSeek API долго отвечает, попробуйте позже."
    except requests.exceptions.RequestException as e:
        return f"⚠ Ошибка запроса к DeepSeek API: {str(e)}"

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


    try:
        print("Бот запущен!")
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
