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
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from flask import Flask, request, jsonify
from threading import Thread

# --- Bot Configuration ---
BOT_TOKEN = "8815920877:AAFGwxjKGoo9HhcsVOcbBhi9JMqXT-LLMsY"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"

# Render External URL
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}
broadcast_sessions = {}
ban_sessions = {}
promo_sessions = {}
user_inspect_sessions = {}
user_earn_sessions = {}

# --- Flask Server & Webhook Route ---
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
        
        # ২০০x২০০ পিক্সেল এইচডি সাইজে থাম্বনেইল তৈরি
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

def get_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🚀 Premium resource 💎", web_app=WebAppInfo(url=WEB_APP_URL)),
        InlineKeyboardButton("📂 ফাইল দিয়ে কয়েন আয় করুন (Earn)", callback_data="earn_coins_start"),
        InlineKeyboardButton("📖 সহায়তা ও নির্দেশিকা (Help)", callback_data="help_menu")
    )
    return markup

def get_admin_dashboard_keyboard():
    # অ্যাড সেট করার বাটন এখান থেকে সম্পূর্ণ রিমুভ করা হয়েছে
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

def cancel_process(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    uid = message.from_user.id
    for s_dict in [admin_temp_data, edit_sessions, coin_sessions, broadcast_sessions, ban_sessions, promo_sessions, user_inspect_sessions, user_earn_sessions]:
        if uid in s_dict:
            del s_dict[uid]

    if int(uid) == int(ADMIN_ID):
        bot.send_message(message.chat.id, "❌ প্রসেসটি বাতিল করা হয়েছে।", reply_markup=get_admin_dashboard_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())

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
            f"✅ **সফলভাবে সম্পন্ন হয়েছে!**\n\nডেটাবেজের আগের মোট **{count}টি** বড় ইমেজ অটো কম্প্রেস হয়ে নতুন করে এইচডি (200x200) আকারে সেভ হয়ে গেছে! 🚀",
            message.chat.id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(f"❌ সমস্যা হয়েছে: {str(e)}", message.chat.id, status_msg.message_id)

# --- User Earn Coins Flow ---
@bot.callback_query_handler(func=lambda call: call.data == "earn_coins_start")
def start_user_earn_flow(call):
    uid = call.from_user.id
    if is_user_banned(uid):
        bot.answer_callback_query(call.id, "❌ আপনি ব্যান হয়েছেন!", show_alert=True)
        return

    user_earn_sessions[uid] = {}
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🎨 PLP ফাইল", callback_data="earntype:plp"),
        InlineKeyboardButton("🔤 ফন্ট", callback_data="earntype:font"),
        InlineKeyboardButton("⚡ XML প্রজেক্ট", callback_data="earntype:xml")
    )
    bot.send_message(
        call.message.chat.id,
        "📂 **ফাইল দিয়ে কয়েন আয় প্যানেল**\n\nআপনি কোন ক্যাটাগরির ফাইল আপলোড করতে চান?",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('earntype:'))
