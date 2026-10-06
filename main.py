import os
import time
import io
import requests
import telebot
from PIL import Image
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from flask import Flask, request, jsonify

# --- Bot Configuration (Brand New Token) ---
BOT_TOKEN = "8815920877:AAHK0aaPhEUUINy74c7fMlOvm20_By3EzI8"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"
SUPPORT_URL = "https://t.me/PLPSTOREAI"

# Render External URL (Automatic)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://premium-resources-wprw.onrender.com")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}
broadcast_sessions = {}
ban_sessions = {}
promo_sessions = {}
user_inspect_sessions = {}
user_earn_sessions = {}

# --- Flask Server (Runs with python main.py) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly with Flask & Webhook via python main.py!", 200

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

# --- Auto Image Compression Function (200x200 HD) ---
def compress_image_data(image_input):
    try:
        if isinstance(image_input, str) and image_input.startswith("http"):
            response = requests.get(image_input, timeout=10)
            if response.status_code != 200:
                return image_input
            img_bytes = response.content
        elif isinstance(image_input, str) and image_input.startswith("data:image"):
            import base64
            header, encoded = image_input.split(",", 1)
            img_bytes = base64.b64decode(encoded)
        else:
            img_bytes = image_input

        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("RGB")
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        output.seek(0)
        
        import base64
        encoded_str = base64.b64encode(output.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded_str}"
    except Exception as e:
        print(f"Compression error: {e}")
        return image_input if isinstance(image_input, str) else "https://via.placeholder.com/150"

def get_force_sub_keyboard(target_arg=""):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL),
        InlineKeyboardButton("🔄 ভেরিফাই করুন", callback_data=f"check_sub:{target_arg}")
    )
    return markup

# --- Reply Keyboards (Bottom Permanent Keyboards) ---
def get_admin_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("➕ নতুন রিসোর্স যুক্ত করুন"),
        KeyboardButton("✏️ রিসোর্স এডিট/আপডেট"),
        KeyboardButton("🪙 কয়েন আপডেট/ম্যানেজ"),
        KeyboardButton("📊 ডাউনলোড হিস্ট্রি"),
        KeyboardButton("📢 ব্রডকাস্ট মেসেজ"),
        KeyboardButton("🚫 ইউজার ব্যান/আনব্যান"),
        KeyboardButton("🎁 প্রোমো কোড তৈরি"),
        KeyboardButton("🔍 ইউজার চেক"),
        KeyboardButton("❌ বাতিল করুন")
    )
    return markup

def get_user_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        KeyboardButton("🚀 প্রিমিয়াম রিসোর্স 💎"),
        KeyboardButton("📂 ফাইল দিয়ে কয়েন আয় করুন (Earn)"),
        KeyboardButton("📖 সহায়তা ও নির্দেশিকা (Help)")
    )
    return markup

# --- Help Guides Inline Menu ---
def get_help_inline_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📥 কিভাবে ফাইল ডাউনলোড করবেন?", callback_data="help_download"),
        InlineKeyboardButton("📖 ফন্ট ও পিএলপি ব্যবহারের গাইড", callback_data="help_usage"),
        InlineKeyboardButton("🪙 ফ্রি কয়েন পাওয়ার উপায়", callback_data="help_coins"),
        InlineKeyboardButton("💬 লাইভ সাপোর্ট ও হেল্পলাইন", url=SUPPORT_URL),
        InlineKeyboardButton("◀️ মূল মেনুতে ফিরুন", callback_data="help_back")
    )
    return markup

