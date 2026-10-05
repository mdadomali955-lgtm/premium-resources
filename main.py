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
    ReplyKeyboardRemove
)

# --- Bot Configuration ---
BOT_TOKEN = "8815920877:AAFGwxjKGoo9HhcsVOcbBhi9JMqXT-LLMsY"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"
SUPPORT_URL = "https://t.me/PLPSTOREAI"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}
broadcast_sessions = {}
ban_sessions = {}
promo_sessions = {}
user_inspect_sessions = {}
user_earn_sessions = {}

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

# --- Admin Dashboard Inline Keyboard ---
def get_admin_dashboard_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ নতুন রিসোর্স যুক্ত করুন", callback_data="adm_add"),
        InlineKeyboardButton("✏️ রিসোর্স এডিট/আপডেট", callback_data="adm_edit"),
        InlineKeyboardButton("🪙 কয়েন আপডেট/ম্যানেজ", callback_data="adm_coin"),
        InlineKeyboardButton("📊 ডাউনলোড হিস্ট্রি", callback_data="adm_logs"),
        InlineKeyboardButton("📢 ব্রডকাস্ট মেসেজ", callback_data="adm_broadcast"),
        InlineKeyboardButton("🚫 ইউজার ব্যান/আনব্যান", callback_data="adm_ban"),
        InlineKeyboardButton("🎁 প্রোমো কোড তৈরি", callback_data="adm_promo"),
        InlineKeyboardButton("🔍 ইউজার চেক", callback_data="adm_inspect")
    )
    return markup

# --- User Custom Useful Keyboard ---
def get_user_dashboard_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🚀 Premium Resource Mini App 💎", web_app=WebAppInfo(url=WEB_APP_URL)),
        InlineKeyboardButton("📂 ফাইল দিয়ে কয়েন আয় করুন (Earn)", callback_data="earn_coins_start"),
        InlineKeyboardButton("📥 কিভাবে ফাইল ডাউনলোড করবেন?", callback_data="help_download"),
        InlineKeyboardButton("📖 ফন্ট ও পিএলপি ব্যবহারের গাইড", callback_data="help_usage"),
        InlineKeyboardButton("🪙 ফ্রি কয়েন পাওয়ার উপায়", callback_data="help_coins"),
        InlineKeyboardButton("💬 সাপোর্ট ও হেল্পলাইন", url=SUPPORT_URL)
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
            bot.reply_to(message, "⚠️ আপনি কোনো ফাইল আপলোড করেননি!", reply_markup=get_user_dashboard_keyboard())
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
            reply_markup=get_user_dashboard_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ সমস্যা হয়েছে: {e}", reply_markup=get_user_dashboard_keyboard())

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
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◀️ মূল মেনুতে ফিরুন", callback_data="help_back"))

    if data == "help_download":
        text = "📥 **কিভাবে ফাইল ডাউনলোড করবেন?**\n\nমিনি অ্যাপে প্রবেশ করে পছন্দের ফাইলের 'ডাউনলোড' বাটনে চাপ দিন এবং ৫ সেকেন্ড অপেক্ষা করে ইনবক্সে ফাইল নিন!"
    elif data == "help_usage":
        text = "📖 **ফন্ট ও পিএলপি ব্যবহারের গাইড**\n\nPLP ফাইল PixelLab ফোল্ডারে এবং ফন্টসমূহ ফন্ট ফোল্ডারে রেখে ব্যবহার করতে হবে।"
    elif data == "help_coins":
        text = "🪙 **ফ্রি কয়েন পাওয়ার উপায়**\n\nডেইলি চেক-ইন, স্পিন, স্ক্র্যাচ কার্ড এবং ফাইল আপলোড করে ফ্রি কয়েন আর্ন করুন।"
    elif data == "help_back":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "👋 মূল মেনুতে স্বাগতম:", reply_markup=get_user_dashboard_keyboard())
        return
    else:
        return

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# --- Admin Inline Actions Handler ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def handle_admin_inline_actions(call):
    if int(call.from_user.id) != int(ADMIN_ID):
        return
    
    action = call.data
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    if action == "adm_add":
        start_add_flow(call.message)
    elif action == "adm_edit":
        start_edit_flow(call.message)
    elif action == "adm_coin":
        start_coin_management_flow(call.message)
    elif action == "adm_logs":
        show_download_logs_cmd(call.message)
    elif action == "adm_broadcast":
        start_broadcast_flow(call.message)
    elif action == "adm_ban":
        start_ban_flow(call.message)
    elif action == "adm_promo":
        start_promo_flow(call.message)
    elif action == "adm_inspect":
        start_user_inspect_flow(call.message)

    bot.answer_callback_query(call.id)

# --- Universal Text Fallback for Old Keyboards ---
@bot.message_handler(func=lambda message: int(message.from_user.id) == int(ADMIN_ID) and message.text)
def handle_accidental_reply_clicks(message):
    text = message.text.strip()
    if 'নতুন রিসোর্স' in text:
        start_add_flow(message)
    elif 'রিসোর্স এডিট' in text:
        start_edit_flow(message)
    elif 'কয়েন আপডেট' in text:
        start_coin_management_flow(message)
    elif 'ডাউনলোড হিস্ট্রি' in text:
        show_download_logs_cmd(message)
    elif 'ব্রডকাস্ট' in text:
        start_broadcast_flow(message)
    elif 'ইউজার ব্যান' in text:
        start_ban_flow(message)
    elif 'প্রোমো কোড' in text:
        start_promo_flow(message)
    elif 'ইউজার চেক' in text:
        start_user_inspect_flow(message)

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
        bot.reply_to(message, "⚠️ অনুগ্রহ করে ছবি অথবা সঠিক সরাসরি লিংক পাঠান:")
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
    if user_id not in admin
