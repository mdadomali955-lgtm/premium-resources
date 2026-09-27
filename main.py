import os
import time
import requests
import telebot
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from flask import Flask, request, jsonify
from threading import Thread

# --- Konfigaresan o bot token ---
BOT_TOKEN = "8815920877:AAFGwxjKGoo9HhcsVOcbBhi9JMqXT-LLMsY"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"

# Render-nisvanta URL
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}
broadcast_sessions = {}
ban_sessions = {}
promo_sessions = {}
user_inspect_sessions = {}

# --- Flask server o webhook rout ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly with Webhook!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@app.route('/verify-channel/<int:user_id>', methods=['GET'])
def verify_channel_member(user_id):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            res = jsonify({"joined": True})
        else:
            res = jsonify({"joined": False})
    except Exception as e:
        res = jsonify({"joined": False, "error": str(e)})

    res.headers.add("Access-Control-Allow-Origin", "*")
    return res, 200

def is_user_banned(user_id):
    try:
        banned = requests.get(f"{FIREBASE_BASE}/banned_users/{user_id}.json").json()
        return bool(banned)
    except Exception:
        return False

def is_user_member(user_id):
    if int(user_id) == int(ADMIN_ID):
        return True
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True

def get_force_sub_keyboard(target_arg=""):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📢 Channel-alli jayen karun", url=CHANNEL_URL),
        InlineKeyboardButton("🔄 Verify karun", callback_data=f"check_sub:{target_arg}")
    )
    return markup

def get_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 Premium resource 💎", web_app=WebAppInfo(url=WEB_APP_URL)))
    return markup

def get_admin_dashboard_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("➕ Hosa resource jukta karun"),
        KeyboardButton("✏️ Resource edit/update"),
        KeyboardButton("🪙 Coin update/manage"),
        KeyboardButton("📊 Download history nodi"),
        KeyboardButton("📢 Broadcast message"),
        KeyboardButton("🚫 User ban/unban"),
        KeyboardButton("🎁 Promo code tayari"),
        KeyboardButton("🔍 User check"),
        KeyboardButton("📢 Advertisement set karun"),
        KeyboardButton("❌ Cancel karun")
    )
    return markup

def get_file_collection_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("✅ Upload sampurna"),
        KeyboardButton("❌ Cancel karun")
    )
    return markup

