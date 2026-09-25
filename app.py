import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
import requests
import threading
import time
from flask import Flask
import os

# Bot Config
BOT_TOKEN = "8867616150:AAE6qoHzxnec38o-I5z3NIp-juQeXqSJd4A"
ADMIN_ID = 72660672019

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# State Management
maintenance_mode = False
user_api_keys = {}
user_active_orders = {} 
search_flags = {} 

# Checker API Config
CHECKER_URL = "http://api.agbots.site:8080/check/"
CHECKER_AUTH = "user8354"
CHECKER_API_KEY = "SIGUzg7Xf7euGs8B"

STATUS_EMOJIS = {
    "unoccupied": "✅ Fresh",
    "fresh": "✅ Fresh",
    "clean": "✅ Fresh",
    "ok": "✅ Fresh",
    "banned": "🚫 Banned",
    "flood": "🚫 Banned",
    "occupied": "❌ Registered",
    "registered": "❌ Registered",
    "used": "❌ Registered",
    "locked": "🔒 Locked",
    "2fa": "🔒 Locked",
    "password": "🔒 Locked"
}

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 Buy Number"), KeyboardButton("🟢 Active Numbers"))
    markup.add(KeyboardButton("👤 Profile"))
    return markup

def check_tg_number(phone_number):
    if not phone_number.startswith("+"):
        query_number = "+" + phone_number
    else:
        query_number = phone_number
        
    payload = {
        "auth": CHECKER_AUTH,
        "api_key": CHECKER_API_KEY,
        "phone_numbers": [query_number]
    }
    
    try:
        response = requests.get(CHECKER_URL, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if str(data.get("status")) == "200":
                result_obj = data.get("result_obj", {})
                
                raw_status = result_obj.get(query_number) or result_obj.get(query_number.replace("+", ""))
                if not raw_status:
                    return "⚠️ Check Failed"
                    
                status_str = str(raw_status).lower().strip()
                
                fresh_signals = ["unoccupied", "phone_number_unoccupied", "unregistered", "not_registered", "not_occupied", "free", "fresh", "available", "ready", "allow", "ok", "valid", "clean", "false", "0", "no_account", "does_not_exist"]
                if any(s in status_str for s in fresh_signals):
                    return "✅ Fresh"
                    
                locked_signals = ["flood", "locked", "lock", "wait", "restricted", "2fa", "password", "has_password"]
                if any(s in status_str for s in locked_signals):
                    return "🔒 Locked"
                    
                banned_signals = ["banned", "ban", "blocked"]
                if any(s in status_str for s in banned_signals) and "not_" not in status_str:
                    return "🚫 Banned"
                    
                registered_signals = ["occupied", "phone_number_occupied", "registered", "taken", "used", "true", "1"]
                if any(s in status_str for s in registered_signals):
                    return "❌ Registered"
                    
                return "⚠️ Check Failed"
                
    except requests.RequestException:
        pass
    
    return "⚠️ Check Failed"

def wait_for_otp(chat_id, user_id, api_key, activation_id, phone_number):
    url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
    
    for _ in range(60): 
        if user_id not in user_active_orders or activation_id not in user_active_orders.get(user_id, {}):
            return

        time.sleep(5)
        try:
            res = requests.get(url, timeout=10)
            response_text = res.text
            
            if response_text.startswith("STATUS_OK"):
                otp = response_text.split(":")[1]
                
                if user_id in user_active_orders and activation_id in user_active_orders[user_id]:
                    del user_active_orders[user_id][activation_id]
                
                text = f"✅ **OTP Received!**\n\n🇨🇴 Telegram `{phone_number}`"
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(text=f"{otp}", copy_text=CopyTextButton(text=otp)))
                
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
                return
            elif response_text == "STATUS_CANCEL":
                if user_id in user_active_orders and activation_id in user_active_orders[user_id]:
                    del user_active_orders[user_id][activation_id]
                bot.send_message(chat_id, f"❌ Automatically Cancelled: `{phone_number}`", parse_mode="Markdown")
                return
        except Exception:
            pass
            
    if user_id in user_active_orders and activation_id in user_active_orders[user_id]:
        del user_active_orders[user_id][activation_id]
    bot.send_message(chat_id, f"⏱ Timeout! Kono OTP asheni: `{phone_number}`", parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_command(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    text = "Bot e swagotom! 🚀\n\nNicher menu theke tomar proyojoniyo option bachai koro."
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    args = message.text.split()
    global maintenance_mode
    
    if len(args) > 1:
        if args[1].lower() == "on":
            maintenance_mode = True
            bot.send_message(message.chat.id, "🛠 Maintenance mode ON kora hoyeche.")
        elif args[1].lower() == "off":
            maintenance_mode = False
            bot.send_message(message.chat.id, "✅ Maintenance mode OFF kora hoyeche.")

# ----------------- BUTTON HANDLERS -----------------

@bot.message_handler(func=lambda message: message.text == "👤 Profile")
def profile_handler(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    api_key = user_api_keys.get(message.from_user.id)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔑 Change API Key", callback_data="set_api_key"))
    
    if not api_key:
        bot.send_message(message.chat.id, "⚠️ Tomar kono API Key set kora nei.\nNicher button e click kore API key set koro.", reply_markup=markup, parse_mode="Markdown")
        return
        
    bot.send_message(message.chat.id, "Checking profile info... ⏳")
    
    url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    try:
        res = requests.get(url, timeout=15)
        text = res.text
        if text.startswith("ACCESS_BALANCE"):
            ruble_bal = float(text.split(":")[1])
            usd_bal = round(ruble_bal / 92.5, 2)
            
            profile_text = f"👤 **Tomar Profile**\n\n"
            profile_text += f"🔑 **API Key:** `{api_key[:5]}...{api_key[-5:]}`\n"
            profile_text += f"💰 **Balance:** **${usd_bal} USD** *(Approx {ruble_bal} RUB)*"
            
            bot.send_message(message.chat.id, profile_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"❌ Profile load korte problem hocche: `{text}`", reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ API theke response ashte problem hoyeche.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_api_key")
def set_api_key_callback(call):
    msg = bot.send_message(call.message.chat.id, "✏️ Tomar notun API Key ti ekhane type kore pathao:")
    bot.register_next_step_handler(msg, process_api_key_step)
    
def process_api_key_step(message):
    user_api_keys[message.from_user.id] = message.text.strip()
    bot.send_message(message.chat.id, "✅ API key successfully set kora hoyeche!", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "🟢 Active Numbers")
def active_handler(message):
    user_id = message.from_user.id
    orders = user_active_orders.get(user_id, {})
    
    if not orders:
        bot.send_message(message.chat.id, "Tomar ekhon kono active order nei.")
        return
        
    text = "🟢 **Tomar Active Number Gula:**\n*(Cancel korte nicher button e tap koro)*"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for act_id, phone in list(orders.items()):
        markup.add(InlineKeyboardButton(text=f"Cancel {phone} ❌", callback_data=f"cancel_{act_id}_{phone}"))
        
    if len(orders) > 1:
        markup.add(InlineKeyboardButton(text="Cancel All ❌", callback_data="cancelall"))
        
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🛒 Buy Number")
def buy_handler(message):
    if maintenance_mode and message.from_user.id != ADMIN_ID:
        return
        
    api_key = user_api_keys.get(message.from_user.id)
    if not api_key:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="🔑 Set API Key", callback_data="set_api_key"))
        bot.send_message(message.chat.id, "⚠️ Number kinar aage API key set korte hobe.", reply_markup=markup, parse_mode="Markdown")
        return
        
    msg = bot.send_message(message.chat.id, "Koyta Fresh number kinte chao? (Jemon: 1, 5, 10)")
    bot.register_next_step_handler(msg, process_buy_amount_init, api_key)

# ----------------- CALL BACKS & AUTO GRABBER -----------------

@bot.callback_query_handler(func=lambda call: call.data == "cancelall")
def cancel_all_callback(call):
    user_id = call.from_user.id
    api_key = user_api_keys.get(user_id)
    
    if not api_key:
        bot.answer_callback_query(call.id, "API key pawa jayni!", show_alert=True)
        return
        
    orders = user_active_orders.get(user_id, {})
    if not orders:
        bot.answer_callback_query(call.id, "Kono active order nei!", show_alert=True)
        return
        
    bot.answer_callback_query(call.id, "Shob cancel kora hocche... Please wait ⏳")
    
    for act_id, phone in list(orders.items()):
        cancel_url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=8&id={act_id}"
        try:
            requests.get(cancel_url, timeout=5)
        except Exception:
            pass
            
    user_active_orders[user_id] = {}
    bot.edit_message_text("✅ Tomar shob active number eksathe cancel & refund kora hoyeche!", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_order_callback(call):
    parts = call.data.split("_")
    act_id = parts[1]
    phone = parts[2]
    user_id = call.from_user.id
    
    api_key = user_api_keys.get(user_id)
    if not api_key:
        bot.answer_callback_query(call.id, "API key pawa jayni!", show_alert=True)
        return
        
    cancel_url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=8&id={act_id}"
    
    try:
        requests.get(cancel_url, timeout=10)
        
        if user_id in user_active_orders and act_id in user_active_orders[user_id]:
            del user_active_orders[user_id][act_id]
            
        bot.answer_callback_query(call.id, f"{phone} Cancel kora hoyeche & Taka Refund hoyeche!", show_alert=True)
        
        orders = user_active_orders.get(user_id, {})
        if not orders:
            bot.edit_message_text("✅ Tomar shob active number cancel hoye geche.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            text = "🟢 **Tomar Active Number Gula:**\n*(Cancel korte nicher button e tap koro)*"
            markup = InlineKeyboardMarkup(row_width=1)
            for a_id, p_num in list(orders.items()):
                markup.add(InlineKeyboardButton(text=f"Cancel {p_num} ❌", callback_data=f"cancel_{a_id}_{p_num}"))
            
            if len(orders) > 1:
                markup.add(InlineKeyboardButton(text="Cancel All ❌", callback_data="cancelall"))
                
            bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            
    except Exception:
        bot.answer_callback_query(call.id, "API er sathe connect kora jayni.", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("stopsearch_"))
def stop_search_callback(call):
    search_id = call.data.split("_")[1]
    search_flags[search_id] = False
    bot.answer_callback_query(call.id, "🛑 Search stop kora hocche...")


def process_buy_amount_init(message, api_key):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Sothik number dewa hoyni. Abar try koro.")
        return
        
    amount = int(message.text)
    if amount <= 0:
        bot.send_message(message.chat.id, "Amount 0 er cheye beshi hote hobe.")
        return
        
    if amount > 10:
        bot.send_message(message.chat.id, "Auto-grab mode e eksathe max 10 ta number order kora jabe. 10 ta processing hocche...")
        amount = 10
        
    search_id = f"{message.chat.id}{int(time.time())}"
    search_flags[search_id] = True
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Cancel Search ❌", callback_data=f"stopsearch_{search_id}"))
    
    text = f"🛒 **Tomar Order List:**\n\n"
    msg = bot.send_message(message.chat.id, text + "🔍 Fresh Number khujchi... ⏳", parse_mode="Markdown", reply_markup=markup)
    
    threading.Thread(target=auto_grab_task, args=(message.from_user.id, message.chat.id, api_key, amount, msg, text, search_id)).start()


def auto_grab_task(user_id, chat_id, api_key, amount, msg, base_text, search_id):
    if user_id not in user_active_orders:
        user_active_orders[user_id] = {}
        
    buy_url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getNumber&service=tg&country=33&maxPrice=0.12"
    
    for i in range(amount):
        attempt = 0
        
        while search_flags.get(search_id, False):
            attempt += 1
            try:
                res = requests.get(buy_url, timeout=30)
                response_text = res.text
                
                if response_text.startswith("ACCESS_NUMBER"):
                    parts = response_text.split(":")
                    activation_id = parts[1]
                    phone_number = parts[2]
                    
                    emoji_status = check_tg_number(phone_number)
                    
                    if "✅ Fresh" in emoji_status:
                        base_text += f"{i+1}. `{phone_number}` {emoji_status}\n"
                        user_active_orders[user_id][activation_id] = phone_number
                        
                        markup = InlineKeyboardMarkup()
                        markup.add(InlineKeyboardButton(text="Cancel Search ❌", callback_data=f"stopsearch_{search_id}"))
                        
                        bot.edit_message_text(base_text + f"\n⏳ Baki gula khujchi... ({i+1}/{amount})", chat_id=chat_id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=markup)
                        threading.Thread(target=wait_for_otp, args=(chat_id, user_id, api_key, activation_id, phone_number)).start()
                        
                        break 
                    else:
                        # ⚠️ EKHANE 2.5 SECOND ER DELAY ADD KORA HOYECHE ⚠️
                        # Jate API server number ta database e properly save korar time pay
                        time.sleep(2.5) 

                        cancel_url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=setStatus&status=8&id={activation_id}"
                        try:
                            requests.get(cancel_url, timeout=5)
                        except:
                            pass
                        
                        temp_text = base_text + f"\n♻️ `{phone_number}` ({emoji_status}), Auto Cancel.\n🔍 Notun khujchi... (Attempt {attempt})"
                        
                        markup = InlineKeyboardMarkup()
                        markup.add(InlineKeyboardButton(text="Cancel Search ❌", callback_data=f"stopsearch_{search_id}"))
                        
                        bot.edit_message_text(temp_text, chat_id=chat_id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=markup)
                        
                        # API rate limit erate porer bar number khujar age aro 1 sec wait
                        time.sleep(1) 
                        
                else:
                    if response_text in ["NO_BALANCE", "BAD_KEY", "NO_KEY"]:
                        base_text += f"\n⚠️ API Error: `{response_text}`. Khonja stop kora holo."
                        search_flags[search_id] = False
                        break
                    elif response_text == "NO_NUMBERS":
                        temp_text = base_text + f"\n⚠️ Ekhon kono number nei. Wait kore abar try korchi... (Attempt {attempt})"
                        markup = InlineKeyboardMarkup()
                        markup.add(InlineKeyboardButton(text="Cancel Search ❌", callback_data=f"stopsearch_{search_id}"))
                        bot.edit_message_text(temp_text, chat_id=chat_id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=markup)
                        time.sleep(5)
                    else:
                        base_text += f"{i+1}. ❌ Failed (`{response_text}`)\n"
                        break
                        
            except Exception:
                time.sleep(3) 
                
        if not search_flags.get(search_id, False):
            break
            
    bot.edit_message_text(base_text + "\n✅ **Order Process Complete / Stopped!**\nManage/Cancel korte menu theke `🟢 Active Numbers` e tap koro.", chat_id=chat_id, message_id=msg.message_id, parse_mode="Markdown")

# --- Render Dummy Server ---
@app.route('/')
def index():
    return "Bot is running on Polling mode!"

def run_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
