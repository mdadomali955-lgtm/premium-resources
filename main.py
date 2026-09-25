import os
import requests
import telebot
import time
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from flask import Flask, jsonify
from threading import Thread

BOT_TOKEN = "8815920877:AAHlGCVVXjFPnQ1R__cLI8PSN8qA0YxKGN4"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}
broadcast_sessions = {}
ban_sessions = {}
promo_sessions = {}
user_inspect_sessions = {}

# --- UptimeRobot ও চ্যানেল ভেরিফিকেশন API সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!", 200

@app.route('/health')
def health():
    return "OK", 200

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

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.daemon = True
    t.start()

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
        InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL),
        InlineKeyboardButton("🔄 ভেরিফাই করুন", callback_data=f"check_sub:{target_arg}")
    )
    return markup

def get_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 প্রিমিয়াম রিসোর্স 💎", web_app=WebAppInfo(url=WEB_APP_URL)))
    return markup

def get_admin_dashboard_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("➕ নতুন রিসোর্স যুক্ত করুন"),
        KeyboardButton("✏️ রিসোর্স এডিট/আপডেট"),
        KeyboardButton("🪙 কয়েন আপডেট/ম্যানেজ"),
        KeyboardButton("📊 ডাউনলোড হিস্ট্রি দেখুন"),
        KeyboardButton("📢 ব্রডকাস্ট মেসেজ"),
        KeyboardButton("🚫 ইউজার ব্যান/আনব্যান"),
        KeyboardButton("🎁 প্রোমো কোড তৈরি"),
        KeyboardButton("🔍 ইউজার চেক"),
        KeyboardButton("📢 বিজ্ঞাপন সেট করুন"),
        KeyboardButton("❌ বাতিল করুন")
    )
    return markup

def get_file_collection_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("✅ আপলোড সম্পন্ন"),
        KeyboardButton("❌ বাতিল করুন")
    )
    return markup

