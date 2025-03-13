import os
import telebot
import requests
from dotenv import load_dotenv
from flask import Flask, request

# Загружаем переменные из .env
load_dotenv()

# Настройки бота и API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # Пример: @my_channel или -1001234567890
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, DEEPSEEK_API_KEY]):
    raise ValueError("❌ Ошибка: Проверьте, что все переменные окружения заданы!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_history = {}

# Проверка подписки пользователя
def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(TELEGRAM_CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"⚠ Ошибка проверки подписки: {e}")
        return False

# Запрос к DeepSeek API
def ask_deepseek(user_id, prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    
    user_history.setdefault(user_id, [])
    user_history[user_id].append({"role": "user", "content": prompt})
    user_history[user_id] = user_history[user_id][-10:]
    
    data = {"model": "deepseek-chat", "messages": user_history[user_id], "temperature": 0.4}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"]
        user_history[user_id].append({"role": "assistant", "content": ai_response})
        return ai_response
    except requests.exceptions.Timeout:
        return "⚠ DeepSeek API долго отвечает, попробуйте позже."
    except requests.exceptions.RequestException as e:
        return f"⚠ Ошибка запроса к DeepSeek API: {str(e)}"

# Flask-приложение
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = message.chat.id
    print(f"📩 Получено сообщение от {user_id}: {message.text}")
    
    if check_subscription(user_id):
        bot.send_chat_action(user_id, "typing")
        response = ask_deepseek(user_id, message.text)
        print(f"🤖 Ответ от ИИ: {response}")
        bot.send_message(user_id, response)
    else:
        bot.send_message(user_id, f'⚠ Чтобы пользоваться ботом, подпишитесь на канал: {TELEGRAM_CHANNEL_ID}', parse_mode="HTML")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    WEBHOOK_URL = "https://telegram-bot-8j05.onrender.com/webhook"  # Замените на свой
    
    try:
        print(f"🟢 Бот запускается на порту {port}...")
        bot.delete_webhook()
        print("🔄 Старый вебхук удалён.")
        success = bot.set_webhook(url=WEBHOOK_URL)
        
        if success:
            print(f"✅ Новый вебхук установлен: {WEBHOOK_URL}")
        else:
            print("❌ Ошибка при установке вебхука!")
        
        webhook_info = bot.get_webhook_info()
        print(f"🔍 Webhook info: {webhook_info}")
        
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