def handle_earn_type(call):
    uid = call.from_user.id
    cat = call.data.split(":")[1]
    user_earn_sessions[uid] = {'type': cat, 'file_ids': []}
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(call.message.chat.id, f"✅ ক্যাটাগরি: *{cat.upper()}*\n\nএখন এই ফাইলের একটি সুন্দর নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_user_earn_name)

def get_user_earn_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    uid = message.from_user.id
    if uid not in user_earn_sessions:
        return
    user_earn_sessions[uid]['name'] = message.text.strip()
    msg = bot.reply_to(message, "🖼️ **ফাইলের প্রিভিউ থাম্বনেইল ছবি পাঠান (ছবি পাঠানোর সাথে সাথে এটি অটো কম্প্রেস হয়ে যাবে):**")
    bot.register_next_step_handler(msg, get_user_earn_image)

def get_user_earn_image(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
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
            bot.reply_to(message, f"❌ ছবি প্রসেস করতে সমস্যা হয়েছে: {e}")
            return
    elif message.text and message.text.strip().startswith("http"):
        user_earn_sessions[uid]['image'] = compress_image_data(message.text.strip())
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ছবি পাঠান:")
        bot.register_next_step_handler(message, get_user_earn_image)
        return

    msg = bot.reply_to(
        message,
        "📂 **মূল ফাইল(গুলো) ডকুমেন্ট হিসেবে পাঠান:**\n\n(সব ফাইল পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন)",
        reply_markup=get_file_collection_keyboard(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, collect_user_earn_files)

def collect_user_earn_files(message):
    uid = message.from_user.id
    if uid not in user_earn_sessions:
        return

    if message.text and message.text.strip().lower() in ['/cancel', 'cancel', '❌ বাতিল করুন']:
        cancel_process(message)
        return

    if message.text and message.text.strip() in ['/done', 'done', '✅ আপলোড সম্পন্ন']:
        session = user_earn_sessions.pop(uid, None)
        if not session or not session.get('file_ids'):
            bot.reply_to(message, "⚠️ আপনি কোনো ফাইল আপলোড করেননি! প্রসেস বাতিল করা হলো।", reply_markup=get_main_keyboard())
            return

        submit_to_admin_review(message, session, uid)
        return

    if message.document:
        user_earn_sessions[uid]['file_ids'].append(message.document.file_id)
        count = len(user_earn_sessions[uid]['file_ids'])
        bot.reply_to(message, f"📥 ফাইল ({count}) যুক্ত হয়েছে! আরও ফাইল থাকলে পাঠান অথবা **✅ আপলোড সম্পন্ন** চাপুন।")
        bot.register_next_step_handler(message, collect_user_earn_files)
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ডকুমেন্ট ফাইল পাঠান অথবা **✅ আপলোড সম্পন্ন** চাপুন:")
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
            InlineKeyboardButton("✅ এপ্রুভ করুন (কয়েন দিন)", callback_data=f"rev_sub:approve:{sub_key}:{uid}"),
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
            "🎉 **আপনার ফাইল সফলভাবে অ্যাডমিনের কাছে রিভিউয়ের জন্য জমা হয়েছে!**\n\n"
            "অ্যাডমিন ফাইলটি চেক করে অনুমোদন দিলেই আপনার অ্যাকাউন্টে নির্দিষ্ট পরিমাণ কয়েন যুক্ত করে দেওয়া হবে। ধন্যবাদ!",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ সাবমিট করতে সমস্যা হয়েছে: {e}", reply_markup=get_main_keyboard())

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
            bot.answer_callback_query(call.id, "❌ এই সাবমিশনটি আর খুঁজে পাওয়া যায়নি!", show_alert=True)
            return

        if action == "reject":
            requests.delete(f"{FIREBASE_BASE}/pending_submissions/{sub_key}.json")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(target_id, f"❌ দুঃখিত! আপনার সাবমিট করা ফাইল '{sub_data['name']}' অ্যাডমিন কর্তৃক রিজেক্ট করা হয়েছে।")
            bot.answer_callback_query(call.id, "সফলভাবে রিজেক্ট করা হয়েছে।", show_alert=False)
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

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            target_id,
            f"🎉 **অভিনন্দন! আপনার ফাইল এপ্রুভ হয়েছে।**\n\n"
            f"📦 ফাইল: {sub_data['name']}\n"
            f"🎁 উপহার স্বরূপ আপনার অ্যাকাউন্টে যুক্ত হয়েছে: *{reward_coins} 🪙* কয়েন!\n"
            f"বর্তমান ব্যালেন্স: *{new_c} 🪙*",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, f"সফল! ইউজারকে {reward_coins} কয়েন দেওয়া হয়েছে।", show_alert=True)

    except Exception as e:
        bot.answer_callback_query(call.id, f"ত্রুটি: {e}", show_alert=True)

# --- Help Menu Handler ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('help') or call.data == 'help_menu')
def handle_help_menu(call):
    data = call.data
    markup = InlineKeyboardMarkup(row_width=1)

    if data == "help_menu":
        markup.add(
            InlineKeyboardButton("📥 কিভাবে ফাইল ডাউনলোড করব?", callback_data="help_download"),
            InlineKeyboardButton("📂 ফাইল দিয়ে কয়েন আয় করার নিয়ম", callback_data="help_earn"),
            InlineKeyboardButton("🪙 কিভাবে ফ্রি কয়েন পাবো?", callback_data="help_coins"),
            InlineKeyboardButton("🔗 রেফার করে আয় করার নিয়ম", callback_data="help_refer"),
            InlineKeyboardButton("📂 ফন্ট ও পিএলপি ব্যবহারের নিয়ম", callback_data="help_usage"),
            InlineKeyboardButton("◀️ মূল মেনুতে ফিরুন", callback_data="help_back")
        )
        text = "📖 **সহায়তা ও নির্দেশিকা কেন্দ্র**\n\nযে বিষয়টি সম্পর্কে জানতে চান নিচের বাটনে ক্লিক করুন:"
    elif data == "help_download":
        markup.add(InlineKeyboardButton("◀️ পেছনের মেনুতে যান", callback_data="help_menu"))
        text = (
            "📥 **কিভাবে ফাইল ডাউনলোড করবেন?**\n\n"
            "১. প্রথমে মিনি অ্যাপ ওপেন করে আপনার পছন্দের PLP, ফন্ট বা XML ফাইলে যান।\n"
            "২. ফাইল আনলক করতে আপনার ওয়ালেটে নির্দিষ্ট পরিমাণ কয়েন থাকতে হবে।\n"
            "৩. 'ডাউনলোড করুন' বাটনে চাপ দিলে ৫ সেকেন্ডের একটি কাউন্টডাউন ও বিজ্ঞাপন আসবে।\n"
            "৪. প্রসেস শেষ হওয়ার পর 'ইনবক্সে ফাইল নিন' বাটনে ক্লিক করলেই বট সরাসরি আপনার টেলিগ্রাম ইনবক্সে ফাইল পাঠিয়ে দেবে!"
        )
    elif data == "help_earn":
        markup.add(InlineKeyboardButton("◀️ পেছনের মেনুতে যান", callback_data="help_menu"))
        text = (
            "📂 **ফাইল দিয়ে কয়েন আয় করার নিয়ম**\n\n"
            "• বটের মূল মেনু থেকে **'📂 ফাইল দিয়ে কয়েন আয় করুন (Earn)'** বাটনে ক্লিক করুন।\n"
            "• আপনার কাছে থাকা ভালো মানের PLP, ফন্ট বা XML ফাইল এবং থাম্বনেইল ছবি আপলোড করুন (ছবি অটোমেটিক অপ্টিমাইজ ও কম্প্রেস হয়ে যাবে)।\n"
            "• অ্যাডমিন ফাইলটি চেক ও রিভিউ করে এপ্রুভ করার সাথে সাথেই আপনার অ্যাকাউন্টে ফ্রি কয়েন জমা হয়ে যাবে!"
        )
    elif data == "help_coins":
        markup.add(InlineKeyboardButton("◀️ পেছনের মেনুতে যান", callback_data="help_menu"))
        text = (
            "🪙 **কিভাবে ফ্রিতে কয়েন অর্জন করবেন?**\n\n"
            "• **ডেইলি চেক-ইন:** প্রতিদিন অ্যাপে ঢুকে একবার চেক-ইন করে প্রতিদিন ফ্রি কয়েন নিন।\n"
            "• **লাকি হুইল স্পিন:** চাকা ঘুরিয়ে প্রতিদিন ভাগ্য পরীক্ষা করে কয়েন জিতুন।\n"
            "• **স্ক্র্যাচ কার্ড:** কার্ড ঘষে নিশ্চিত রিওয়ার্ড বা কয়েন সংগ্রহ করুন।\n"
            "• **চ্যানেল টাস্ক:** আমাদের অফিসিয়াল টেলিগ্রাম চ্যানেলে জয়েন করে ভেরিফাই করলেই পেয়ে যাবেন বোনাস কয়েন!"
        )
    elif data == "help_refer":
        markup.add(InlineKeyboardButton("◀️ পেছনের মেনুতে যান", callback_data="help_menu"))
        text = (
            "🔗 **রেফার করে আয় করার নিয়ম**\n\n"
            "• 'রেফার' পেজ থেকে আপনার ইউনিক রেফারেল লিংকটি বন্ধুদের সাথে শেয়ার করুন।\n"
            "• আপনার লিংকের মাধ্যমে কোনো নতুন মেম্বার জয়েন করলে এবং সে মিনি অ্যাপ থেকে কমপক্ষে **১টি রিসোর্স ডাউনলোড করলে** আপনি পাবেন **৫০ কয়েন** বোনাস!"
        )
    elif data == "help_usage":
        markup.add(InlineKeyboardButton("◀️ পেছনের মেনুতে যান", callback_data="help_menu"))
        text = (
            "📂 **ফন্ট ও পিএলপি ফাইল ব্যবহারের নিয়ম**\n\n"
            "• **PLP ফাইল:** পিক্সেল ল্যাব (PixelLab) অ্যাপের .plp প্রজেক্ট ফোল্ডারে রেখে ওপেন করতে হয়।\n"
            "• **ফন্ট ফাইল:** MT Manager বা পিক্সেল ল্যাবের ফন্ট ফোল্ডারে ফন্টগুলো এড করে কাস্টম ডিজাইন করতে পারবেন।\n"
            "• **XML ফাইল:** Sketchware বা প্রজেক্টে ইম্পোর্ট করে ব্যবহার করা যায়।"
        )
    elif data == "help_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "👋 মূল মেনুতে স্বাগতম:", reply_markup=get_main_keyboard())
        return

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        pass

def process_resource_delivery(chat_id, arg_text, user_obj=None):
    file_key = arg_text.replace("get_", "").split("_from_")[0]
    bot.send_message(chat_id, "⏳ আপনার ফাইল প্রস্তুত করা হচ্ছে...")
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
                        f"🔔 **নতুন ফাইল ডাউনলোড হয়েছে!**\n\n"
                        f"👤 ইউজার: *{user_obj.first_name}*\n"
                        f"🆔 ইউজার আইডি: `{user_obj.id}`\n"
                        f"📦 রিসোর্স: {res_name}\n"
                        f"📁 ক্যাটাগরি: {res_type}\n"
                        f"⏰ সময়: {current_time}"
                    )
                    bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
                except Exception:
                    pass

            if item.get("download_link"):
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড করুন", url=item["download_link"]))
                markup.add(InlineKeyboardButton("🚀 পুনরায় অ্যাপ ওপেন করুন", web_app=WebAppInfo(url=WEB_APP_URL)))
                bot.send_message(
                    chat_id,
                    f"🎁 আপনার রিসোর্স: *{res_name}*\n"
                    f"📁 ক্যাটাগরি: *{res_type}*\n"
                    f"🪙 খরচ হওয়া কয়েন: {item.get('coins', 0)}\n\n"
                    "🔗 নিচের বাটন থেকে ফাইল সংগ্রহ করুন:",
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
                        "📂 সেভ করতে ফাইলের ওপর ট্যাপ করুন অথবা ডাউনলোড কোণায় ৩-ডট (⋮) এ ক্লিক করে **'Save to Downloads'** করুন।"
                    )
                    bot.send_document(chat_id, fid, caption=cap, parse_mode="Markdown")
                    time.sleep(0.3)
                bot.send_message(chat_id, "✅ আপনার সমস্ত ফাইল সফলভাবে ইনবক্সে ডেলিভারি করা হয়েছে!", reply_markup=get_main_keyboard())
                return
        else:
            bot.send_message(chat_id, "❌ ফাইলটি ডাটাবেজে পাওয়া যায়নি।", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ রিসোর্স ডেলিভারিতে সমস্যা দেখা দিচ্ছে: {e}", reply_markup=get_main_keyboard())

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
                    bot.send_message(referrer_id, "🎉 অভিনন্দন! নতুন মেম্বার আপনার রেফারলের মাধ্যমে জয়েন করেছেন। আপনি পেয়েছেন +50 🪙 কয়েন!")
            except Exception:
                pass

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👑 **অ্যাডমিন প্যানেলে স্বাগতম!**\n\n"
            "নিচের বাটন অথবা কমান্ড ব্যবহার করে যেকোনো কাজ পরিচালনা করতে পারেন:",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
        bot.send_message(message.chat.id, "মিনি অ্যাপে যেতে নিচের বাটন চাপুন:", reply_markup=get_main_keyboard())
        return

    target_arg = args[1] if len(args) > 1 else ""
    if not is_user_member(user_id):
        bot.send_message(
            message.chat.id,
            f"👋 হ্যালো *{user_name}*!\n\n"
            "⚠️ **বট এবং মিনি অ্যাপ ব্যবহার করতে আমাদের অফিসিয়াল টেলিগ্রাম চ্যানেলে জয়েন করা বাধ্যতামূলক।**\n\n"
            "👉 নিচের বাটনে ক্লিক করে চ্যানেলে জয়েন করুন এবং পরবর্তীতে **'🔄 ভেরিফাই করুন'** বাটন চাপুন:",
            parse_mode="Markdown",
            reply_markup=get_force_sub_keyboard(target_arg)
        )
        return

    bot.send_message(
        message.chat.id,
        f"👋 হ্যালো {user_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে স্বাগতম। নিচের বাটনে ক্লিক করে অ্যাপ ওপেন করুন অথবা সহায়তা মেনু দেখুন:",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda m: int(m.from_user.id) == int(ADMIN_ID) and m.text and not m.reply_to_message)
def handle_all_admin_text(message):
    text = message.text.strip().lower()

    if text in ['/cancel', 'cancel', 'বাতিল', '❌ বাতিল করুন']:
        cancel_process(message)
        return

    if text in ['/edit', 'edit', '✏️ রিসোর্স এডিট/আপডেট', 'update']:
        start_edit_flow(message)
        return

    if text in ['/add', 'add', '➕ নতুন রিসোর্স যুক্ত করুন']:
        start_add_flow(message)
        return

    if text in ['🪙 কয়েন আপডেট/ম্যানেজ', 'coin', 'coins', '/coins']:
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
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(
        call.message.chat.id,
        f"✅ নির্বাচিত ক্যাটাগরি: *{cat.upper()}*\n\n"
        "এখন কোন ফাইল আপডেট করতে চান তার **নাম অথবা নামের কিছু অংশ** লিখে পাঠান:",
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
                f"❌ *{selected_type.upper()}* ক্যাটাগরিতে '{message.text}' নামের কোনো ফাইল পাওয়া যায়নি!\n\n"
                "সঠিক নাম লিখে আবার পাঠান (অথवा '❌ বাতিল করুন' চাপুন):",
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
            bot.send_message(message.chat.id, "🎯 একাধিক ফাইল পাওয়া গেছে। নির্দিষ্ট ফাইলটি নির্বাচন করুন:", reply_markup=markup)

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
            InlineKeyboardButton("🖼️ থাম্বনেইল ইমেজ", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("⚡ মূল XML ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )
    elif r_type == 'plp':
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ইমেজ", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("🔗 ড্রাইভ লিংক পরিবর্তন", callback_data=f"do_upd:{res_key}:download_link"),
            InlineKeyboardButton("📂 PLP ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )
    else:
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ইমেজ", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("📁 ফন্ট ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:files")
        )

    markup.add(InlineKeyboardButton("🗑️ রিসোর্স ডিলিট করুন", callback_data=f"do_del:{res_key}"))
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
            "📂 **নতুন ফাইল(গুলো) পাঠান:**\n\n"
            "আপনি এক বা একাধিক ডকুমেন্ট ফাইল পাঠাতে পারেন। সব ফাইল পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন:",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, collect_edit_files)
        return

    prompts = {
        "name": "নতুন নাম লিখে পাঠান:",
        "coins": "নতুন কয়েনের সংখ্যা লিখে পাঠান (যেমন: 15):",
        "image": "নতুন থাম্বনেইল ইমেজ অথবা সরাসরি লিংক (ড্রাইভ লিংক) পাঠান:",
        "video": "নতুন প্রিভিউ ভিডিও ফাইল, ইউটিউব লিংক অথবা সরাসরি লিংক পাঠান:",
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
            f"📥 ফাইল ({count}) গ্রহণ করা হয়েছে!\n\nআরও ফাইল থাকলে পাঠান, অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন।"
        )
        bot.register_next_step_handler(message, collect_edit_files)
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ফাইলটি ডকুমেন্ট হিসেবে পাঠান অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন:")
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
            bot.reply_to(message, "⚠️ কয়েনের পরিমাণ সংখ্যায় হতে হবে। আবার লিখে পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return

    elif field == "name":
        if not message.text:
            bot.reply_to(message, "⚠️ টেক্সট আকারে নাম পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.text.strip()

    elif field == "image":
        if message.photo:
            try:
                file_id = message.photo[-1].file_id
                file_info = bot.get_file(file_id)
                img_bytes = bot.download_file(file_info.file_path)
                new_val = compress_image_data(img_bytes)
            except Exception as e:
                bot.reply_to(message, f"❌ ছবি প্রসেসে ত্রুটি: {e}")
                return
        elif message.text and message.text.strip().startswith("http"):
            new_val = compress_image_data(message.text.strip())
        else:
            bot.reply_to(message, "⚠️ অনুগ্রহ করে ছবি অথবা সঠিক সরাসরি লিংক পাঠান:")
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
            bot.reply_to(message, "⚠️ অনুগ্রহ করে ভিডিও ফাইল, ইউটিউব লিংক অথবা সঠিক সরাসরি লিংক পাঠান:")
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
                f"🎉 **সফলভাবে আপডেট হয়েছে!**\n\nফাইলের **{field}** সফলভাবে পরিবর্তন করা হয়েছে।",
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
        bot.answer_callback_query(call.id, "রিসোর্সটি ডিলিট করা হয়েছে!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"ত্রুটি: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "close_edit")
def close_edit_box(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

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
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(call.message.chat.id, f"✅ ক্যাটাগরি: *{cat.upper()}*\n\nএখন রিসোর্সের নাম লিখে পাঠান:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্স আনলক করতে ইউজারের কত কয়েন লাগবে? (উদাহরণ: 15):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    try:
        admin_temp_data[message.from_user.id]['coins'] = int(message.text.strip())
        cat = admin_temp_data[message.from_user.id]['type']

        if cat == 'xml':
            bot.reply_to(message, "🎬 **XML প্রিভিউ ভিডিও পাঠান (ভিডিও ফাইল অথবা ইউটিউব/সরাসরি লিংক দিন):**")
            bot.register_next_step_handler(message, get_xml_video)
        else:
            bot.reply_to(message, "🖼️ **থাম্বনেইল ইমেজ পাঠান (ছবি পাঠানোর সাথে সাথে সেটি অটো কম্প্রেস হয়ে যাবে):**")
            bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েনের পরিমাণ সংখ্যায় দিন (যেমন: 15)। আবার লিখে পাঠান:")
        bot.register_next_step_handler(message, get_coins)

def get_image(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return

    if message.photo:
        try:
            photo_file_id = message.photo[-1].file_id
            admin_temp_data[message.from_user.id]['image_file_id'] = photo_file_id
            file_info = bot.get_file(photo_file_id)
            img_bytes = bot.download_file(file_info.file_path)
            admin_temp_data[message.from_user.id]['image'] = compress_image_data(img_bytes)
        except Exception as e:
            bot.reply_to(message, f"❌ ছবি প্রসেসে ত্রুটি: {e}")
            return
    elif message.text and message.text.strip().startswith("http"):
        admin_temp_data[message.from_user.id]['image'] = compress_image_data(message.text.strip())
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ছবি পাঠান:")
        bot.register_next_step_handler(message, get_image)
        return

    cat = admin_temp_data[message.from_user.id]['type']
    if cat == 'plp':
        bot.reply_to(
            message,
            "📂 **PLP ফাইল অথবা লিংক পাঠান:**\n\n"
            "• **ছোট ফাইল হলে:** ১ বা একাধিক ফাইল পাঠান এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন。\n"
            "• **বড় ফাইল হলে:** সরাসরি ডাউনলোড লিংক পাঠান।",
            reply_markup=get_file_collection_keyboard(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(
            message,
            "📁 মূল **ফন্ট ফাইল পাঠান:**\n\n(১ বা একাধিক ফন্ট পাঠাতে পারেন। সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন)",
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
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ভিডিও ফাইল বা লিংক পাঠান:")
        bot.register_next_step_handler(message, get_xml_video)
        return

    bot.reply_to(
        message,
        "📁 প্রিভিউ ভিডিও যুক্ত হয়েছে!\n\nএখন **XML ফাইল(গুলো) পাঠান** এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন:",
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
            bot.reply_to(message, "⚠️ আপনি এখনো কোনো ফাইল পাঠাননি! ফাইল আপলোড করুন:")
            bot.register_next_step_handler(message, get_batch_files_or_link)
            return
        save_resource_to_firebase(message)
        return

    if message.document:
        admin_temp_data[user_id]['file_ids'].append(message.document.file_id)
        count = len(admin_temp_data[user_id]['file_ids'])
        bot.reply_to(
            message,
            f"📥 ফাইল ({count}) গ্রহণ করা হয়েছে!\n\nআরও ফাইল থাকলে পাঠান, অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন।"
        )
        bot.register_next_step_handler(message, get_batch_files_or_link)
    else:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ডকুমেন্ট ফাইল পাঠান অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটন চাপুন:")
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
        file_info_msg = f"📦 মোট ফাইল: {total_files}টি" if total_files > 0 else "🔗 লিংক যুক্ত হয়েছে"

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ হ্যাঁ, চ্যানেলে পোস্ট করুন", callback_data=f"ch_post:yes:{res_key}"),
            InlineKeyboardButton("❌ না, প্রয়োজন নেই", callback_data=f"ch_post:no:{res_key}")
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
        bot.reply_to(message, "❌ ফায়ারবেজে তথ্য সংরক্ষণ করা যায়নি।", reply_markup=get_admin_dashboard_keyboard())

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
            "✅ রিসোর্সটি কেবল মিনি অ্যাপে সেভ করা হয়েছে (চ্যানেলে কোনো পোস্ট করা হয়নি)।",
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
                f"🚀 ফ্রিতে সংগ্রহ করতে নিচের বাটন চাপুন এবং বটে প্রবেশ করুন:"
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

@bot.message_handler(func=lambda message: message.reply_to_message is not None and int(message.from_user.id) == int(ADMIN_ID))
def reply_to_user_from_admin(message):
    try:
        reply_header = message.reply_to_message.text or message.reply_to_message.caption
        if reply_header and "User ID:" in reply_header:
            target_id = int(reply_header.split("User ID:")[1].split()[0])
            bot.send_message(target_id, f"💬 *সাপোর্ট টিম উত্তর দিয়েছে:*\n\n{message.text}", parse_mode="Markdown")
            bot.reply_to(message, "✅ ইউজারের কাছে উত্তর পৌঁছে গেছে!")
    except Exception as e:
        bot.reply_to(message, f"❌ উত্তর পাঠানো যায়নি: {e}")

@bot.message_handler(func=lambda message: message.chat.type == 'private' and int(message.from_user.id) != int(ADMIN_ID) and not (message.text and message.text.startswith('/')))
def forward_user_message_to_admin(message):
    if is_user_banned(message.from_user.id):
        return
    user_info = f"👤 *মেসেজ প্রেরক:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *টেক্সট:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ আপনার মেসেজ সাপোর্ট টিমের কাছে পৌঁছে গেছে।")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

def setup_webhook():
    if not RENDER_EXTERNAL_URL:
        print("RENDER_EXTERNAL_URL not found. Webhook not set.")
        return

    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"

    for attempt in range(1, 6):
        try:
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
    setup_webhook()

    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    while True:
        time.sleep(10)