# --- ক্যানসেল হ্যান্ডলার ---
def cancel_process(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    uid = message.from_user.id
    for s_dict in [admin_temp_data, edit_sessions, coin_sessions, broadcast_sessions, ban_sessions, promo_sessions, user_inspect_sessions]:
        if uid in s_dict:
            del s_dict[uid]
    
    if int(uid) == int(ADMIN_ID):
        bot.send_message(message.chat.id, "❌ চলমান প্রক্রিয়া বাতিল করা হয়েছে।", reply_markup=get_admin_dashboard_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())

# --- সরাসরি ক্যাটাগরি কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['add_xml', 'xml', 'add_plp', 'plp', 'add_font', 'font'])
def handle_direct_add_commands(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    
    cmd = message.text.split()[0].replace('/', '').lower()
    cat_type = 'xml' if 'xml' in cmd else ('plp' if 'plp' in cmd else 'font')
    
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'type': cat_type, 'file_ids': []}
    
    cat_title = "⚡ XML প্রজেক্ট" if cat_type == 'xml' else ("🎨 PLP প্রজেক্ট" if cat_type == 'plp' else "🔤 ফন্ট ফাইল")
    msg = bot.send_message(
        message.chat.id, 
        f"✅ কমান্ড গ্রহণ করা হয়েছে: *{cat_title}*\n\nএবার রিসোর্সের নাম লিখে পাঠান:\n(বাতিল করতে /cancel চাপুন)", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_name)

# --- ডাউনলোড হিস্ট্রি দেখার ফাংশন ---
@bot.message_handler(commands=['download_logs', 'logs'])
def show_download_logs_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    
    try:
        res = requests.get(f"{FIREBASE_BASE}/download_logs.json").json()
        if not res:
            bot.reply_to(message, "📂 এখনো কোনো ডাউনলোডের রেকর্ড জমা হয়নি।")
            return
        
        log_text = "📊 **শেষ ১০টি ডাউনলোড হিস্ট্রি:**\n\n"
        items = list(res.items())[-10:]
        for key, log in items:
            log_text += (
                f"👤 ইউজার: *{log.get('user_name', 'Unknown')}*\n"
                f"🆔 আইডি: `{log.get('user_id')}`\n"
                f"📦 ফাইল: {log.get('resource_name')}\n"
                f"⏰ সময়: {log.get('time')}\n"
                f"-----------------------------------\n"
            )
        bot.reply_to(message, log_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ লগ লোড করতে সমস্যা হয়েছে: {e}")

# --- ফিচার ১: ব্রডকাস্ট সিস্টেম ---
def start_broadcast_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(
        message, 
        "📢 **ব্রডকাস্ট মেসেজ প্যানেল**\n\nসব ইউজারের কাছে যে মেসেজ বা নোটিশ পাঠাতে চান তা লিখে পাঠান (টেক্সট, ছবি বা ভিডিও দিতে পারেন):",
        parse_mode="Markdown",
        reply_markup=get_admin_dashboard_keyboard()
    )
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return

    users_data = requests.get(f"{FIREBASE_BASE}/users.json").json()
    if not users_data:
        bot.reply_to(message, "⚠️ ডেটাবেজে কোনো ইউজার পাওয়া যায়নি!", reply_markup=get_admin_dashboard_keyboard())
        return

    sent_count = 0
    fail_count = 0
    
    wait_msg = bot.reply_to(message, "⏳ ব্রডকাস্ট মেসেজ পাঠানো হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")

    for uid in users_data.keys():
        try:
            if message.content_type == 'text':
                bot.send_message(uid, f"📢 **অফিসিয়াল নোটিশ:**\n\n{message.text}", parse_mode="Markdown")
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
        f"✅ **ব্রডকাস্ট সম্পন্ন হয়েছে!**\n\n"
        f"📤 সফলভাবে পাঠানো হয়েছে: *{sent_count}* জনের কাছে\n"
        f"⚠️ ফেইল হয়েছে: *{fail_count}* জনের কাছে",
        parse_mode="Markdown",
        reply_markup=get_admin_dashboard_keyboard()
    )

# --- ফিচার ২: ইউজার ব্যান/আনব্যান সিস্টেম ---
def start_ban_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 ইউজার ব্যান করুন", callback_data="ban_action:ban"),
        InlineKeyboardButton("✅ ইউজার আনব্যান করুন", callback_data="ban_action:unban")
    )
    bot.send_message(message.chat.id, "🚫 **ইউজার ম্যানেজমেন্ট প্যানেল**\n\nআপনি কী করতে চান?", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ban_action:'))
def handle_ban_action(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    action = call.data.split(":")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    ban_sessions[call.from_user.id] = {'action': action}
    
    txt = "🚫 যে ইউজারের আইডি ব্যান করতে চান তা লিখে পাঠান:" if action == "ban" else "✅ যে ইউজারের আইডি আনব্যান করতে চান তা লিখে পাঠান:"
    msg = bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_ban_unban_id)

def process_ban_unban_id(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
        bot.reply_to(message, f"🚫 ইউজার আইডি `{target_id}` সফলভাবে ব্যান করা হয়েছে!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    else:
        requests.delete(f"{FIREBASE_BASE}/banned_users/{target_id}.json")
        bot.reply_to(message, f"✅ ইউজার আইডি `{target_id}` আনব্যান করা হয়েছে!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())

# --- ফিচার ৩: প্রোমো কোড / রিডিম কোড সিস্টেম ---
def start_promo_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(message, "🎁 নতুন প্রোমো কোডের নাম লিখুন (যেমন: `FREECOIN50`):", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(msg, get_promo_code_name)

def get_promo_code_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    code = message.text.strip().upper()
    promo_sessions[message.from_user.id] = {'code': code}
    msg = bot.reply_to(message, f"🪙 কোড: *{code}*\n\nএই কোড ব্যবহার করলে ইউজার কত কয়েন পাবে তার পরিমাণ সংখ্যায় লিখুন (যেমন: 100):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_promo_code_amount)

def get_promo_code_amount(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
            f"🎉 **প্রোমো কোড সফলভাবে তৈরি হয়েছে!**\n\n"
            f"🎁 কোড: `{code}`\n"
            f"🪙 কয়েন মূল্য: *{coins}*\n\n"
            f"ইউজাররা `/redeem {code}` লিখে এটি ব্যবহার করতে পারবে।",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "⚠️ কয়েন সংখ্যায় দিতে হবে। আবার লিখুন:")
        bot.register_next_step_handler(message, get_promo_code_amount)

@bot.message_handler(commands=['redeem'])
def redeem_promo_code(message):
    args = message.text.split()
    uid = message.from_user.id
    if is_user_banned(uid):
        return
        
    if len(args) < 2:
        bot.reply_to(message, "⚠️ ব্যবহার: `/redeem [প্রোমো_কোড]`\nযেমন: `/redeem FREECOIN50`", parse_mode="Markdown")
        return
        
    code = args[1].strip().upper()
    try:
        p_data = requests.get(f"{FIREBASE_BASE}/promo_codes/{code}.json").json()
        if not p_data:
            bot.reply_to(message, "❌ ভুল বা মেয়াদোত্তীর্ণ প্রোমো কোড!")
            return
            
        used_by = p_data.get('used_by') or {}
        if str(uid) in used_by:
            bot.reply_to(message, "⚠️ আপনি ইতিমধ্যে এই প্রোমো কোড ব্যবহার করেছেন!")
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
            f"🎉 অভিনন্দন! প্রোমো কোড সফলভাবে রিডিম হয়েছে।\n"
            f"আপনার অ্যাকাউন্টে যুক্ত হয়েছে *{coins_to_add}* কয়েন!\n"
            f"বর্তমান ব্যালেন্স: *{new_coins} 🪙*",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি হয়েছে: {e}")

# --- ফিচার ৫: ইউজার প্রোফাইল ইন্সপেক্টর ---
def start_user_inspect_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.reply_to(message, "🔍 যে ইউজারের তথ্য দেখতে চান তার **Telegram User ID** লিখে পাঠান:", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(msg, process_user_inspection)

def process_user_inspection(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
        
    target_id = message.text.strip()
    try:
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json()
        if not u_data:
            bot.reply_to(message, f"❌ আইডি `{target_id}` ডেটাবেজে পাওয়া যায়নি!", parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
            return
            
        banned = is_user_banned(target_id)
        status_text = "🚫 ব্যান করা" if banned else "✅ সচল (Active)"
        
        info = (
            f"👤 **ইউজার প্রোফাইল তথ্য**\n\n"
            f"📌 নাম: {u_data.get('name', 'Unknown')}\n"
            f"🔗 ইউজারনেম: @{u_data.get('username', 'None')}\n"
            f"🆔 আইডি: `{target_id}`\n"
            f"🪙 বর্তমান কয়েন: {u_data.get('coins', 0)}\n"
            f"👥 মোট রেফার: {u_data.get('refers', 0)}\n"
            f"⚙️ স্ট্যাটাস: {status_text}"
        )
        bot.reply_to(message, info, parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ তথ্য লোড করতে সমস্যা হয়েছে: {e}", reply_markup=get_admin_dashboard_keyboard())

# --- কয়েন ম্যানেজমেন্ট ফ্লো ---
def start_coin_management_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👑 আমার নিজের কয়েন সেট করুন", callback_data="coin_act:self"),
        InlineKeyboardButton("👤 অন্য ইউজারকে কয়েন দিন/কমান", callback_data="coin_act:other")
    )
    bot.send_message(
        message.chat.id,
        "🪙 **কয়েন ম্যানেজমেন্ট প্যানেল**\n\nআপনি নিজের কয়েন আপডেট করতে চান নাকি কোনো ইউজারকে কয়েন দিতে চান?",
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
            "👑 **আপনার অ্যাকাউন্টে কত কয়েন সেট করতে চান?**\n(যেমন: `2000` লিখে পাঠান বা '❌ বাতিল করুন' চাপুন)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_self_coins)
    else:
        msg = bot.send_message(
            call.message.chat.id,
            "👤 **যে ইউজারকে কয়েন দিতে চান তার Telegram User ID লিখে পাঠান:**\n(বাতিল করতে '❌ বাতিল করুন' চাপুন)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_user_id_for_coins)

def process_self_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    try:
        amount = int(message.text.strip())
        requests.patch(f"{FIREBASE_BASE}/users/{ADMIN_ID}.json", json={"coins": amount})
        bot.reply_to(
            message,
            f"🎉 আপনার অ্যাকাউন্টে সফলভাবে *{amount} 🪙* কয়েন সেট করা হয়েছে!",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "⚠️ কয়েনের পরিমাণ সংখ্যায় দিন। আবার লিখুন:")
        bot.register_next_step_handler(message, process_self_coins)

def process_user_id_for_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    
    target_id = message.text.strip()
    u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json()
    if not u_data:
        bot.reply_to(message, f"❌ আইডি `{target_id}` ডেটাবেজে খুঁজে পাওয়া যায়নি! সঠিক আইডি দিন:")
        bot.register_next_step_handler(message, process_user_id_for_coins)
        return

    coin_sessions[message.from_user.id] = {'target_id': target_id, 'user_name': u_data.get('name', 'User')}
    msg = bot.reply_to(
        message, 
        f"✅ ইউজার পাওয়া গেছে: *{u_data.get('name', 'User')}* (বর্তমান কয়েন: {u_data.get('coins', 0)})\n\n"
        f"🪙 **কত কয়েন যোগ বা বিয়োগ করতে চান?** (যেমন: যোগ করতে `500` বা কমাতে `-200`):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_apply_coins)

def process_apply_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
            f"🎉 **সফলভাবে সম্পন্ন হয়েছে!**\n\n"
            f"👤 ইউজার: {u_data.get('name', 'User')}\n"
            f"🆔 আইডি: `{target_id}`\n"
            f"🪙 পূর্বের কয়েন: {current_c}\n"
            f"✨ বর্তমান কয়েন: *{updated_c}*",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
        
        try:
            bot.send_message(
                target_id, 
                f"🎁 **অ্যাডমিন থেকে কয়েন আপডেট!**\n\nআপনার অ্যাকাউন্টে *{amount}* কয়েন যোগ করা হয়েছে।\nবর্তমান ব্যালেন্স: *{updated_c} 🪙*",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    except ValueError:
        bot.reply_to(message, "⚠️ কয়েন সংখ্যায় দিন (যেমন: 500)। আবার লিখুন:")
        bot.register_next_step_handler(message, process_apply_coins)

# সরাসরি কমান্ড সাপোর্ট
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
            bot.reply_to(message, "⚠️ কয়েনের পরিমাণ সংখ্যায় দিন। যেমন: `/mycoins 2500`", parse_mode="Markdown")
            return

    try:
        requests.patch(f"{FIREBASE_BASE}/users/{ADMIN_ID}.json", json={"coins": amount})
        bot.reply_to(message, f"🎉 আপনার অ্যাকাউন্টে সফলভাবে *{amount} 🪙* কয়েন সেট করা হয়েছে!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ ডেটাবেজ এরর: {e}")

@bot.message_handler(commands=['givecoins'])
def give_user_coins_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ ব্যবহার: `/givecoins [User_ID] [Coins]`\nযেমন: `/givecoins 7481264433 500`", parse_mode="Markdown")
        return

    target_uid = args[1].strip()
    try:
        coins_to_add = int(args[2].strip())
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_uid}.json").json()
        if not u_data:
            bot.reply_to(message, f"❌ আইডি `{target_uid}` খুঁজে পাওয়া যায়নি!")
            return

        current_c = u_data.get('coins', 0)
        updated_c = max(0, current_c + coins_to_add)
        requests.patch(f"{FIREBASE_BASE}/users/{target_uid}.json", json={"coins": updated_c})
        bot.reply_to(message, f"✅ সফল! বর্তমান কয়েন: *{updated_c}*", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠️ কয়েন সংখ্যায় দিন।")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

# --- ফোর্স সাবস্ক্রিপশন ভেরিফিকেশন বাটন হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('check_sub:'))
def handle_verify_subscription(call):
    user_id = call.from_user.id
    target_arg = call.data.split("check_sub:")[1]

    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ আপনি এই বট থেকে ব্যান হয়েছেন!", show_alert=True)
        return

    if is_user_member(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=False)
        
        if target_arg.startswith("get_"):
            process_resource_delivery(call.message.chat.id, target_arg, call.from_user)
        else:
            bot.send_message(
                call.message.chat.id,
                f"👋 স্বাগতম {call.from_user.first_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে আপনাকে স্বাগতম। নিচের বাটনে চাপ দিয়ে অ্যাপ ওপেন করুন:",
                reply_markup=get_main_keyboard()
            )
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনও চ্যানেলে জয়েন করেননি! আগে জয়েন করুন।", show_alert=True)

# মূল ফাইল ডেলিভারি ফাংশন ও ট্র্যাকিং লগ সেভ
def process_resource_delivery(chat_id, arg_text, user_obj=None):
    file_key = arg_text.replace("get_", "").split("_from_")[0]
    bot.send_message(chat_id, "⏳ আপনার ফাইল প্রস্তুত করা হচ্ছে...")
    try:
        res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
        item = res.json()
        if item:
            res_name = item.get('name', 'রিসোর্স')
            res_type = item.get("type", "plp").upper()
            
            if user_obj:
                try:
                    log_data = {
                        "user_id": user_obj.id,
                        "user_name": user_obj.first_name,
                        "resource_name": res_name,
                        "category": res_type,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    requests.post(f"{FIREBASE_BASE}/download_logs.json", json=log_data)
                except Exception:
                    pass

            if item.get("download_link"):
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড করুন", url=item["download_link"]))
                markup.add(InlineKeyboardButton("🚀 পুনরায় অ্যাপ খুলুন", web_app=WebAppInfo(url=WEB_APP_URL)))
                bot.send_message(
                    chat_id,
                    f"🎁 আপনার রিসোর্স: *{res_name}*\n"
                    f"📁 ক্যাটাগরি: *{res_type}*\n"
                    f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                    "🔗 নিচের বাটনে চাপ দিয়ে ফাইলটি সংগ্রহ করুন:",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return

            file_ids = item.get("file_ids") or ([] if not item.get("file_id") else [item.get("file_id")])
            if file_ids:
                total_f = len(file_ids)
                for idx, fid in enumerate(file_ids, 1):
                    cap = (
                        f"🎁 ফাইল ({idx}/{total_f}): *{res_name}*\n"
                        f"📁 ক্যাটাগরি: *{res_type}*\n\n"
                        "📂 সেভ করতে ফাইলে ট্যাপ করুন ও ডাউনলোড শেষে ৩-ডট (⋮) চেপে **'Save to Downloads'** করুন."
                    )
                    bot.send_document(chat_id, fid, caption=cap, parse_mode="Markdown")
                    time.sleep(0.3)
                bot.send_message(chat_id, "✅ আপনার সমস্ত ফাইল সফলভাবে ইনবক্সে ডেলিভার করা হয়েছে!", reply_markup=get_main_keyboard())
                return
        else:
            bot.send_message(chat_id, "❌ ফাইলটি ডাটাবেজে খুঁজে পাওয়া যায়নি।", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ রিসোর্স ডেলিভারিতে সমস্যা দেখা দিয়েছে: {e}", reply_markup=get_main_keyboard())

# --- স্টার্ট ও ডেলিভারি হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "❌ দুঃখিত, আপনি এই বট থেকে ব্যান হয়েছেন!")
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
                    bot.send_message(referrer_id, "🎉 অভিনন্দন! নতুন মেম্বার আপনার রেফারে জয়েন করেছে। আপনি পেয়েছেন +50 🪙 কয়েন!")
            except Exception:
                pass

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👑 **স্বাগতম অ্যাডমিন প্যানেলে!**\n\n"
            "নিচের বাটন বা কমান্ড ব্যবহার করে যেকোনো কাজ পরিচালনা করতে পারেন:",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
        bot.send_message(message.chat.id, "মিনি অ্যাপে যেতে নিচের বাটনে চাপুন:", reply_markup=get_main_keyboard())
        return

    target_arg = args[1] if len(args) > 1 else ""
    if not is_user_member(user_id):
        bot.send_message(
            message.chat.id,
            f"👋 হ্যালো *{user_name}*!\n\n"
            "⚠️ **বট এবং মিনি অ্যাপটি ব্যবহার করতে হলে আমাদের অফিসিয়াল টেলিগ্রাম চ্যানেলে জয়েন থাকা বাধ্যতামূলক।**\n\n"
            "👉 নিচের বাটনে ক্লিক করে চ্যানেলে জয়েন করুন এবং এরপর **'🔄 ভেরিফাই করুন'** বাটনে চাপ দিন:",
            parse_mode="Markdown",
            reply_markup=get_force_sub_keyboard(target_arg)
        )
        return

    bot.send_message(
        message.chat.id,
        f"👋 হ্যালো {user_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে আপনাকে স্বাগতম। নিচের বাটনে চাপ দিয়ে অ্যাপ ওপেন করুন:",
        reply_markup=get_main_keyboard()
    )

# --- সেন্ট্রাল অ্যাডমিন টেক্সট কন্ট্রোলার ---
@bot.message_handler(func=lambda m: int(m.from_user.id) == int(ADMIN_ID) and m.text and not m.reply_to_message)
def handle_all_admin_text(message):
    text = message.text.strip().lower()

    if text in ['/cancel', 'cancel', 'বাতিল', '❌ বাতিল করুন']:
        cancel_process(message)
        return

    if text in ['/edit', 'edit', 'এডিট', '✏️ রিসোর্স এডিট/আপডেট', 'আপডেট']:
        start_edit_flow(message)
        return

    if text in ['/add', 'add', 'যোগ', '➕ নতুন রিসোর্স যুক্ত করুন']:
        start_add_flow(message)
        return

    if text in ['🪙 কয়েন আপডেট/ম্যানেজ', 'কয়েন', 'coins', '/coins']:
        start_coin_management_flow(message)
        return

    if text in ['📊 ডাউনলোড হিস্ট্রি দেখুন', 'logs', 'download_logs', '/logs']:
        show_download_logs_cmd(message)
        return

    if text in ['📢 ব্রডকাস্ট মেসেজ', 'broadcast', '/broadcast']:
        start_broadcast_flow(message)
        return

    if text in ['🚫 ইউজার ব্যান/আনব্যান', 'ban', '/ban']:
        start_ban_flow(message)
        return

    if text in ['🎁 প্রোমো কোড তৈরি', 'promo', '/promo']:
        start_promo_flow(message)
        return

    if text in ['🔍 ইউজার চেক', 'inspect', '/inspect']:
        start_user_inspect_flow(message)
        return

    if text in ['/setad', 'setad', 'বিজ্ঞাপন', '📢 বিজ্ঞাপন সেট করুন']:
        start_ad_flow(message)
        return

# --- এডিট ফ্লো ---
def start_edit_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    edit_sessions[message.from_user.id] = {}
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP", callback_data="edcat:plp"),
        InlineKeyboardButton("🔤 ফন্ট", callback_data="edcat:font"),
        InlineKeyboardButton("⚡ XML", callback_data="edcat:xml")
    )
    bot.send_message(message.chat.id, "🛠️ **কোন ক্যাটাগরির ফাইল আপডেট করতে চান?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edcat:'))
def handle_edit_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    edit_sessions[call.from_user.id] = {'type': cat}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    msg = bot.send_message(
        call.message.chat.id,
        f"✅ নির্বাচিত ক্যাটাগরি: *{cat.upper()}*\n\n"
        "এবার যে ফাইলটি আপডেট করতে চান সেটির **নাম বা নামের কিছু অংশ** লিখে পাঠান:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, find_resource_by_name)

def find_resource_by_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    
    search_name = (message.text or "").strip().lower()
    selected_type = edit_sessions.get(message.from_user.id, {}).get('type', 'plp')
    
    wait_msg = bot.reply_to(message, "🔍 ডাটাবেজে ফাইল খোঁজা হচ্ছে...")
    
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
                f"❌ *{selected_type.upper()}* ক্যাটাগরিতে '{message.text}' নামের ফাইল মেলেনি!\n\n"
                "সঠিক নাম লিখে আবার পাঠান (অথবা '❌ বাতিল করুন' চাপুন):",
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
            bot.send_message(message.chat.id, "🎯 একাধিক ফাইল মিলেছে। নির্দিষ্ট ফাইলটি বেছে নিন:", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('selres:'))
def select_from_matched(call):
    res_key = call.data.split(":")[1]
    res_data = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json").json()
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_edit_options(call.message.chat.id, res_key, res_data)

def show_edit_options(chat_id, res_key, item_data):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 নাম পরিবর্তন", callback_data=f"do_upd:{res_key}:name"),
        InlineKeyboardButton("🪙 কয়েন পরিবর্তন", callback_data=f"do_upd:{res_key}:coins")
    )

    r_type = item_data.get('type')
    if r_type == 'xml':
        markup.add(
            InlineKeyboardButton("🎬 প্রিভিউ ভিডিও পরিবর্তন", callback_data=f"do_upd:{res_key}:video"),
            InlineKeyboardButton("🖼️ থাম্বনেইল ছবি", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("⚡ মূল XML ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )
    elif r_type == 'plp':
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ছবি", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("🔗 ড্রাইভ লিংক পরিবর্তন", callback_data=f"do_upd:{res_key}:download_link"),
            InlineKeyboardButton("📂 PLP ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )
    else:
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ছবি", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("📁 ফন্ট ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )
        
    markup.add(InlineKeyboardButton("🗑️ রিসোর্সটি ডিলিট করুন", callback_data=f"do_del:{res_key}"))
    markup.add(InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close_edit"))

    details = (
        f"🎯 **রিসোর্স পাওয়া গেছে!**\n\n"
        f"📌 **নাম:** {item_data.get('name')}\n"
        f"📁 **ক্যাটাগরি:** {item_data.get('type', '').upper()}\n"
        f"🪙 **কয়েন:** {item_data.get('coins')}\n\n"
        f"👇 **আপনি কোনটি আপডেট করতে চান?**"
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
            "📂 **নতুন ফাইল(সমূহ) পাঠান:**\n\n"
            "আপনি এক বা একাধিক ডকুমেন্ট ফাইল পাঠাতে পারেন। সব ফাইল পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন:",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, collect_edit_files)
        return

    prompts = {
        "name": "নতুন নামটি লিখে পাঠান:",
        "coins": "নতুন কয়েন সংখ্যাটি লিখে পাঠান (যেমন: 15):",
        "image": "নতুন থাম্বনেইল ছবি অথবা ডাইরেক্ট লিংক (ড্রাইভ লিংক) পাঠান:",
        "video": "নতুন প্রিভিউ ভিডিও ফাইল, ইউটিউব লিংক অথবা ডাইরেক্ট লিংক পাঠান:",
        "download_link": "নতুন গুগল ড্রাইভ বা অন্য যেকোনো ডাউনলোড লিংক পাঠান:"
    }
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"✍️ **{prompts.get(field, 'নতুন মান পাঠান:')}**", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_updated_field)

def collect_edit_files(message):
    user_id = message.from_user.id
    if user_id not in edit_sessions:
        return
    
    if message.text and message.text.strip().lower() in ['/cancel', 'cancel', '❌ বাতিল করুন']:
        cancel_process(message)
        return

    if message.text and message.text.strip() in ['/done', 'done', '✅ আপলোড সম্পন্ন']:
        session = edit_sessions.pop(user_id, None)
        if not session or not session.get('file_ids'):
            bot.reply_to(message, "⚠️ আপনি কোনো ফাইল আপলোড করেননি! বাতিল করা হয়েছে।", reply_markup=get_admin_dashboard_keyboard())
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
                f"🎉 **সফলভাবে ফাইল আপডেট হয়েছে!**\n\nমোট ফাইল: **{len(file_list)}টি** সেভ করা হয়েছে।",
                parse_mode="Markdown",
                reply_markup=get_admin_dashboard_keyboard()
            )
        except Exception as e:
            bot.reply_to(message, f"❌ ডাটাবেজ ত্রুটি: {e}", reply_markup=get_admin_dashboard_keyboard())
        return

    if message.document:
        edit_sessions[user_id]['file_ids'].append(message.document.file_id)
        count = len(edit_sessions[user_id]['file_ids'])
        bot.reply_to(
            message,
            f"📥 ফাইল ({count}) গ্রহণ করা হয়েছে!\n\nআরও ফাইল থাকলে পাঠান, অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন."
        )
        bot.register_next_step_handler(message, collect_edit_files)
    else:
        bot.reply_to(message, "⚠️ দয়া করে ফাইলটি ডকুমেন্ট হিসেবে পাঠান অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন:")
        bot.register_next_step_handler(message, collect_edit_files)

def save_updated_field(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
            bot.reply_to(message, "⚠️ কয়েন সংখ্যায় হতে হবে। আবার লিখুন:")
            bot.register_next_step_handler(message, save_updated_field)
            return
            
    elif field == "name":
        if not message.text:
            bot.reply_to(message, "⚠️ টেক্সট হিসেবে নাম পাঠান:")
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
            bot.reply_to(message, "⚠️ দয়া করে সঠিক ছবি অথবা ডাইরেক্ট লিংক (https://...) পাঠান:")
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
            bot.reply_to(message, "⚠️ দয়া করে ভিডিও ফাইল, ইউটিউব লিংক অথবা ডাইরেক্ট লিংক পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return

    elif field == "download_link":
        if not message.text or not message.text.strip().startswith("http"):
            bot.reply_to(message, "⚠️ সঠিক লিংক পাঠান (যেমন: https://...):")
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
                f"🎉 **সফলভাবে আপডেট হয়েছে!**\n\nফাইলটির **{field}** সফলভাবে পরিবর্তন করা হয়েছে।", 
                parse_mode="Markdown", 
                reply_markup=get_admin_dashboard_keyboard()
            )
        except Exception as e:
            bot.reply_to(message, f"❌ ডাটাবেজ ত্রুটি: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('do_del:'))
def delete_item(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    res_key = call.data.split(":")[1]
    try:
        requests.delete(f"{FIREBASE_BASE}/resources/{res_key}.json")
        bot.answer_callback_query(call.id, "রিসোর্সটি মুছে ফেলা হয়েছে!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"ত্রুটি: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "close_edit")
def close_edit_box(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- রিসোর্স যুক্ত করার ফ্লো ---
def start_add_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'file_ids': []}
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP প্রজেক্ট", callback_data="addcat:plp"),
        InlineKeyboardButton("🔤 ফন্ট ফাইল", callback_data="addcat:font"),
        InlineKeyboardButton("⚡ XML ফাইল", callback_data="addcat:xml")
    )
    bot.send_message(message.chat.id, "📦 **কোন ক্যাটাগরির রিসোর্স যোগ করতে চান?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addcat:'))
def handle_add_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    admin_temp_data[call.from_user.id] = {'type': cat, 'file_ids': []}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    msg = bot.send_message(call.message.chat.id, f"✅ ক্যাটাগরি: *{cat.upper()}*\n\nএবার রিসোর্সের নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্স আনলক করতে ইউজারের কত কয়েন লাগবে? (যেমন: 15):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    try:
        admin_temp_data[message.from_user.id]['coins'] = int(message.text.strip())
        cat = admin_temp_data[message.from_user.id]['type']
        
        if cat == 'xml':
            bot.reply_to(message, "🎬 **XML প্রিভিউ ভিডিও পাঠান (ভিডিও ফাইল অথবা ইউটিউব/ডাইরেক্ট লিংক দিন):**")
            bot.register_next_step_handler(message, get_xml_video)
        else:
            bot.reply_to(message, "🖼️ **থাম্বনেইল ছবি পাঠান (অথবা ড্রাইভের ডাইরেক্ট লিংক দিন):**")
            bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েন সংখ্যায় দিন (যেমন: 15)। আবার লিখুন:")
        bot.register_next_step_handler(message, get_coins)

def get_image(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
        bot.reply_to(message, "⚠️ দয়া করে একটি ফটো অথবা সঠিক ডাইরেক্ট লিংক (https://...) পাঠান:")
        bot.register_next_step_handler(message, get_image)
        return
    
    cat = admin_temp_data[message.from_user.id]['type']
    if cat == 'plp':
        bot.reply_to(
            message, 
            "📂 **PLP ফাইল বা লিঙ্ক পাঠান:**\n\n"
            "• **ছোট ফাইল হলে:** ১টি বা একাধিক ফাইল পাঠান এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন。\n"
            "• **বড় ফাইল হলে:** সরাসরি ডাউনলোড লিঙ্ক পাঠিয়ে দিন।",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(
            message, 
            "📁 মূল **ফন্ট ফাইল পাঠান:**\n\n(১টি বা একাধিক ফন্ট পাঠাতে পারেন। সব ফাইল পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন)",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)

def get_xml_video(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
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
        bot.reply_to(message, "⚠️ দয়া করে ভিডিও ফাইল, ইউটিউব লিংক অথবা সঠিক ডাইরেক্ট লিংক (https://...) পাঠান:")
        bot.register_next_step_handler(message, get_xml_video)
        return
    
    bot.reply_to(
        message, 
        "📁 প্রিভিউ ভিডিও যুক্ত হয়েছে!\n\nএবার **XML ফাইল(সমূহ) পাঠান** এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন:",
        reply_markup=get_file_collection_keyboard(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, get_batch_files_or_link)

def get_batch_files_or_link(message):
    user_id = message.from_user.id
    if user_id not in admin_temp_data:
        return

    if message.text and message.text.strip().lower() in ['/cancel', 'cancel', '❌ বাতিল করুন']:
        cancel_process(message)
        return

    if message.text and message.text.strip().startswith("http"):
        admin_temp_data[user_id]['download_link'] = message.text.strip()
        admin_temp_data[user_id]['file_ids'] = []
        save_resource_to_firebase(message)
        return

    if message.text and message.text.strip() in ['/done', 'done', '✅ আপলোড সম্পন্ন']:
        if not admin_temp_data[user_id].get('file_ids'):
            bot.reply_to(message, "⚠️ আপনি এখনও কোনো ফাইল পাঠাননি! আগে ফাইল আপলোড করুন:")
            bot.register_next_step_handler(message, get_batch_files_or_link)
            return
        save_resource_to_firebase(message)
        return

    if message.document:
        admin_temp_data[user_id]['file_ids'].append(message.document.file_id)
        count = len(admin_temp_data[user_id]['file_ids'])
        bot.reply_to(
            message,
            f"📥 ফাইল ({count}) গ্রহণ করা হয়েছে!\n\nআরও ফাইল থাকলে পাঠাতে থাকুন, অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন।"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(message, "⚠️ দয়া করে ডকুমেন্ট ফাইল পাঠান, লিঙ্ক পাঠান অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন:")
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
        file_info_msg = f"📦 মোট ফাইল: {total_files}টি" if total_files > 0 else "🔗 লিঙ্ক সংযুক্ত"
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ হ্যাঁ, চ্যানেলে পোস্ট করুন", callback_data=f"ch_post:yes:{res_key}"),
            InlineKeyboardButton("❌ না, দরকার নেই", callback_data=f"ch_post:no:{res_key}")
        )
        
        bot.reply_to(
            message,
            f"🎉 **রিসোর্স সফলভাবে মিনি অ্যাপে যুক্ত হয়েছে!**\n\n"
            f"📌 নাম: {resource['name']}\n"
            f"📁 ক্যাটাগরি: {resource['type'].upper()}\n"
            f"🪙 মূল্য: {resource['coins']} কয়েন\n"
            f"{file_info_msg}\n\n"
            f"📢 **আপনি কি এই রিসোর্সটি টেলিগ্রাম চ্যানেলে পোস্ট করতে চান?**",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.reply_to(message, "❌ ফায়ারবেসে তথ্য সংরক্ষণ করা যায়নি।", reply_markup=get_admin_dashboard_keyboard())

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
            "✅ রিসোর্সটি শুধু মিনি অ্যাপে সেভ করা হয়েছে (চ্যানেলে কোনো পোস্ট করা হয়নি)।",
            reply_markup=get_admin_dashboard_keyboard()
        )
        return
    
    try:
        item_res = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json")
        resource = item_res.json()
        
        if resource:
            res_type_upper = resource['type'].upper()
            channel_caption = (
                f"🔥 *নতুন প্রিমিয়াম {res_type_upper} যুক্ত হয়েছে!*\n\n"
                f"📌 *নাম:* {resource['name']}\n"
                f"📁 *ক্যাটাগরি:* {res_type_upper}\n"
                f"🪙 *মূল্য:* {resource['coins']} কয়েন\n\n"
                f"🚀 ফ্রিতে সংগ্রহ করতে নিচের বাটনে চাপ দিয়ে বটে প্রবেশ করুন:"
            )
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 ডাউনলোড করুন", url=f"https://t.me/{BOT_USERNAME}?start=ref_{ADMIN_ID}"))
            
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
                "🎉 **সফলভাবে টেলিগ্রাম চ্যানেলে পোস্ট করা হয়েছে!**",
                reply_markup=get_admin_dashboard_keyboard()
            )
        else:
            bot.send_message(call.message.chat.id, "❌ রিসোর্স ডেটা পাওয়া যায়নি।", reply_markup=get_admin_dashboard_keyboard())
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ চ্যানেলে পোস্ট করতে সমস্যা হয়েছে: {e}", reply_markup=get_admin_dashboard_keyboard())

# --- বিজ্ঞাপন ফ্লো ---
def start_ad_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📢 বিজ্ঞাপনের শিরোনাম বা টেক্সট লিখে পাঠান:\n(বাতিল করতে '❌ বাতিল করুন' চাপুন)", reply_markup=get_admin_dashboard_keyboard())
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    admin_temp_data[message.from_user.id]['text'] = message.text.strip()
    bot.reply_to(message, "🔗 বিজ্ঞাপনের ক্লিক লিংকটি পাঠান (যেমন: https://...):")
    bot.register_next_step_handler(message, get_ad_link)

def get_ad_link(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    link = message.text.strip()
    ad_data = {
        "text": admin_temp_data[message.from_user.id]['text'],
        "link": link
    }
    requests.put(f"{FIREBASE_BASE}/active_ad.json", json=ad_data)
    bot.reply_to(message, "✅ বিজ্ঞাপন সফলভাবে মিনি অ্যাপে সেট হয়েছে!", reply_markup=get_admin_dashboard_keyboard())

# --- সাপোর্ট রিপ্লাই ---
@bot.message_handler(func=lambda message: message.reply_to_message is not None and int(message.from_user.id) == int(ADMIN_ID))
def reply_to_user_from_admin(message):
    try:
        reply_header = message.reply_to_message.text or message.reply_to_message.caption
        if reply_header and "User ID:" in reply_header:
            target_id = int(reply_header.split("User ID:")[1].split()[0])
            bot.send_message(target_id, f"💬 *সাপোর্ট টিম রিপ্লাই:*\n\n{message.text}", parse_mode="Markdown")
            bot.reply_to(message, "✅ ইউজারের কাছে উত্তর পৌঁছেছে!")
    except Exception as e:
        bot.reply_to(message, f"❌ উত্তর পাঠানো যায়নি: {e}")

# --- ইউজার মেসেজ ফরওয়ার্ড ---
@bot.message_handler(func=lambda message: message.chat.type == 'private' and int(message.from_user.id) != int(ADMIN_ID) and not (message.text and message.text.startswith('/')))
def forward_user_message_to_admin(message):
    if is_user_banned(message.from_user.id):
        return
    user_info = f"👤 *মেসেজ প্রেরক:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *টেক্সট:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ আপনার মেসেজটি সাপোর্ট টিমে পৌঁছেছে।")

if __name__ == "__main__":
    keep_alive()
    print("Premium Resource Delivery Bot is running with Web Server...")
    
    try:
        bot.remove_webhook()
    except Exception:
        pass

    bot.infinity_polling(
        skip_pending=True, 
        allowed_updates=['message', 'callback_query', 'my_chat_member', 'chat_member']
            )
