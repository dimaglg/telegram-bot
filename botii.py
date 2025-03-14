import telebot
import requests
import os
import time
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Настройки бота и API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверяем, загружены ли переменные
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_LINK or not DEEPSEEK_API_KEY:
    print("⚠ Ошибка: не загружены переменные окружения! Проверь файл .env")
    exit(1)

# Получаем имя канала
TELEGRAM_CHANNEL_USERNAME = TELEGRAM_CHANNEL_LINK.split("/")[-1]

# Подключаем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Храним историю сообщений пользователей
user_history = {}

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на канал."""
    try:
        chat_member = bot.get_chat_member(f"@{TELEGRAM_CHANNEL_USERNAME}", user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def ask_deepseek(user_id, prompt):
    """Запрашивает ответ у DeepSeek API с учетом истории чата."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}

    if user_id not in user_history:
        user_history[user_id] = []

    user_history[user_id].append({"role": "user", "content": prompt})
    user_history[user_id] = user_history[user_id][-10:]

    data = {
        "model": "deepseek-chat",
        "messages": user_history[user_id],
        "temperature": 0.4
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        response_json = response.json()

        if "choices" in response_json and response_json["choices"]:
            ai_response = response_json["choices"][0]["message"]["content"]
        else:
            ai_response = "⚠ DeepSeek не вернул ответ."

        user_history[user_id].append({"role": "assistant", "content": ai_response})
        return ai_response

    except requests.exceptions.Timeout:
        return "⚠ DeepSeek API долго отвечает, попробуйте позже."
    except requests.exceptions.HTTPError as e:
        return f"⚠ Ошибка API: {response.status_code} {response.text}"
    except Exception as e:
        return f"⚠ Ошибка запроса: {str(e)}"

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    """Обрабатывает сообщения пользователей с учетом контекста"""
    user_id = message.chat.id
    print(f"Получено сообщение от {user_id}: {message.text}")

    if check_subscription(user_id):
        bot.send_chat_action(user_id, "typing")
        response = ask_deepseek(user_id, message.text)
        print(f"Ответ от ИИ: {response}")
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, f'⚠ Чтобы пользоваться ботом, подпишитесь на канал: <a href="{TELEGRAM_CHANNEL_LINK}">NEWS_GLG</a>', parse_mode="HTML")

# 🚀 Автоперезапуск бота
if __name__ == "__main__":
    while True:
        try:
            print("Бот запущен!")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            time.sleep(5)