def cancel_process(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    uid = message.from_user.id
    for s_dict in [admin_temp_data, edit_sessions, coin_sessions, broadcast_sessions, ban_sessions, promo_sessions, user_inspect_sessions]:
        if uid in s_dict:
            del s_dict[uid]

    if int(uid) == int(ADMIN_ID):
        bot.send_message(message.chat.id, "❌ Calana prakriya cancel madalagide.", reply_markup=get_admin_dashboard_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Cancel madalagide.", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['add_xml', 'xml', 'add_plp', 'plp', 'add_font', 'font'])
def handle_direct_add_commands(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return

    cmd = message.text.split()[0].replace('/', '').lower()
    cat_type = 'xml' if 'xml' in cmd else ('plp' if 'plp' in cmd else 'font')

    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'type': cat_type, 'file_ids': []}

    cat_title = "⚡ XML project" if cat_type == 'xml' else ("🎨 PLP project" if cat_type == 'plp' else "🔤 Font file")
    msg = bot.send_message(
        message.chat.id,
        f"✅ Command sweekarisalagide: *{cat_title}*\n\nIga resource-ina hesaru bareda kalsi:\n(Cancel madalu /cancel odi)",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_name)

@bot.message_handler(commands=['download_logs', 'logs'])
def show_download_logs_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return

    try:
        res = requests.get(f"{FIREBASE_BASE}/download_logs.json").json()
        if not res:
            bot.reply_to(message, "📂 Innu yavude download record jama agilla.")
            return

        log_text = "📊 **Koneya 10 download history:**\n\n"
        items = list(res.items())[-10:]
        for key, log in items:
            log_text += (
                f"👤 User: *{log.get('user_name', 'Unknown')}*\n"
                f"🆔 ID: `{log.get('user_id')}`\n"
                f"📦 File: {log.get('resource_name')}\n"
                f"⏰ Samaya: {log.get('time')}\n"
                f"-----------------------------------\n"
            )
        bot.reply_to(message, log_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Log load madalu samasye agide: {e}")

def start_broadcast_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(
        message,
        "📢 **Broadcast message panel**\n\nElla user-galige kalsalu icchisuva message athava notice bareda kalsi:",
        parse_mode="Markdown",
        reply_markup=get_admin_dashboard_keyboard()
    )
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    users_data = requests.get(f"{FIREBASE_BASE}/users.json").json()
    if not users_data:
        bot.reply_to(message, "⚠️ Database-alli yava user sikkilla!", reply_markup=get_admin_dashboard_keyboard())
        return

    sent_count = 0
    fail_count = 0

    wait_msg = bot.reply_to(message, "⏳ Broadcast message kalsalaguttide, dayavittu kayiri...")

    for uid in users_data.keys():
        try:
            if message.content_type == 'text':
                bot.send_message(uid, f"📢 **Official notice:**\n\n{message.text}", parse_mode="Markdown")
            elif message.content_type == 'photo':
                bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "", parse_mode="Markdown")
            elif message.content_type == 'video':
                bot.send_video(uid, message.video.file_id, caption=message.caption or "", parse_mode="Markdown")
            elif message.content_type == 'document':
                bot.send_document(uid, message.document.file_id, caption=message.caption or "", parse_mode="Markdown")
            sent_count += 1
            time.sleep(0.1)
        except Exception:
            fail_count += 1

    bot.delete_message(message.chat.id, wait_msg.message_id)
    bot.reply_to(
        message,
        f"✅ **Broadcast sampurna vagide!**\n\n"
        f"📤 Successfully kalsalagide: *{sent_count}* janarige\n"
        f"⚠️ Fail agide: *{fail_count}* janarige",
        parse_mode="Markdown",
        reply_markup=get_admin_dashboard_keyboard()
    )

def start_ban_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 User ban madun", callback_data="ban_action:ban"),
        InlineKeyboardButton("✅ User unban madun", callback_data="ban_action:unban")
    )
    bot.send_message(message.chat.id, "🚫 **User management panel**\n\nNeevu en madalu icchisuteera?", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ban_action:'))
def handle_ban_action(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    action = call.data.split(":")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    ban_sessions[call.from_user.id] = {'action': action}

    txt = "🚫 Yaava user-ina ID ban madalu icchisuteera adu bareda kalsi:" if action == "ban" else "✅ Yaava user-ina ID unban madalu icchisuteera adu bareda kalsi:"
    msg = bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_ban_unban_id)

def process_ban_unban_id(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    uid = message.from_user.id
    if uid not in ban_sessions:
        return

    action = ban_sessions[uid]['action']
    target_id = message.text.strip()
    del ban_sessions[uid]

    if action == "ban":
        requests.put(f"{FIREBASE_BASE}/banned_users/{target_id}.json", json=True)
        bot.reply_to(message, f"🚫 User ID `{target_id}` successagi ban madalagide!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    else:
        requests.delete(f"{FIREBASE_BASE}/banned_users/{target_id}.json")
        bot.reply_to(message, f"✅ User ID `{target_id}` unban madalagide!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())

def start_promo_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(message, "🎁 Hosa promo code-ina hesaru bareda kalsi (udaharanage: `FREECOIN50`):", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(msg, get_promo_code_name)

def get_promo_code_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    code = message.text.strip().upper()
    promo_sessions[message.from_user.id] = {'code': code}
    msg = bot.reply_to(message, f"🪙 Code: *{code}*\n\nEe code use madidre user eshtu coin padeyuttane enba sankhye bareda kalsi (udaharanage: 100):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_promo_code_amount)

def get_promo_code_amount(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    uid = message.from_user.id
    if uid not in promo_sessions:
        return

    try:
        coins = int(message.text.strip())
        code = promo_sessions[uid]['code']
        del promo_sessions[uid]

        requests.put(f"{FIREBASE_BASE}/promo_codes/{code}.json", json={"coins": coins, "used_by": {}})
        bot.reply_to(
            message,
            f"🎉 **Promo code successagi tayaragide!**\n\n"
            f"🎁 Code: `{code}`\n"
            f"🪙 Coin bele: *{coins}*\n\n"
            f"User-galu `/redeem {code}` antu use madabahudu.",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "⚠️ Coin sankhye roopadalli irabekku. Matte bareda kalsi:")
        bot.register_next_step_handler(message, get_promo_code_amount)

@bot.message_handler(commands=['redeem'])
def redeem_promo_code(message):
    args = message.text.split()
    uid = message.from_user.id
    if is_user_banned(uid):
        return

    if len(args) < 2:
        bot.reply_to(message, "⚠️ Balake: `/redeem [promo_code]`\nUdaharanage: `/redeem FREECOIN50`", parse_mode="Markdown")
        return

    code = args[1].strip().upper()
    try:
        p_data = requests.get(f"{FIREBASE_BASE}/promo_codes/{code}.json").json()
        if not p_data:
            bot.reply_to(message, "❌ Thappu athava expired promo code!")
            return

        used_by = p_data.get('used_by') or {}
        if str(uid) in used_by:
            bot.reply_to(message, "⚠️ Neevu eegaagale ee promo code use madiddire!")
            return

        u_data = requests.get(f"{FIREBASE_BASE}/users/{uid}.json").json() or {}
        cur_coins = u_data.get('coins', 0)
        coins_to_add = p_data.get('coins', 0)
        new_coins = cur_coins + coins_to_add

        requests.patch(f"{FIREBASE_BASE}/users/{uid}.json", json={"coins": new_coins})

        used_by[str(uid)] = True
        requests.patch(f"{FIREBASE_BASE}/promo_codes/{code}.json", json={"used_by": used_by})

        bot.reply_to(
            message,
            f"🎉 Abhinandanagalu! Promo code successagi redeem agide.\n"
            f"Nimma account-ige jukta vagide *{coins_to_add}* coin!\n"
            f"Prastuta balance: *{new_coins} 🪙*",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Dosha undagide: {e}")

def start_user_inspect_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(message, "🔍 Yaava user-ina mahiti nodalu icchisuteera avara **Telegram User ID** bareda kalsi:", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(msg, process_user_inspection)

def process_user_inspection(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    target_id = message.text.strip()
    try:
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json()
        if not u_data:
            bot.reply_to(message, f"❌ ID `{target_id}` database-alli sikkilla!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
            return

        banned = is_user_banned(target_id)
        status_text = "🚫 Ban madalagide" if banned else "✅ Sacha (Active)"

        info = (
            f"👤 **User profile mahiti**\n\n"
            f"📌 Hesaru: {u_data.get('name', 'Unknown')}\n"
            f"🔗 Username: @{u_data.get('username', 'None')}\n"
            f"🆔 ID: `{target_id}`\n"
            f"🪙 Prastuta coin: {u_data.get('coins', 0)}\n"
            f"👥 Mot refer: {u_data.get('refers', 0)}\n"
            f"⚙️ Status: {status_text}"
        )
        bot.reply_to(message, info, parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ Mahiti load madalu samasye agide: {e}", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())

def start_coin_management_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👑 Nanna sontha coin set madun", callback_data="coin_act:self"),
        InlineKeyboardButton("👤 Verre user-ige coin kodi/kammadi", callback_data="coin_act:other")
    )
    bot.send_message(
        message.chat.id,
        "🪙 **Coin management panel**\n\nNeevu sontha coin update madalu icchisuteera athava yaru user-ige coin kodalu icchisuteera?",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('coin_act:'))
def handle_coin_action(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    act = call.data.split(":")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)

    if act == "self":
        msg = bot.send_message(
            call.message.chat.id,
            "👑 **Nimma account-alli eshtu coin set madalu icchisuteera?**\n(Udaharanage: `2000` bareda kalsi athava '❌ Cancel karun' odi)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_self_coins)
    else:
        msg = bot.send_message(
            call.message.chat.id,
            "👤 **Yaava user-ige coin kodalu icchisuteera avara Telegram User ID bareda kalsi:**\n(Cancel madalu '❌ Cancel karun' odi)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_user_id_for_coins)

def process_self_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    try:
        amount = int(message.text.strip())
        requests.patch(f"{FIREBASE_BASE}/users/{ADMIN_ID}.json", json={"coins": amount})
        bot.reply_to(
            message,
            f"🎉 Nimma account-alli successagi *{amount} 🪙* coin set madalagide!",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "⚠️ Coin sankhye roopadalli kodi. Matte bareda kalsi:")
        bot.register_next_step_handler(message, process_self_coins)

def process_user_id_for_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    target_id = message.text.strip()
    u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json()
    if not u_data:
        bot.reply_to(message, f"❌ ID `{target_id}` database-alli kandu bandilla! Sariya ada ID kodi:")
        bot.register_next_step_handler(message, process_user_id_for_coins)
        return

    coin_sessions[message.from_user.id] = {'target_id': target_id, 'user_name': u_data.get('name', 'User')}
    msg = bot.send_message(
        message.chat.id,
        f"✅ User sikkiddare: *{u_data.get('name', 'User')}* (Prastuta coin: {u_data.get('coins', 0)})\n\n"
        f"🪙 **Eshtu coin jukta athava kaledu hakalu icchisuteera?** (Udaharanage: Jukta madalu `500` athava kaledu hakalu `-200`):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_apply_coins)

def process_apply_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    user_id = message.from_user.id
    if user_id not in coin_sessions:
        return

    try:
        amount = int(message.text.strip())
        target_id = coin_sessions[user_id]['target_id']
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json() or {}

        current_c = u_data.get('coins', 0)
        updated_c = max(0, current_c + amount)
        requests.patch(f"{FIREBASE_BASE}/users/{target_id}.json", json={"coins": updated_c})

        del coin_sessions[user_id]
        bot.reply_to(
            message,
            f"🎉 **Successagi sampurna vagide!**\n\n"
            f"👤 User: {u_data.get('name', 'User')}\n"
            f"🆔 ID: `{target_id}`\n"
            f"🪙 Muncheya coin: {current_c}\n"
            f"✨ Prastuta coin: *{updated_c}*",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )

        try:
            bot.send_message(
                target_id,
                f"🎁 **Admin-inda coin update!**\n\nNimma account-ige *{amount}* coin jukta madalagide.\nPrastuta balance: *{updated_c} 🪙*",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    except ValueError:
        bot.reply_to(message, "⚠️ Coin sankhye roopadalli kodi (udaharanage: 500). Matte bareda kalsi:")
        bot.register_next_step_handler(message, process_apply_coins)

@bot.message_handler(commands=['mycoins'])
def set_admin_my_coins_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    args = message.text.split()
    amount = 2000
    if len(args) > 1:
        try:
            amount = int(args[1].strip())
        except ValueError:
            bot.reply_to(message, "⚠️ Coin sankhye roopadalli kodi. Daharanage: `/mycoins 2500`", parse_mode="Markdown")
            return

    try:
        requests.patch(f"{FIREBASE_BASE}/users/{ADMIN_ID}.json", json={"coins": amount})
        bot.reply_to(message, f"🎉 Nimma account-alli successagi *{amount} 🪙* coin set madalagide!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Database error: {e}")

@bot.message_handler(commands=['givecoins'])
def give_user_coins_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Balake: `/givecoins [User_ID] [Coins]`\nUdaharanage: `/givecoins 7481264433 500`", parse_mode="Markdown")
        return

    target_uid = args[1].strip()
    try:
        coins_to_add = int(args[2].strip())
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_uid}.json").json()
        if not u_data:
            bot.reply_to(message, f"❌ ID `{target_uid}` kandu bandilla!")
            return

        current_c = u_data.get('coins', 0)
        updated_c = max(0, current_c + coins_to_add)
        requests.patch(f"{FIREBASE_BASE}/users/{target_uid}.json", json={"coins": updated_c})
        bot.reply_to(message, f"✅ Success! Prastuta coin: *{updated_c}*", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠️ Coin sankhye roopadalli kodi.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_sub:'))
def handle_verify_subscription(call):
    user_id = call.from_user.id
    target_arg = call.data.split("check_sub:")[1]

    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ Neevu ee bot-inda ban agiddire!", show_alert=True)
        return

    if is_user_member(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Verification success agide!", show_alert=False)

        if target_arg.startswith("get_"):
            process_resource_delivery(call.message.chat.id, target_arg, call.from_user)
        else:
            bot.send_message(
                call.message.chat.id,
                f"👋 Swagatam {call.from_user.first_name}!\n\n💎 Premium resource app-ige swagatam. Kelagina button otti app open madi:",
                reply_markup=get_main_keyboard()
            )
    else:
        bot.answer_callback_query(call.id, "❌ Neevu innu channel-alli jayen agilla! Munde jayen agi.", show_alert=True)

def process_resource_delivery(chat_id, arg_text, user_obj=None):
    file_key = arg_text.replace("get_", "").split("_from_")[0]
    bot.send_message(chat_id, "⏳ Nimma file siddha madalaguttide...")
    try:
        res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
        item = res.json()
        if item:
            res_name = item.get('name', 'Resource')
            res_type = item.get("type", "plp").upper()

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if user_obj:
                try:
                    log_data = {
                        "user_id": user_obj.id,
                        "user_name": user_obj.first_name,
                        "resource_name": res_name,
                        "category": res_type,
                        "time": current_time
                    }
                    requests.post(f"{FIREBASE_BASE}/download_logs.json", json=log_data)

                    admin_alert = (
                        f"🔔 **Hosa file download agide!**\n\n"
                        f"👤 User: *{user_obj.first_name}*\n"
                        f"🆔 User ID: `{user_obj.id}`\n"
                        f"📦 Resource: {res_name}\n"
                        f"📁 Category: {res_type}\n"
                        f"⏰ Samaya: {current_time}"
                    )
                    bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
                except Exception:
                    pass

            if item.get("download_link"):
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📥 Direct file download madi", url=item["download_link"]))
                markup.add(InlineKeyboardButton("🚀 Punah app open madi", web_app=WebAppInfo(url=WEB_APP_URL)))
                bot.send_message(
                    chat_id,
                    f"🎁 Nimma resource: *{res_name}*\n"
                    f"📁 Category: *{res_type}*\n"
                    f"🪙 Upayogisida coin: {item.get('coins', 0)}\n\n"
                    "🔗 Kelagina button otti file sangraha madi:",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return

            file_ids = item.get("file_ids") or ([] if not item.get("file_id") else [item.get("file_id")])
            if file_ids:
                total_f = len(file_ids)
                for idx, fid in enumerate(file_ids, 1):
                    cap = (
                        f"🎁 File ({idx}/{total_f}): *{res_name}*\n"
                        f"📁 Category: *{res_type}*\n\n"
                        "📂 Save madalu file mele tap madi o download konedalli 3-dot (⋮) otti **'Save to Downloads'** madi."
                    )
                    bot.send_document(chat_id, fid, caption=cap, parse_mode="Markdown")
                    time.sleep(0.3)
                bot.send_message(chat_id, "✅ Nimma ella file successagi inbox-ige delivery madalagide!", reply_markup=get_main_keyboard())
                return
        else:
            bot.send_message(chat_id, "❌ File database-alli kandu bandilla.", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ Resource delivery-alli samasye kanisikolluttide: {e}", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "❌ Dukhadavagide, neevu ee bot-inda ban agiddire!")
        return

    try:
        u_res = requests.get(f"{FIREBASE_BASE}/users/{user_id}.json").json()
        if not u_res:
            requests.put(f"{FIREBASE_BASE}/users/{user_id}.json", json={
                "name": user_name,
                "username": message.from_user.username or "",
                "coins": 20,
                "refers": 0,
                "daily_ads": {}
            })
    except Exception:
        pass

    if len(args) > 1 and args[1].startswith("get_"):
        process_resource_delivery(message.chat.id, args[1], message.from_user)
        return

    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if str(referrer_id) != str(user_id):
            try:
                ref_data = requests.get(f"{FIREBASE_BASE}/users/{referrer_id}.json").json()
                if ref_data:
                    requests.patch(f"{FIREBASE_BASE}/users/{referrer_id}.json", json={
                        "coins": ref_data.get('coins', 0) + 50,
                        "refers": ref_data.get('refers', 0) + 1
                    })
                    bot.send_message(referrer_id, "🎉 Abhinandanagalu! Hosa member nimma refer-alli jayen agiddare. Neevu padediddiri +50 🪙 coin!")
            except Exception:
                pass

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👑 **Swagatam admin panel-ige!**\n\n"
            "Kelagina button athava command upayogisi yavude kelasa nirvahisabahudu:",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
        bot.send_message(message.chat.id, "Mini app-ige hogalu kelagina button otti:", reply_markup=get_main_keyboard())
        return

    target_arg = args[1] if len(args) > 1 else ""
    if not is_user_member(user_id):
        bot.send_message(
            message.chat.id,
            f"👋 Hello *{user_name}*!\n\n"
            "⚠️ **Bot mattu mini app upayogisalu namma official telegram channel-alli jayen agiruvudu kaddaya.**\n\n"
            "👉 Kelagina button click madi channel-alli jayen agi mattu nantara **'🔄 Verify karun'** button otti:",
            parse_mode="Markdown",
            reply_markup=get_force_sub_keyboard(target_arg)
        )
        return

    bot.send_message(
        message.chat.id,
        f"👋 Hello {user_name}!\n\n💎 Premium resource app-ige swagatam. Kelagina button otti app open madi:",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda m: int(m.from_user.id) == int(ADMIN_ID) and m.text and not m.reply_to_message)
def handle_all_admin_text(message):
    text = message.text.strip().lower()

    if text in ['/cancel', 'cancel', 'badal', '❌ Cancel karun']:
        cancel_process(message)
        return

    if text in ['/edit', 'edit', 'edit', '✏️ Resource edit/update', 'update']:
        start_edit_flow(message)
        return

    if text in ['/add', 'add', 'jokta', '➕ Hosa resource jukta karun']:
        start_add_flow(message)
        return

    if text in ['🪙 Coin update/manage', 'coin', 'coins', '/coins']:
        start_coin_management_flow(message)
        return

    if text in ['📊 Download history nodi', 'logs', 'download_logs', '/logs']:
        show_download_logs_cmd(message)
        return

    if text in ['📢 Broadcast message', 'broadcast', '/broadcast']:
        start_broadcast_flow(message)
        return

    if text in ['🚫 User ban/unban', 'ban', '/ban']:
        start_ban_flow(message)
        return

    if text in ['🎁 Promo code tayari', 'promo', '/promo']:
        start_promo_flow(message)
        return

    if text in ['🔍 User check', 'inspect', '/inspect']:
        start_user_inspect_flow(message)
        return

    if text in ['/setad', 'setad', 'vijnapan', '📢 Advertisement set karun']:
        start_ad_flow(message)
        return

def start_edit_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    edit_sessions[message.from_user.id] = {}

    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP", callback_data="edcat:plp"),
        InlineKeyboardButton("🔤 Font", callback_data="edcat:font"),
        InlineKeyboardButton("⚡ XML", callback_data="edcat:xml")
    )
    bot.send_message(message.chat.id, "🛠️ **Yava category-ina file update madalu icchisuteera?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edcat:'))
def handle_edit_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    edit_sessions[call.from_user.id] = {'type': cat}
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(
        call.message.chat.id,
        f"✅ Ayke madiro category: *{cat.upper()}*\n\n"
        "Iga yaava file update madalu icchisuteera adara **hesaru athava hesarina kelavu bhaga** bareda kalsi:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, find_resource_by_name)

def find_resource_by_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    search_name = (message.text or "").strip().lower()
    selected_type = edit_sessions.get(message.from_user.id, {}).get('type', 'plp')

    wait_msg = bot.reply_to(message, "🔍 Database-alli file hudukalaguttide...")

    try:
        res = requests.get(f"{FIREBASE_BASE}/resources.json").json() or {}
        bot.delete_message(message.chat.id, wait_msg.message_id)

        matched_items = {}
        for key, item in res.items():
            if item.get('type') == selected_type:
                res_name = item.get('name', '').lower()
                if search_name in res_name:
                    matched_items[key] = item

        if not matched_items:
            msg = bot.send_message(
                message.chat.id,
                f"❌ *{selected_type.upper()}* category-alli '{message.text}' hesarina file sikkilla!\n\n"
                "Sariya ada hesaru bareda matte kalsi (athava '❌ Cancel karun' odi):",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, find_resource_by_name)
            return

        if len(matched_items) == 1:
            res_key = list(matched_items.keys())[0]
            item_data = matched_items[res_key]
            show_edit_options(message.chat.id, res_key, item_data)
        else:
            markup = InlineKeyboardMarkup(row_width=1)
            for k, it in matched_items.items():
                markup.add(InlineKeyboardButton(f"📁 {it.get('name')}", callback_data=f"selres:{k}"))
            bot.send_message(message.chat.id, "🎯 Halavaru file-galu siktive. Nirdista file ayke madi:", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ Dosha: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('selres:'))
def select_from_matched(call):
    res_key = call.data.split(":")[1]
    res_data = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json").json()
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_edit_options(call.message.chat.id, res_key, res_data)

def show_edit_options(chat_id, res_key, item_data):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 Hesaru badalavane", callback_data=f"do_upd:{res_key}:name"),
        InlineKeyboardButton("🪙 Coin badalavane", callback_data=f"do_upd:{res_key}:coins")
    )

    r_type = item_data.get('type')
    if r_type == 'xml':
        markup.add(
            InlineKeyboardButton("🎬 Preview video badalavane", callback_data=f"do_upd:{res_key}:video"),
            InlineKeyboardButton("🖼️ Thumbnail image", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("⚡ Mula XML file badalavane", callback_data=f"do_upd:{res_key}:files")
        )
    elif r_type == 'plp':
        markup.add(
            InlineKeyboardButton("🖼️ Thumbnail image", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("🔗 Drive link badalavane", callback_data=f"do_upd:{res_key}:download_link"),
            InlineKeyboardButton("📂 PLP file badalavane", callback_data=f"do_upd:{res_key}:files")
        )
    else:
        markup.add(
            InlineKeyboardButton("🖼️ Thumbnail image", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("📁 Font file badalavane", callback_data=f"do_upd:{res_key}:files")
        )

    markup.add(InlineKeyboardButton("🗑️ Resource delete madi", callback_data=f"do_del:{res_key}"))
    markup.add(InlineKeyboardButton("❌ Bandh madi", callback_data="close_edit"))

    details = (
        f"🎯 **Resource sikkide!**\n\n"
        f"📌 **Hesaru:** {item_data.get('name')}\n"
        f"📁 **Category:** {item_data.get('type', '').upper()}\n"
        f"🪙 **Coin:** {item_data.get('coins')}\n\n"
        f"👇 **Neevu yavadannu update madalu icchisuteera?**"
    )
    bot.send_message(chat_id, details, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('do_upd:'))
def prompt_for_field(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return

    _, res_key, field = call.data.split(":")
    edit_sessions[call.from_user.id] = {'key': res_key, 'field': field, 'file_ids': []}

    bot.delete_message(call.message.chat.id, call.message.message_id)

    if field == "files":
        msg = bot.send_message(
            call.message.chat.id,
            "📂 **Hosa file(galu) kalsi:**\n\n"
            "Neevu ondu athava halavaru document file kalsabahudu. Ella file kalsi mugididdare kelagina **✅ Upload sampurna** button otti:",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, collect_edit_files)
        return

    prompts = {
        "name": "Hosa hesaru bareda kalsi:",
        "coins": "Hosa coin sankhye bareda kalsi (udaharanage: 15):",
        "image": "Hosa thumbnail image athava direct link (drive link) kalsi:",
        "video": "Hosa preview video file, youtube link athava direct link kalsi:",
        "download_link": "Hosa google drive athava bere yavude download link kalsi:"
    }

    msg = bot.send_message(
        call.message.chat.id,
        f"✍️ **{prompts.get(field, 'Hosa mana kalsi:')}**",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_updated_field)

def collect_edit_files(message):
    user_id = message.from_user.id
    if user_id not in edit_sessions:
        return

    if message.text and message.text.strip().lower() in ['/cancel', 'cancel', '❌ Cancel karun']:
        cancel_process(message)
        return

    if message.text and message.text.strip() in ['/done', 'done', '✅ Upload sampurna']:
        session = edit_sessions.pop(user_id, None)
        if not session or not session.get('file_ids'):
            bot.reply_to(message, "⚠️ Neevu yavude file upload madilla! Cancel madalagide.", reply_markup=get_admin_dashboard_keyboard())
            return

        res_key = session['key']
        file_list = session['file_ids']

        try:
            patch_data = {
                "file_ids": file_list,
                "file_id": file_list[0],
                "download_link": None
            }
            requests.patch(f"{FIREBASE_BASE}/resources/{res_key}.json", json=patch_data)
            bot.reply_to(
                message,
                f"🎉 **Successagi file update agide!**\n\nMot file: **{len(file_list)}ti** save madalagide.",
                parse_mode="Markdown",
                reply_markup=get_admin_dashboard_keyboard()
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Database dosha: {e}", reply_markup=get_admin_dashboard_keyboard())
        return

    if message.document:
        edit_sessions[user_id]['file_ids'].append(message.document.file_id)
        count = len(edit_sessions[user_id]['file_ids'])
        bot.reply_to(
            message,
            f"📥 File ({count}) sweekarisalagide!\n\nInnu file-galu iddare kalsi, athava mugididdare kelagina **✅ Upload sampurna** button otti."
        )
        bot.register_next_step_handler(message, collect_edit_files)
    else:
        bot.reply_to(message, "⚠️ Dayavittu file-annu document roopadalli kalsi athava mugididdare kelagina **✅ Upload sampurna** button otti:")
        bot.register_next_step_handler(message, collect_edit_files)

def save_updated_field(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    user_id = message.from_user.id
    if user_id not in edit_sessions:
        return

    session = edit_sessions[user_id]
    res_key = session['key']
    field = session['field']
    new_val = None

    if field == "coins":
        try:
            new_val = int(message.text.strip())
        except (ValueError, AttributeError):
            bot.reply_to(message, "⚠️ Coin sankhye roopadalli irabekku. Matte bareda kalsi:")
            bot.register_next_step_handler(message, save_updated_field)
            return

    elif field == "name":
        if not message.text:
            bot.reply_to(message, "⚠️ Text roopadalli hesaru kalsi:")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.text.strip()

    elif field == "image":
        if message.photo:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            new_val = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        elif message.text and message.text.strip().startswith("http"):
            new_val = message.text.strip()
        else:
            bot.reply_to(message, "⚠️ Dayavittu photo athava sariya ada direct link (https://...) kalsi:")
            bot.register_next_step_handler(message, save_updated_field)
            return

    elif field == "video":
        if message.video:
            vid_id = message.video.file_id
            file_info = bot.get_file(vid_id)
            new_val = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        elif message.text and message.text.strip().startswith("http"):
            new_val = message.text.strip()
        else:
            bot.reply_to(message, "⚠️ Dayavittu video file, youtube link athava sariya ada direct link (https://...) kalsi:")
            bot.register_next_step_handler(message, save_updated_field)
            return

    elif field == "download_link":
        if not message.text or not message.text.strip().startswith("http"):
            bot.reply_to(message, "⚠️ Sariya ada link kalsi (udaharanage: https://...):")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.text.strip()

    if new_val is not None:
        try:
            patch_data = {field: new_val}
            if field == "download_link":
                patch_data["file_ids"] = None
                patch_data["file_id"] = None

            requests.patch(f"{FIREBASE_BASE}/resources/{res_key}.json", json=patch_data)
            del edit_sessions[user_id]
            bot.reply_to(
                message,
                f"🎉 **Successagi update agide!**\n\nFile-ina **{field}** successagi badalavane madalagide.",
                parse_mode="Markdown",
                reply_markup=get_admin_dashboard_keyboard()
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Database dosha: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('do_del:'))
def delete_item(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    res_key = call.data.split(":")[1]
    try:
        requests.delete(f"{FIREBASE_BASE}/resources/{res_key}.json")
        bot.answer_callback_query(call.id, "Resource-annu kaledu hakalagide!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Dosha: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "close_edit")
def close_edit_box(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

def start_add_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'file_ids': []}

    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP project", callback_data="addcat:plp"),
        InlineKeyboardButton("🔤 Font file", callback_data="addcat:font"),
        InlineKeyboardButton("⚡ XML file", callback_data="addcat:xml")
    )
    bot.send_message(message.chat.id, "📦 **Yava category-ina resource jukta madalu icchisuteera?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addcat:'))
def handle_add_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    admin_temp_data[call.from_user.id] = {'type': cat, 'file_ids': []}
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(call.message.chat.id, f"✅ Category: *{cat.upper()}*\n\nIga resource-ina hesaru bareda kalsi:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 Ee resource unlock madalu user-ige eshtu coin bekagutte? (udaharanage: 15):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    try:
        admin_temp_data[message.from_user.id]['coins'] = int(message.text.strip())
        cat = admin_temp_data[message.from_user.id]['type']

        if cat == 'xml':
            bot.reply_to(message, "🎬 **XML preview video kalsi (Video file athava youtube/direct link kodi):**")
            bot.register_next_step_handler(message, get_xml_video)
        else:
            bot.reply_to(message, "🖼️ **Thumbnail image kalsi (athava drive-ina direct link kodi):**")
            bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "Coin sankhye roopadalli kodi (udaharanage: 15). Matte bareda kalsi:")
        bot.register_next_step_handler(message, get_coins)

def get_image(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    if message.photo:
        photo_file_id = message.photo[-1].file_id
        admin_temp_data[message.from_user.id]['image_file_id'] = photo_file_id
        file_info = bot.get_file(photo_file_id)
        admin_temp_data[message.from_user.id]['image'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    elif message.text and message.text.strip().startswith("http"):
        admin_temp_data[message.from_user.id]['image'] = message.text.strip()
    else:
        bot.reply_to(message, "⚠️ Dayavittu photo athava sariya ada direct link (https://...) kalsi:")
        bot.register_next_step_handler(message, get_image)
        return

    cat = admin_temp_data[message.from_user.id]['type']
    if cat == 'plp':
        bot.reply_to(
            message,
            "📂 **PLP file athava link kalsi:**\n\n"
            "• **Chikk file iddare:** 1 athava halavaru file kalsi mattu ella kalsi mugididdare kelagina **✅ Upload sampurna** button otti.\n"
            "• **Dodda file iddare:** Direct download link kalsi.",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(
            message,
            "📁 Mula **font file kalsi:**\n\n(1 athava halavaru font kalsabahudu. Ella file kalsi mugididdare kelagina **✅ Upload sampurna** button otti)",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)

def get_xml_video(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return

    if message.video:
        vid_id = message.video.file_id
        admin_temp_data[message.from_user.id]['video_file_id'] = vid_id
        file_info = bot.get_file(vid_id)
        admin_temp_data[message.from_user.id]['video'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    elif message.text and message.text.strip().startswith("http"):
        admin_temp_data[message.from_user.id]['video'] = message.text.strip()
    else:
        bot.reply_to(message, "⚠️ Dayavittu video file, youtube link athava sariya ada direct link (https://...) kalsi:")
        bot.register_next_step_handler(message, get_xml_video)
        return

    bot.reply_to(
        message,
        "📁 Preview video jukta vagide!\n\nIga **XML file(galu) kalsi** mattu ella kalsi mugididdare kelagina **✅ Upload sampurna** button otti:",
        reply_markup=get_file_collection_keyboard(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, get_batch_files_or_link)

def get_batch_files_or_link(message):
    user_id = message.from_user.id
    if user_id not in admin_temp_data:
        return

    if message.text and message.text.strip().lower() in ['/cancel', 'cancel', '❌ Cancel karun']:
        cancel_process(message)
        return

    if message.text and message.text.strip().startswith("http"):
        admin_temp_data[user_id]['download_link'] = message.text.strip()
        admin_temp_data[user_id]['file_ids'] = []
        save_resource_to_firebase(message)
        return

    if message.text and message.text.strip() in ['/done', 'done', '✅ Upload sampurna']:
        if not admin_temp_data[user_id].get('file_ids'):
            bot.reply_to(message, "⚠️ Neevu innu yavude file kalsilla! Munde file upload madi:")
            bot.register_next_step_handler(message, get_batch_files_or_link)
            return
        save_resource_to_firebase(message)
        return

    if message.document:
        admin_temp_data[user_id]['file_ids'].append(message.document.file_id)
        count = len(admin_temp_data[user_id]['file_ids'])
        bot.reply_to(
            message,
            f"📥 File ({count}) sweekarisalagide!\n\nInnu file iddare kalsi, athava mugididdare kelagina **✅ Upload sampurna** button otti."
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(message, "⚠️ Dayavittu document file kalsi, link kalsi athava mugididdare kelagina **✅ Upload sampurna** button otti:")
        bot.register_next_step_handler(message, get_batch_files_or_link)

def save_resource_to_firebase(message):
    user_id = message.from_user.id
    if user_id not in admin_temp_data:
        return

    resource = admin_temp_data.pop(user_id, None)
    if not resource:
        return

    if resource.get('file_ids'):
        resource['file_id'] = resource['file_ids'][0]

    res = requests.post(f"{FIREBASE_BASE}/resources.json", json=resource)

    if res.status_code == 200:
        res_key = res.json().get("name")
        total_files = len(resource.get('file_ids', []))
        file_info_msg = f"📦 Mot file: {total_files}ti" if total_files > 0 else "🔗 Link jukta vagide"

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Houdu, channel-alli post madi", callback_data=f"ch_post:yes:{res_key}"),
            InlineKeyboardButton("❌ Illa, agatyavilla", callback_data=f"ch_post:no:{res_key}")
        )

        bot.reply_to(
            message,
            f"🎉 **Resource successagi mini app-ige jukta vagide!**\n\n"
            f"📌 Hesaru: {resource['name']}\n"
            f"📁 Category: {resource['type'].upper()}\n"
            f"🪙 Bele: {resource['coins']} coin\n"
            f"{file_info_msg}\n\n"
            f"📢 **Neevu ee resource-annu telegram channel-alli post madalu icchisuteera?**",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.reply_to(message, "❌ Firebase-alli mahiti sanrakshane madalu agilla.", reply_markup=get_admin_dashboard_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('ch_post:'))
def handle_channel_post_decision(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return

    parts = call.data.split(":")
    decision = parts[1]
    res_key = parts[2]

    bot.delete_message(call.message.chat.id, call.message.message_id)

    if decision == "no":
        bot.send_message(
            call.message.chat.id,
            "✅ Resource-annu keval mini app-alli save madalagide (Channel-alli yavude post madalagilla).",
            reply_markup=get_admin_dashboard_keyboard()
        )
        return

    try:
        item_res = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json")
        resource = item_res.json()

        if resource:
            res_type_upper = resource['type'].upper()
            channel_caption = (
                f"🔥 *Hosa premium {res_type_upper} jukta vagide!*\n\n"
                f"📌 *Hesaru:* {resource['name']}\n"
                f"📁 *Category:* {res_type_upper}\n"
                f"🪙 *Bele:* {resource['coins']} coin\n\n"
                f"🚀 Free-yagi sangraha madalu kelagina button otti bot-ige pravesha madi:"
            )

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 Download madi", url=f"https://t.me/{BOT_USERNAME}?start=ref_{ADMIN_ID}"))

            if resource.get('video_file_id'):
                bot.send_video(CHANNEL_ID, resource['video_file_id'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            elif resource.get('image_file_id'):
                bot.send_photo(CHANNEL_ID, resource['image_file_id'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            elif resource.get('video'):
                bot.send_video(CHANNEL_ID, resource['video'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            elif resource.get('image'):
                bot.send_photo(CHANNEL_ID, resource['image'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(CHANNEL_ID, channel_caption, parse_mode="Markdown", reply_markup=markup)

            bot.send_message(
                call.message.chat.id,
                "🎉 **Successagi telegram channel-alli post madalagide!**",
                reply_markup=get_admin_dashboard_keyboard()
            )
        else:
            bot.send_message(call.message.chat.id, "❌ Resource data sikkilla.", reply_markup=get_admin_dashboard_keyboard())
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Channel-alli post madalu samasye agide: {e}", reply_markup=get_admin_dashboard_keyboard())

def start_ad_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📢 Advertisement shirshike athava text bareda kalsi:\n(Cancel madalu '❌ Cancel karun' odi)", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    admin_temp_data[message.from_user.id]['text'] = message.text.strip()
    bot.reply_to(message, "🔗 Advertisement click link kalsi (udaharanage: https://...):")
    bot.register_next_step_handler(message, get_ad_link)

def get_ad_link(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ Cancel karun"):
        cancel_process(message)
        return
    link = message.text.strip()
    ad_data = {
        "text": admin_temp_data[message.from_user.id]['text'],
        "link": link
    }
    requests.put(f"{FIREBASE_BASE}/active_ad.json", json=ad_data)
    bot.reply_to(message, "✅ Advertisement successagi mini app-alli set agide!", reply_markup=get_admin_dashboard_keyboard())

@bot.message_handler(func=lambda message: message.reply_to_message is not None and int(message.from_user.id) == int(ADMIN_ID))
def reply_to_user_from_admin(message):
    try:
        reply_header = message.reply_to_message.text or message.reply_to_message.caption
        if reply_header and "User ID:" in reply_header:
            target_id = int(reply_header.split("User ID:")[1].split()[0])
            bot.send_message(target_id, f"💬 *Support team reply:*\n\n{message.text}", parse_mode="Markdown")
            bot.reply_to(message, "✅ User-ina hatra uttara talupide!")
    except Exception as e:
        bot.reply_to(message, f"❌ Uttara kalsalu agilla: {e}")

@bot.message_handler(func=lambda message: message.chat.type == 'private' and int(message.from_user.id) != int(ADMIN_ID) and not (message.text and message.text.startswith('/')))
def forward_user_message_to_admin(message):
    if is_user_banned(message.from_user.id):
        return
    print(message)
    user_info = f"👤 *Message preraka:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *Text:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ Nimma message support team-ige talupide.")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    # NOTE: single-threaded, single-process Flask dev server.
    # Do NOT put this app behind gunicorn with more than 1 worker,
    # and do NOT run more than one Render instance/replica of this
    # service — multiple live processes hitting the same bot token
    # is the #1 real-world cause of "Conflict: terminated by other
    # getUpdates request", even in webhook mode, because Telegram
    # will also reject overlapping setWebhook/getUpdates calls from
    # more than one process using the same token at the same time.
    app.run(host='0.0.0.0', port=port, threaded=True)

def setup_webhook():
    """
    Cleanly tear down any previous webhook/polling state, then set the
    webhook for this instance. Retries a few times because right after
    a Render redeploy the old instance may still briefly hold the
    connection to Telegram's servers.
    """
    if not RENDER_EXTERNAL_URL:
        print("RENDER_EXTERNAL_URL not found. Webhook not set.")
        return

    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"

    for attempt in range(1, 6):
        try:
            # drop_pending_updates=True clears any backlog left over
            # from a previous polling/webhook session, which is what
            # actually triggers the "Conflict" error on the next call.
            bot.remove_webhook(drop_pending_updates=True)
            time.sleep(2)
            bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            print(f"Webhook set to: {webhook_url}")
            return
        except Exception as e:
            print(f"[Attempt {attempt}/5] Failed to set webhook: {e}")
            time.sleep(3)

    print("Could not set webhook after 5 attempts.")

if __name__ == "__main__":
    # No polling anywhere in this file — bot.polling() /
    # bot.infinity_polling() are intentionally never called.
    # Everything runs through the Flask webhook route above.
    setup_webhook()

    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    while True:
        time.sleep(10)