# --- Compress All Previous Images Command (/compress_all) ---
@bot.message_handler(commands=['compress_all'])
def compress_all_cmd(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return

    status_msg = bot.reply_to(message, "⏳ ডেটাবেজের আগের সব পুরোনো ইমেজ খুঁজে বের করে কম্প্রেস করা শুরু হচ্ছে...")

    try:
        res = requests.get(f"{FIREBASE_BASE}/resources.json").json() or {}
        count = 0
        for key, item in res.items():
            if "image" in item and item["image"]:
                old_img = item["image"]
                if not (old_img.startswith("data:image") and len(old_img) < 15000):
                    new_img = compress_image_data(old_img)
                    requests.put(f"{FIREBASE_BASE}/resources/{key}/image.json", json=new_img)
                    count += 1

        bot.edit_message_text(
            f"✅ **সফলভাবে সম্পন্ন হয়েছে!**\n\nডেটাবেজের আগের মোট ফাইলগুলোর বড় ইমেজ অটো কম্প্রেস হয়ে গেছে! 🚀",
            message.chat.id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ সমস্যা হয়েছে: {str(e)}", message.chat.id, status_msg.message_id)

# --- User Earn Coins Flow ---
def start_user_earn_flow(message):
    uid = message.from_user.id
    if is_user_banned(uid):
        bot.reply_to(message, "❌ আপনি ব্যান হয়েছেন!")
        return

    user_earn_sessions[uid] = {}
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP ফাইল", callback_data="earntype:plp"),
        InlineKeyboardButton("🔤 ফন্ট", callback_data="earntype:font"),
        InlineKeyboardButton("⚡ XML প্রজেক্ট", callback_data="earntype:xml")
    )
    bot.send_message(
        message.chat.id,
        "📂 **ফাইল দিয়ে কয়েন আয় প্যানেল**\n\nআপনি কোন ক্যাটাগরির ফাইল আপলোড করতে চান?",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('earntype:'))
def handle_earn_type(call):
    uid = call.from_user.id
    cat = call.data.split(":")[1]
    user_earn_sessions[uid] = {'type': cat, 'file_ids': []}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    msg = bot.send_message(call.message.chat.id, f"✅ ক্যাটাগরি: *{cat.upper()}*\n\nএখন এই ফাইলের একটি সুন্দর নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_user_earn_name)

def get_user_earn_name(message):
    if message.text and message.text.startswith('/'):
        return
    uid = message.from_user.id
    if uid not in user_earn_sessions:
        return
    user_earn_sessions[uid]['name'] = message.text.strip()
    msg = bot.reply_to(message, "🖼️ **থাম্বনেইল ইমেজ দিন (সরাসরি ছবি অথবা ফ্রি হোস্টিং ইমেজ লিংক পাঠান):**")
    bot.register_next_step_handler(msg, get_user_earn_image)

def get_user_earn_image(message):
    if message.text and message.text.startswith('/'):
        return
    uid = message.from_user.id
    if uid not in user_earn_sessions:
        return

    if message.photo:
        try:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            img_bytes = bot.download_file(file_info.file_path)
            user_earn_sessions[uid]['image'] = compress_image_data(img_bytes)
        except Exception as e:
            bot.reply_to(message, f"❌ ছবি প্রসেসে ত্রুটি: {e}")
            return
    elif message.text and message.text.strip().startswith("http"):
        user_earn_sessions[uid]['image'] = compress_image_data(message.text.strip())
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ছবি অথবা সঠিক সরাসরি লিংক পাঠান:")
        bot.register_next_step_handler(message, get_user_earn_image)
        return

    msg = bot.reply_to(
        message,
        "📂 **মূল ফাইল(গুলো) ডকুমেন্ট হিসেবে পাঠান:**\n\n(সব ফাইল পাঠানো শেষ হলে 'done' লিখে পাঠান)",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, collect_user_earn_files)

def collect_user_earn_files(message):
    uid = message.from_user.id
    if uid not in user_earn_sessions:
        return

    if message.text and message.text.strip().lower() in ['done', 'শেষ', 'ok']:
        session = user_earn_sessions.pop(uid, None)
        if not session or not session.get('file_ids'):
            bot.reply_to(message, "⚠️ আপনি কোনো ফাইল আপলোড করেননি!", reply_markup=get_user_reply_keyboard())
            return

        submit_to_admin_review(message, session, uid)
        return

    if message.document:
        user_earn_sessions[uid]['file_ids'].append(message.document.file_id)
        count = len(user_earn_sessions[uid]['file_ids'])
        bot.reply_to(message, f"📥 ফাইল ({count}) যুক্ত হয়েছে! আরও থাকলে পাঠান অথবা শেষ হলে 'done' লিখুন।")
        bot.register_next_step_handler(message, collect_user_earn_files)
    else:
        bot.reply_to(message, "⚠️ ডকুমেন্ট ফাইল পাঠান অথবা কাজ শেষ হলে 'done' লিখুন:")
        bot.register_next_step_handler(message, collect_user_earn_files)

def submit_to_admin_review(message, session, uid):
    try:
        user_obj = message.from_user
        session['user_id'] = uid
        session['user_name'] = user_obj.first_name
        session['username'] = user_obj.username or "None"
        session['status'] = "pending"

        res = requests.post(f"{FIREBASE_BASE}/pending_submissions.json", json=session)
        sub_key = res.json().get("name")

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ এপ্রুভ করুন (৫০ কয়েন দিন)", callback_data=f"rev_sub:approve:{sub_key}:{uid}"),
            InlineKeyboardButton("❌ রিজেক্ট করুন", callback_data=f"rev_sub:reject:{sub_key}:{uid}")
        )

        caption = (
            f"📥 **নতুন ফাইল সাবমিশন (রিসোর্স রিভিউ)**\n\n"
            f"👤 প্রেরক: {user_obj.first_name} (@{session['username']})\n"
            f"🆔 আইডি: `{uid}`\n"
            f"📌 নাম: {session['name']}\n"
            f"📁 ক্যাটাগরি: {session['type'].upper()}\n"
            f"📦 মোট ফাইল: {len(session['file_ids'])}টি"
        )

        if session.get('image'):
            bot.send_photo(ADMIN_ID, session['image'], caption=caption, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(ADMIN_ID, caption, parse_mode="Markdown", reply_markup=markup)

        bot.reply_to(
            message,
            "🎉 **আপনার ফাইল সফলভাবে অ্যাডমিনের কাছে রিভিউয়ের জন্য জমা হয়েছে!**\n\nঅ্যাডমিন এপ্রুভ করলেই আপনার অ্যাকাউন্টে কয়েন যোগ হবে।",
            reply_markup=get_user_reply_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ সমস্যা হয়েছে: {e}", reply_markup=get_user_reply_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('rev_sub:'))
def handle_admin_review_action(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return

    parts = call.data.split(":")
    action = parts[1]
    sub_key = parts[2]
    target_uid = int(parts[3])

    try:
        sub_data = requests.get(f"{FIREBASE_BASE}/pending_submissions/{sub_key}.json").json()
        if not sub_data:
            bot.answer_callback_query(call.id, "❌ সাবমিশন পাওয়া যায়নি!", show_alert=True)
            return

        if action == "reject":
            requests.delete(f"{FIREBASE_BASE}/pending_submissions/{sub_key}.json")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(target_uid, f"❌ দুঃখিত! আপনার সাবমিট করা ফাইল '{sub_data['name']}' রিজেক্ট করা হয়েছে।")
            bot.answer_callback_query(call.id, "রিজেক্ট করা হয়েছে।", show_alert=False)
            return

        reward_coins = 50
        resource_payload = {
            "name": sub_data['name'],
            "type": sub_data['type'],
            "coins": 15,
            "image": sub_data.get('image', ''),
            "file_ids": sub_data['file_ids'],
            "file_id": sub_data['file_ids'][0]
        }
        requests.post(f"{FIREBASE_BASE}/resources.json", json=resource_payload)

        u_res = requests.get(f"{FIREBASE_BASE}/users/{target_uid}.json").json() or {}
        current_c = u_res.get('coins', 0)
        new_c = current_c + reward_coins
        requests.patch(f"{FIREBASE_BASE}/users/{target_uid}.json", json={"coins": new_c})

        requests.delete(f"{FIREBASE_BASE}/pending_submissions/{sub_key}.json")

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(
            target_uid,
            f"🎉 **অভিনন্দন! আপনার ফাইল এপ্রুভ হয়েছে।**\n\n🎁 উপহার স্বরূপ আপনার অ্যাকাউন্টে যুক্ত হয়েছে: *{reward_coins} 🪙* কয়েন!\nবর্তমান ব্যালেন্স: *{new_c} 🪙*",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, f"সফল! ইউজারকে {reward_coins} কয়েন দেওয়া হয়েছে।", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"ত্রুটি: {e}", show_alert=True)

# --- User Help Guide Handlers ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def handle_user_help_guides(call):
    data = call.data
    
    if data == "help_download":
        text = "📥 **কিভাবে ফাইল ডাউনলোড করবেন?**\n\n1️⃣ প্রথমে আমাদের মিনি অ্যাপে প্রবেশ করুন।\n2️⃣ আপনার পছন্দের PLP, ফন্ট বা XML ফাইলটি বেছে নিন।\n3️⃣ 'ডাউনলোড' বাটনে চাপ দিন (প্রয়োজনীয় কয়েন কেটে নেওয়া হবে)।\n4️⃣ ৫ সেকেন্ডের মধ্যে ফাইলটি সরাসরি আপনার টেলিগ্রাম ইনবক্সে চলে আসবে!"
    elif data == "help_usage":
        text = "📖 **ফন্ট ও পিএলপি ব্যবহারের গাইড**\n\n🎨 **PLP ফাইল:** PixelLab অ্যাপ ওপেন করে .plp প্রজেক্ট ফাইলটি PixelLab/Presets ফোল্ডারে রেখে ওপেন করুন।\n🔤 **ফন্ট ফাইল:** ফন্টগুলো ডাউনলোড করে Internal Storage/Fonts ফোল্ডারে রাখুন অথবা PixelLab-এর ফন্ট ফোল্ডারে যুক্ত করে ব্যবহার করুন।"
    elif data == "help_coins":
        text = "🪙 **ফ্রি কয়েন পাওয়ার উপায়**\n\n1️⃣ **ফাইল আপলোড করে:** নিজে প্রিমিয়াম PLP বা ফন্ট আপলোড করে অ্যাডমিনের এপ্রুভালের মাধ্যমে প্রতি ফাইলে ৫০ কয়েন পর্যন্ত আর্ন করুন!\n2️⃣ **রেফার করে:** আপনার রেফার লিংক বন্ধুদের সাথে শেয়ার করে ফ্রি কয়েন সংগ্রহ করুন।"
    elif data == "help_back":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "👋 সহায়তা মেনু বন্ধ করা হয়েছে। নিচের বাটন থেকে যেকোনো অপশন বেছে নিন:", reply_markup=get_user_reply_keyboard())
        return
    else:
        return

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔙 গাইড মেনুতে ফিরুন", callback_data="help_menu_back"),
        InlineKeyboardButton("◀️ মূল মেনুতে ফিরুন", callback_data="help_back")
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "help_menu_back")
def handle_help_menu_back(call):
    text = "📖 **সহায়তা ও নির্দেশিকা সেন্টার**\n\nবটের যেকোনো বিষয় জানতে নিচের বাটনগুলোতে চাপ দিন:"
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=get_help_inline_keyboard())
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=get_help_inline_keyboard())

