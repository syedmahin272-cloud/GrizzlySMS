import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
import requests
import threading
import time
from flask import Flask, request
import os

# Bot Config
BOT_TOKEN = "8668990603:AAHMkDqp_NwpuhVRrFnI6qYHIr2HoiB2NuE"
ADMIN_ID = 7266067201
WEBHOOK_URL = "https://grizzlysms-8ex5.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# State Management
maintenance_mode = False
user_api_keys = {}

# Checker API Config[cite: 1]
CHECKER_URL = "http://api.agbots.site:8080/check/"
CHECKER_AUTH = "user8354"
CHECKER_API_KEY = "SIGUzg7Xf7euGs8B"

STATUS_EMOJIS = {
    "fresh": "🟢",
    "banned": "🔴",
    "registered": "🟡",
    "locked": "🔒",
    "2fa": "🔐"
}

def check_tg_number(phone_number):
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
        
    payload = {
        "auth": CHECKER_AUTH,[cite: 1]
        "api_key": CHECKER_API_KEY,[cite: 1]
        "phone_numbers": [phone_number][cite: 1]
    }
    
    try:
        response = requests.get(CHECKER_URL, json=payload, timeout=60)[cite: 1]
        if response.status_code == 200:[cite: 1]
            data = response.json()[cite: 1]
            if str(data.get("status")) == "200":[cite: 1]
                result_obj = data.get("result_obj", {})[cite: 1]
                status = str(result_obj.get(phone_number, "unknown")).lower()
                return STATUS_EMOJIS.get(status, "❓")
    except Exception:
        pass
    
    return "❓"

def wait_for_otp(chat_id, api_key, activation_id, phone_number):
    url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
    
    for _ in range(60): 
        time.sleep(5)
        try:
            res = requests.get(url, timeout=10)
            response_text = res.text
            
            if response_text.startswith("STATUS_OK"):
                otp = response_text.split(":")[1]
                
                text = f"🇨🇴 Telegram {phone_number}"[cite: 2]
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(text=f"{otp}", copy_text=CopyTextButton(text=otp)))[cite: 2]
                
                bot.send_message(chat_id, text, reply_markup=markup)
                return
            elif response_text == "STATUS_CANCEL":
                bot.send_message(chat_id, f"Cancel: {phone_number}")
                return
        except Exception:
            pass
            
    bot.send_message(chat_id, f"Time out: {phone_number}")

@bot.message_handler(commands=['start'])
def start_command(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    text = "Bot e swagotom.\n\nAPI key set korte:\n/api <tomar_key>\n\nNumber kinte:\n/buy"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['api'])
def api_command(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    args = message.text.split()
    if len(args) > 1:
        user_key = args[1]
        user_api_keys[message.from_user.id] = user_key
        bot.send_message(message.chat.id, "API key successfully set kora hoyeche.")
    else:
        current_key = user_api_keys.get(message.from_user.id, "Ekhono kono key set kora hoyni")
        bot.send_message(message.chat.id, f"Current API key:\n`{current_key}`\n\nChange korte likho:\n/api notun_key", parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    args = message.text.split()
    global maintenance_mode
    
    if len(args) > 1:
        if args[1].lower() == "on":
            maintenance_mode = True
            bot.send_message(message.chat.id, "Maintenance mode ON.")
        elif args[1].lower() == "off":
            maintenance_mode = False
            bot.send_message(message.chat.id, "Maintenance mode OFF.")

@bot.message_handler(commands=['buy'])
def buy_command(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    api_key = user_api_keys.get(message.from_user.id)
    if not api_key:
        bot.send_message(message.chat.id, "Age /api command diye API key set koro.")
        return
        
    buy_url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getNumber&service=tg&country=39&maxPrice=0.12"
    
    try:
        res = requests.get(buy_url, timeout=30)
        response_text = res.text
        
        if response_text.startswith("ACCESS_NUMBER"):
            parts = response_text.split(":")
            activation_id = parts[1]
            phone_number = parts[2]
            
            emoji_status = check_tg_number(phone_number)
            bot.send_message(message.chat.id, f"{phone_number} {emoji_status}")
            
            threading.Thread(target=wait_for_otp, args=(message.chat.id, api_key, activation_id, phone_number)).start()
            
        else:
            bot.send_message(message.chat.id, f"Number kena jayni: {response_text}")
            
    except Exception:
        bot.send_message(message.chat.id, "API theke response ashte problem hoyeche.")

# --- Flask Webhook Setup ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Error', 403

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running on Webhook!', 200

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}", drop_pending_updates=True)
    print(f"Webhook set successfully to {WEBHOOK_URL}")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