# --- Text Router for Reply Keyboard Buttons ---
@bot.message_handler(func=lambda message: True)
def handle_reply_keyboard_text(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if is_user_banned(uid):
        bot.send_message(message.chat.id, "❌ আপনি ব্যান হয়েছেন!")
        return

    # Cancel command handler
    if text == "❌ বাতিল করুন":
        bot.clear_step_handler_by_chat_id(message.chat.id)
        if uid == int(ADMIN_ID):
            bot.send_message(message.chat.id, "✅ অপারেশন বাতিল করা হয়েছে।", reply_markup=get_admin_reply_keyboard())
        else:
            bot.send_message(message.chat.id, "✅ অপারেশন বাতিল করা হয়েছে।", reply_markup=get_user_reply_keyboard())
        return

    # --- Admin Reply Buttons ---
    if uid == int(ADMIN_ID):
        if text == "➕ নতুন রিসোর্স যুক্ত করুন":
            start_add_flow(message)
            return
        elif text == "✏️ রিসোর্স এডিট/আপডেট":
            start_edit_flow(message)
            return
        elif text == "🪙 কয়েন আপডেট/ম্যানেজ":
            start_coin_management_flow(message)
            return
        elif text == "📊 ডাউনলোড হিস্ট্রি":
            show_download_logs_cmd(message)
            return
        elif text == "📢 ব্রডকাস্ট মেসেজ":
            start_broadcast_flow(message)
            return
        elif text == "🚫 ইউজার ব্যান/আনব্যান":
            start_ban_flow(message)
            return
        elif text == "🎁 প্রোমো কোড তৈরি":
            start_promo_flow(message)
            return
        elif text == "🔍 ইউজার চেক":
            start_user_inspect_flow(message)
            return

    # --- User Reply Buttons ---
    if text == "🚀 প্রিমিয়াম রিসোর্স 💎":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 মিনি অ্যাপ ওপেন করুন 💎", web_app=WebAppInfo(url=WEB_APP_URL)))
        bot.send_message(message.chat.id, "💎 প্রিমিয়াম রিসোর্স ব্রাউজ করতে নিচের বাটনে চাপ দিন:", reply_markup=markup)
        return
    elif text == "📂 ফাইল দিয়ে কয়েন আয় করুন (Earn)":
        start_user_earn_flow(message)
        return
    elif text == "📖 সহায়তা ও নির্দেশিকা (Help)":
        bot.send_message(
            message.chat.id,
            "📖 **সহায়তা ও নির্দেশিকা সেন্টার**\n\nবটের যেকোনো বিষয় জানতে নিচের বাটনগুলোতে চাপ দিন:",
            parse_mode="Markdown",
            reply_markup=get_help_inline_keyboard()
        )
        return

# --- Admin Flow Functions ---
def start_add_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'file_ids': []}
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP প্রজেক্ট", callback_data="addcat:plp"),
        InlineKeyboardButton("🔤 ফন্ট ফাইল", callback_data="addcat:font"),
        InlineKeyboardButton("⚡ XML ফাইল", callback_data="addcat:xml")
    )
    bot.send_message(message.chat.id, "📦 **কোন ক্যাটাগরির রিসোর্স যুক্ত করতে চান?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addcat:'))
def handle_add_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    admin_temp_data[call.from_user.id] = {'type': cat, 'file_ids': []}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    msg = bot.send_message(call.message.chat.id, f"✅ ক্যাটাগরি: *{cat.upper()}*\n\nএখন রিসোর্সের নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.text and message.text.startswith('/'):
        return
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্স আনলক করতে কত কয়েন লাগবে লিখুন (যেমন: 15):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    if message.text and message.text.startswith('/'):
        return
    try:
        admin_temp_data[message.from_user.id]['coins'] = int(message.text.strip())
        cat = admin_temp_data[message.from_user.id]['type']
        
        if cat == 'xml':
            bot.reply_to(message, "🎬 **XML প্রিভিউ ভিডিও লিংক (অথবা ইউটিউব লিংক) পাঠান:**")
            bot.register_next_step_handler(message, get_xml_video)
        else:
            bot.reply_to(message, "🖼️ **থাম্বনেইল ইমেজ দিন (সরাসরি ছবি অথবা ফ্রি হোস্টিং ইমেজ লিংক পাঠান):**")
            bot.register_next_step_handler(message, get_image_first)
    except ValueError:
        bot.reply_to(message, "⚠️ কয়েনের পরিমাণ সংখ্যায় দিন:")
        bot.register_next_step_handler(message, get_coins)

def get_image_first(message):
    if message.text and message.text.startswith('/'):
        return
    if message.photo:
        try:
            photo_file_id = message.photo[-1].file_id
            admin_temp_data[message.from_user.id]['image_file_id'] = photo_file_id
            file_info = bot.get_file(photo_file_id)
            img_bytes = bot.download_file(file_info.file_path)
            admin_temp_data[message.from_user.id]['image'] = compress_image_data(img_bytes)
        except Exception as e:
            bot.reply_to(message, f"❌ ত্রুটি: {e}")
            return
    elif message.text and message.text.strip().startswith("http"):
        admin_temp_data[message.from_user.id]['image'] = compress_image_data(message.text.strip())
    else:
        bot.reply_to(message, "⚠️️ অনুগ্রহ করে ছবি অথবা সঠিক সরাসরি লিংক পাঠান:")
        bot.register_next_step_handler(message, get_image_first)
        return

    msg = bot.reply_to(message, "📂 **এখন মূল ফন্ট বা PLP ফাইল (ডকুমেন্ট হিসেবে) পাঠান (শেষ হলে 'done' লিখুন):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_batch_files_or_link)

def get_xml_video(message):
    if message.text and message.text.startswith('/'):
        return
    if message.video:
        vid_id = message.video.file_id
        admin_temp_data[message.from_user.id]['video_file_id'] = vid_id
        file_info = bot.get_file(vid_id)
        admin_temp_data[message.from_user.id]['video'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    elif message.text and message.text.strip().startswith("http"):
        admin_temp_data[message.from_user.id]['video'] = message.text.strip()
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ভিডিও ফাইল অথবা ইউটিউব লিংক পাঠান:")
        bot.register_next_step_handler(message, get_xml_video)
        return

    msg = bot.reply_to(message, "📁 ভিডিও যুক্ত হয়েছে! এখন **XML ফাইল পাঠান** (শেষ হলে 'done' লিখুন):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_batch_files_or_link)

def get_batch_files_or_link(message):
    user_id = message.from_user.id
    if user_id not in admin_temp_data:
        return
    if message.text and message.text.startswith('/'):
        return
    if message.text and message.text.strip().startswith("http"):
        admin_temp_data[user_id]['download_link'] = message.text.strip()
        admin_temp_data[user_id]['file_ids'] = []
        save_resource_to_firebase(message)
        return
    if message.text and ('done' in message.text.lower() or 'শেষ' in message.text):
        if not admin_temp_data[user_id].get('file_ids'):
            bot.reply_to(message, "⚠️ কোনো ফাইল আপলোড করা হয়নি!")
            bot.register_next_step_handler(message, get_batch_files_or_link)
            return
        save_resource_to_firebase(message)
        return
    if message.document:
        admin_temp_data[user_id]['file_ids'].append(message.document.file_id)
        count = len(admin_temp_data[user_id]['file_ids'])
        bot.reply_to(message, f"📥 ফাইল ({count}) যুক্ত হয়েছে! আরও থাকলে পাঠান অথবা শেষ হলে 'done' লিখুন।")
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(message, "⚠️ ডকুমেন্ট ফাইল পাঠান অথবা কাজ শেষ হলে 'done' লিখুন:")
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
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ হ্যাঁ, চ্যানেলে পোস্ট করুন", callback_data=f"ch_post:yes:{res_key}"),
            InlineKeyboardButton("❌ না, প্রয়োজন নেই", callback_data=f"ch_post:no:{res_key}")
        )
        bot.reply_to(message, f"🎉 **রিসোর্স সফলভাবে যুক্ত হয়েছে!**\n\n📢 চ্যানেলে পোস্ট করতে চান?", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ ফায়ারবেজে সেভ হয়নি।")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ch_post:'))
def handle_channel_post_decision(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    parts = call.data.split(":")
    decision = parts[1]
    res_key = parts[2]
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    if decision == "no":
        bot.send_message(call.message.chat.id, "✅ কেবল মিনি অ্যাপে সেভ করা হয়েছে।", reply_markup=get_admin_reply_keyboard())
        return
    try:
        item_res = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json")
        resource = item_res.json()
        if resource:
            res_type_upper = resource['type'].upper()
            channel_caption = f"🔥 *নতুন প্রিমিয়াম {res_type_upper} যুক্ত হয়েছে!*\n\n📌 *নাম:* {resource['name']}\n🪙 *মূল্য:* {resource['coins']} কয়েন\n\n🚀 সংগ্রহ করতে নিচের বাটন চাপুন:"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 ডাউনলোড করুন", url=f"https://t.me/{BOT_USERNAME}?start=ref_{ADMIN_ID}"))
            if resource.get('video'):
                bot.send_video(CHANNEL_ID, resource['video'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            elif resource.get('image'):
                bot.send_photo(CHANNEL_ID, resource['image'], caption=channel_caption, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(CHANNEL_ID, channel_caption, parse_mode="Markdown", reply_markup=markup)
            bot.send_message(call.message.chat.id, "🎉 চ্যানেলে পোস্ট করা হয়েছে!", reply_markup=get_admin_reply_keyboard())
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ সমস্যা: {e}", reply_markup=get_admin_reply_keyboard())

# --- Other Admin Flow Functions ---
def start_edit_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    edit_sessions[message.from_user.id] = {}
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP", callback_data="edcat:plp"),
        InlineKeyboardButton("🔤 Font", callback_data="edcat:font"),
        InlineKeyboardButton("⚡ XML", callback_data="edcat:xml")
    )
    bot.send_message(message.chat.id, "🛠️ **কোন ক্যাটাগরির ফাইল আপডেট করতে চান?**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edcat:'))
def handle_edit_category(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    cat = call.data.split(":")[1]
    edit_sessions[call.from_user.id] = {'type': cat}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    msg = bot.send_message(call.message.chat.id, f"✅ নির্বাচিত ক্যাটাগরি: *{cat.upper()}*\n\nএখন কোন ফাইল আপডেট করতে চান তার নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, find_resource_by_name)

def find_resource_by_name(message):
    if message.text and message.text.startswith('/'):
        return
    search_name = (message.text or "").strip().lower()
    selected_type = edit_sessions.get(message.from_user.id, {}).get('type', 'plp')
    try:
        res = requests.get(f"{FIREBASE_BASE}/resources.json").json() or {}
        matched_items = {}
        for key, item in res.items():
            if item.get('type') == selected_type and search_name in item.get('name', '').lower():
                matched_items[key] = item
        if not matched_items:
            msg = bot.send_message(message.chat.id, f"❌ কোনো ফাইল পাওয়া যায়নি! সঠিক নাম আবার পাঠান:")
            bot.register_next_step_handler(msg, find_resource_by_name)
            return
        if len(matched_items) == 1:
            res_key = list(matched_items.keys())[0]
            show_edit_options(message.chat.id, res_key, matched_items[res_key])
        else:
            markup = InlineKeyboardMarkup(row_width=1)
            for k, it in matched_items.items():
                markup.add(InlineKeyboardButton(f"📁 {it.get('name')}", callback_data=f"selres:{k}"))
            bot.send_message(message.chat.id, "🎯 একাধিক ফাইল মিলেছে। একটি সিলেক্ট করুন:", reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('selres:'))
def select_from_matched(call):
    res_key = call.data.split(":")[1]
    res_data = requests.get(f"{FIREBASE_BASE}/resources/{res_key}.json").json()
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    show_edit_options(call.message.chat.id, res_key, res_data)

def show_edit_options(chat_id, res_key, item_data):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 নাম পরিবর্তন", callback_data=f"do_upd:{res_key}:name"),
        InlineKeyboardButton("🪙 কয়েন পরিবর্তন", callback_data=f"do_upd:{res_key}:coins"),
        InlineKeyboardButton("🖼️ থাম্বনেইল ইমেজ", callback_data=f"do_upd:{res_key}:image"),
        InlineKeyboardButton("🗑️ রিসোর্স ডিলিট", callback_data=f"do_del:{res_key}")
    )
    bot.send_message(chat_id, f"🎯 **রিসোর্স:** {item_data.get('name')}\nকি পরিবর্তন করতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('do_upd:'))
def prompt_for_field(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    _, res_key, field = call.data.split(":")
    edit_sessions[call.from_user.id] = {'key': res_key, 'field': field}
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    msg = bot.send_message(call.message.chat.id, f"✍️ নতুন মান লিখে পাঠান:")
    bot.register_next_step_handler(msg, save_updated_field)

def save_updated_field(message):
    user_id = message.from_user.id
    if user_id not in edit_sessions:
        return
    session = edit_sessions[user_id]
    res_key = session['key']
    field = session['field']
    new_val = message.text.strip()
    if field == "coins":
        try:
            new_val = int(new_val)
        except ValueError:
            bot.reply_to(message, "⚠️ সংখ্যায় দিন:")
            bot.register_next_step_handler(message, save_updated_field)
            return
    elif field == "image" and message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        img_bytes = bot.download_file(file_info.file_path)
        new_val = compress_image_data(img_bytes)

    requests.patch(f"{FIREBASE_BASE}/resources/{res_key}.json", json={field: new_val})
    del edit_sessions[user_id]
    bot.reply_to(message, "🎉 সফলভাবে আপডেট হয়েছে!", reply_markup=get_admin_reply_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('do_del:'))
def delete_item(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    res_key = call.data.split(":")[1]
    requests.delete(f"{FIREBASE_BASE}/resources/{res_key}.json")
    bot.answer_callback_query(call.id, "রিসোর্স ডিলিট করা হয়েছে!", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

def start_coin_management_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "👤 যে ইউজারের কয়েন দিতে চান তার **Telegram User ID** লিখে পাঠান:")
    bot.register_next_step_handler(msg, process_coin_uid)

def process_coin_uid(message):
    uid = message.text.strip()
    coin_sessions[message.from_user.id] = {'target_id': uid}
    msg = bot.send_message(message.chat.id, "🪙 কত কয়েন যোগ করতে চান লিখে পাঠান (যেমন: 100):")
    bot.register_next_step_handler(msg, process_coin_amount)

def process_coin_amount(message):
    admin_id = message.from_user.id
    if admin_id not in coin_sessions:
        return
    try:
        amount = int(message.text.strip())
        target_id = coin_sessions[admin_id]['target_id']
        u_data = requests.get(f"{FIREBASE_BASE}/users/{target_id}.json").json() or {}
        curr = u_data.get('coins', 0)
        new_c = max(0, curr + amount)
        requests.patch(f"{FIREBASE_BASE}/users/{target_id}.json", json={"coins": new_c})
        del coin_sessions[admin_id]
        bot.reply_to(message, f"✅ সফল! বর্তমান কয়েন: *{new_c}*", parse_mode="Markdown", reply_markup=get_admin_reply_keyboard())
    except ValueError:
        bot.reply_to(message, "⚠️ সংখ্যায় দিন:")
        bot.register_next_step_handler(message, process_coin_amount)

def show_download_logs_cmd(message):
    res = requests.get(f"{FIREBASE_BASE}/download_logs.json").json() or {}
    if not res:
        bot.reply_to(message, "📂 এখনো কোনো ডাউনলোড হিস্ট্রি নেই।", reply_markup=get_admin_reply_keyboard())
        return
    txt = "📊 **শেষ ১০টি ডাউনলোড লগ:**\n\n"
    for k, log in list(res.items())[-10:]:
        txt += f"👤 {log.get('user_name')} | 📦 {log.get('resource_name')} | ⏰ {log.get('time')}\n"
    bot.reply_to(message, txt, parse_mode="Markdown", reply_markup=get_admin_reply_keyboard())

def start_broadcast_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "📢 সকল ইউজারের কাছে পাঠানোর জন্য মেসেজ লিখে পাঠান:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    users = requests.get(f"{FIREBASE_BASE}/users.json").json() or {}
    for uid in users.keys():
        try:
            bot.send_message(uid, f"📢 **অফিসিয়াল নোটিশ:**\n\n{message.text}", parse_mode="Markdown")
        except Exception:
            pass
    bot.reply_to(message, "✅ ব্রডকাস্ট সম্পন্ন হয়েছে!", reply_markup=get_admin_reply_keyboard())

def start_ban_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "🚫 ব্যান করতে চান এমন ইউজারের **User ID** লিখে পাঠান:")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    uid = message.text.strip()
    requests.put(f"{FIREBASE_BASE}/banned_users/{uid}.json", json=True)
    bot.reply_to(message, f"🚫 আইডি `{uid}` সফলভাবে ব্যান করা হয়েছে!", parse_mode="Markdown", reply_markup=get_admin_reply_keyboard())

def start_promo_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "🎁 প্রোমো কোডের নাম লিখুন (যেমন: `VIP50`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_promo_name)

def get_promo_name(message):
    code = message.text.strip().upper()
    promo_sessions[message.from_user.id] = {'code': code}
    msg = bot.send_message(message.chat.id, "🪙 এই কোড ব্যবহার করলে কত কয়েন পাবে সংখ্যায় লিখুন:")
    bot.register_next_step_handler(msg, get_promo_coins)

def get_promo_coins(message):
    admin_id = message.from_user.id
    if admin_id not in promo_sessions:
        return
    try:
        coins = int(message.text.strip())
        code = promo_sessions[admin_id]['code']
        del promo_sessions[admin_id]
        requests.put(f"{FIREBASE_BASE}/promo_codes/{code}.json", json={"coins": coins, "used_by": {}})
        bot.reply_to(message, f"🎉 প্রোমো কোড `{code}` তৈরি হয়েছে!", parse_mode="Markdown", reply_markup=get_admin_reply_keyboard())
    except ValueError:
        bot.reply_to(message, "⚠️ সংখ্যায় দিন:")
        bot.register_next_step_handler(message, get_promo_coins)

def start_user_inspect_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "🔍 চেক করতে চান এমন ইউজারের **User ID** লিখুন:")
    bot.register_next_step_handler(msg, process_inspect)

def process_inspect(message):
    uid = message.text.strip()
    u = requests.get(f"{FIREBASE_BASE}/users/{uid}.json").json()
    if not u:
        bot.reply_to(message, "❌ পাওয়া যায়নি!", reply_markup=get_admin_reply_keyboard())
        return
    info = f"👤 নাম: {u.get('name')}\n🪙 কয়েন: {u.get('coins')}\n👥 রেফার: {u.get('refers')}"
    bot.reply_to(message, info, reply_markup=get_admin_reply_keyboard())

# --- Start Command Handler ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "❌ আপনি ব্যান হয়েছেন!")
        return

    try:
        u_res = requests.get(f"{FIREBASE_BASE}/users/{user_id}.json").json()
        if not u_res:
            requests.put(f"{FIREBASE_BASE}/users/{user_id}.json", json={
                "name": user_name, "username": message.from_user.username or "", "coins": 20, "refers": 0, "daily_ads": {}
            })
    except Exception:
        pass

    if len(args) > 1 and args[1].startswith("get_"):
        process_resource_delivery(message.chat.id, args[1], message.from_user)
        return

    if not is_user_member(user_id):
        target_arg = args[1] if len(args) > 1 else ""
        bot.send_message(
            message.chat.id,
            f"👋 হ্যালো *{user_name}*!\n\n⚠️ **বট ব্যবহার করতে আমাদের চ্যানেলে জয়েন করা বাধ্যতামূলক।**",
            parse_mode="Markdown",
            reply_markup=get_force_sub_keyboard(target_arg)
        )
        return

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👑 **অ্যাডমিন কন্ট্রোল প্যানেল (Admin Panel)**\n\nনিচের বাটন থেকে আপনার প্রয়োজনীয় অপশন সিলেক্ট করুন:",
            parse_mode="Markdown",
            reply_markup=get_admin_reply_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"👋 স্বাগতম *{user_name}*!\n\n💎 প্রিমিয়াম রিসোর্স এবং ফন্ট কালেকশনে আপনাকে স্বাগতম। নিচের দরকারি বাটনগুলো ব্যবহার করুন:",
            parse_mode="Markdown",
            reply_markup=get_user_reply_keyboard()
        )

# --- Resource Delivery Logic ---
def process_resource_delivery(chat_id, arg_text, user_obj=None):
    file_key = arg_text.replace("get_", "").split("_from_")[0]
    bot.send_message(chat_id, "⏳ আপনার ফাইল প্রস্তুত করা হচ্ছে...")
    try:
        res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
        item = res.json()
        if item:
            res_name = item.get('name', 'Resource')
            if item.get("download_link"):
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড", url=item["download_link"]))
                bot.send_message(chat_id, f"🎁 রিসোর্স: *{res_name}*", parse_mode="Markdown", reply_markup=markup)
                return
            file_ids = item.get("file_ids") or ([] if not item.get("file_id") else [item.get("file_id")])
            for idx, fid in enumerate(file_ids, 1):
                bot.send_document(chat_id, fid, caption=f"🎁 ফাইল ({idx}): *{res_name}*", parse_mode="Markdown")
                time.sleep(0.3)
            bot.send_message(chat_id, "✅ সমস্ত ফাইল সফলভাবে পাঠানো হয়েছে!", reply_markup=get_user_reply_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ ত্রুটি: {e}")

# --- Setup Webhook automatically when python main.py runs ---
def setup_webhook():
    if not RENDER_EXTERNAL_URL:
        return
    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    for attempt in range(1, 6):
        try:
            bot.remove_webhook(drop_pending_updates=True)
            time.sleep(1)
            bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            print(f"Webhook successfully set to: {webhook_url}")
            return
        except Exception as e:
            print(f"Webhook setup attempt {attempt} failed: {e}")
            time.sleep(2)

if __name__ == "__main__":
    print("Setting up Webhook and starting Flask App via python main.py...")
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)
