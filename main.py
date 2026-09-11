import os
import requests
import telebot
import time
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from flask import Flask, jsonify
from threading import Thread

BOT_TOKEN = "8815920877:AAGoSTAtxPHWvEzmwfLobQYCDGe0tcyGc9U"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}
edit_sessions = {}

# --- UptimeRobot ও API সার্ভার ---
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

def get_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 প্রিমিয়াম রিসোর্স 💎", web_app=WebAppInfo(url=WEB_APP_URL)))
    return markup

def get_admin_dashboard_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("➕ নতুন রিসোর্স যুক্ত করুন"),
        KeyboardButton("✏️ রিসোর্স এডিট/আপডেট"),
        KeyboardButton("📢 বিজ্ঞাপন সেট করুন"),
        KeyboardButton("❌ বাতিল করুন")
    )
    return markup

# --- চ্যানেল ও গ্রুপ অটো-ট্র্যাকিং হ্যান্ডলার ---
@bot.my_chat_member_handler()
def track_bot_channels_and_groups(update):
    try:
        chat = update.chat
        new_status = update.new_chat_member.status
        
        if new_status in ['administrator', 'creator', 'member']:
            chat_info = {
                "id": str(chat.id),
                "title": chat.title or "Untitled",
                "type": chat.type
            }
            clean_id = str(chat.id).replace("-", "m_")
            requests.put(f"{FIREBASE_BASE}/connected_chats/{clean_id}.json", json=chat_info)
            print(f"✅ কানেক্ট হয়েছে: {chat.title} ({chat.id})")
            
        elif new_status in ['left', 'kicked']:
            clean_id = str(chat.id).replace("-", "m_")
            requests.delete(f"{FIREBASE_BASE}/connected_chats/{clean_id}.json")
            print(f"❌ রিমুভ হয়েছে: {chat.id}")
    except Exception as e:
        print(f"Chat tracking error: {e}")

# --- ম্যানুয়াল চ্যানেল অ্যাড করার কমান্ড ---
@bot.message_handler(commands=['addchannel'])
def manual_add_channel(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ চ্যানেলের ইউজারনেম দিন।\nউদাহরণ: `/addchannel @PLPStoreBD0`", parse_mode="Markdown")
        return
    
    target_channel = args[1].strip()
    try:
        chat = bot.get_chat(target_channel)
        clean_id = str(chat.id).replace("-", "m_")
        requests.put(f"{FIREBASE_BASE}/connected_chats/{clean_id}.json", json={
            "id": str(chat.id),
            "title": chat.title or target_channel,
            "type": chat.type
        })
        bot.reply_to(message, f"🎉 ব্রডকাস্ট তালিকায় যুক্ত হয়েছে: *{chat.title}* (`{chat.id}`)", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ চ্যানেল পাওয়া যায়নি! বট চ্যানেলে অ্যাডমিন কিনা নিশ্চিত করুন।\nত্রুটি: `{e}`", parse_mode="Markdown")

# --- চ্যানেলে টেস্ট পোস্ট পাঠানোর কমান্ড ---
@bot.message_handler(commands=['testpost'])
def test_channel_post(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 অ্যাপে দেখুন 💎", url=f"https://t.me/{BOT_USERNAME}?start=open"))
    
    try:
        bot.send_message(
            chat_id=CHANNEL_ID,
            text="🔔 **এটি একটি সফল টেস্ট ব্রডকাস্ট মেসেজ!**\n\nবট এখন চ্যানেলটিতে সফলভাবে পোস্ট পাঠাতে পারছে।",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.reply_to(message, f"✅ সফল! {CHANNEL_ID} চ্যানেলে টেস্ট পোস্ট চলে গেছে।")
    except Exception as e:
        bot.reply_to(message, f"❌ চ্যানেলে পোস্ট যায়নি!\n\nকারণ: `{e}`\n\n💡 সমাধান: চ্যানেলের Administrators অপশনে গিয়ে বটকে **Post Messages** পারমিশন দিন।")

# --- নতুন রিসোর্স ব্রডকাস্ট ফাংশন (ডাবল পোস্ট সমস্যা সমাধানকৃত) ---
def broadcast_new_resource(resource):
    try:
        users_data = requests.get(f"{FIREBASE_BASE}/users.json").json() or {}
        saved_chats = requests.get(f"{FIREBASE_BASE}/connected_chats.json").json() or {}
        
        # ইউনিক চ্যাট আইডি সেট তৈরি (ডুপ্লিকেট রিমুভ করতে)
        target_channels = set()
        
        # ১. ডিফল্ট চ্যানেল আইডি বের করা
        try:
            default_chat = bot.get_chat(CHANNEL_ID)
            target_channels.add(default_chat.id)
        except Exception:
            target_channels.add(CHANNEL_ID)

        # ২. ডাটাবেজ থেকে ইউনিক চ্যানেল আইডি ফিল্টার
        for k, v in saved_chats.items():
            if isinstance(v, dict) and 'id' in v:
                try:
                    target_channels.add(int(v['id']))
                except ValueError:
                    target_channels.add(v['id'])
            elif isinstance(v, str):
                try:
                    target_channels.add(int(v))
                except ValueError:
                    target_channels.add(v)
            else:
                clean_k = k.replace("m_", "-")
                try:
                    target_channels.add(int(clean_k))
                except ValueError:
                    target_channels.add(clean_k)

        r_type = resource.get('type')
        if r_type == 'plp':
            cat_name = "PLP প্রজেক্ট"
            target_tab = "plp"
        elif r_type == 'xml':
            cat_name = "XML প্রজেক্ট"
            target_tab = "xml"
        else:
            cat_name = "ফন্ট ফাইল"
            target_tab = "font"
        
        separator = "&" if "?" in WEB_APP_URL else "?"
        app_url_with_tab = f"{WEB_APP_URL}{separator}tab={target_tab}"
        
        caption_text = (
            f"🔥 **নতুন প্রিমিয়াম রিসোর্স যুক্ত হয়েছে!**\n\n"
            f"📌 **নাম:** {resource.get('name')}\n"
            f"📁 **ক্যাটাগরি:** {cat_name}\n"
            f"🪙 **মূল্য:** {resource.get('coins')} কয়েন\n\n"
            f"✨ এখনই প্রিমিয়াম রিসোর্স অ্যাপ থেকে কয়েন দিয়ে আনলক করে নিতে পারেন!"
        )
        
        # চ্যানেলের জন্য ইউআরএল বাটন
        channel_markup = InlineKeyboardMarkup()
        btn_text = f"🛒 {cat_name} সংগ্রহ করুন"
        channel_markup.add(InlineKeyboardButton(btn_text, url=f"https://t.me/{BOT_USERNAME}?start=open_{target_tab}"))

        # ইনবক্স ইউজারদের জন্য সরাসরি WebApp বাটন
        inbox_markup = InlineKeyboardMarkup()
        inbox_markup.add(InlineKeyboardButton(btn_text, web_app=WebAppInfo(url=app_url_with_tab)))

        raw_vid = resource.get('raw_video_id')
        raw_photo = resource.get('raw_photo_id') or resource.get('image')

        # --- চ্যানেলে একবারই পাঠানো ---
        for target in target_channels:
            try:
                if raw_vid:
                    bot.send_video(
                        chat_id=target,
                        video=raw_vid,
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=channel_markup
                    )
                else:
                    bot.send_photo(
                        chat_id=target,
                        photo=raw_photo,
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=channel_markup
                    )
                time.sleep(0.1)
            except Exception as ex:
                print(f"Channel broadcast failed for {target}: {ex}")

        # --- ইউজারদের ইনবক্সে পোস্ট সেন্ড ---
        for uid in users_data.keys():
            try:
                if raw_vid:
                    bot.send_video(
                        chat_id=int(uid),
                        video=raw_vid,
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=inbox_markup
                    )
                else:
                    bot.send_photo(
                        chat_id=int(uid),
                        photo=raw_photo,
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=inbox_markup
                    )
                time.sleep(0.05)
            except Exception:
                continue
    except Exception as e:
        print(f"Broadcast main error: {e}")

# --- ক্যানসেল হ্যান্ডলার ---
def cancel_process(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id in admin_temp_data:
        del admin_temp_data[message.from_user.id]
    if message.from_user.id in edit_sessions:
        del edit_sessions[message.from_user.id]
    
    if int(message.from_user.id) == int(ADMIN_ID):
        bot.send_message(message.chat.id, "❌ চলমান প্রক্রিয়া বাতিল করা হয়েছে।", reply_markup=get_admin_dashboard_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())

# --- ডাইরেক্ট ক্যাটাগরি কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['add_xml', 'xml', 'add_plp', 'plp', 'add_font', 'font'])
def handle_direct_add_commands(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    
    cmd = message.text.split()[0].replace('/', '').lower()
    cat_type = 'xml' if 'xml' in cmd else ('plp' if 'plp' in cmd else 'font')
    
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {'type': cat_type}
    
    cat_title = "⚡ XML প্রজেক্ট" if cat_type == 'xml' else ("🎨 PLP প্রজেক্ট" if cat_type == 'plp' else "🔤 ফন্ট ফাইল")
    msg = bot.send_message(
        message.chat.id, 
        f"✅ কমান্ড গ্রহণ করা হয়েছে: *{cat_title}*\n\nএবার রিসোর্সের নাম লিখে পাঠান:\n(বাতিল করতে /cancel চাপুন)", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_name)

# --- স্টার্ট ও ডেলিভারি হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
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

    if len(args) > 1 and args[1].startswith("get_"):
        file_key = args[1].replace("get_", "").split("_from_")[0]
        bot.send_message(message.chat.id, "⏳ আপনার ফাইলটি প্রস্তুত করা হচ্ছে...")
        
        try:
            res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
            item = res.json()
            
            if item:
                res_type = item.get("type", "plp")

                if res_type == 'plp' and item.get("download_link"):
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড করুন", url=item["download_link"]))
                    markup.add(InlineKeyboardButton("🚀 পুনরায় অ্যাপ খুলুন", web_app=WebAppInfo(url=WEB_APP_URL)))
                    bot.send_message(
                        message.chat.id,
                        f"🎁 আপনার রিসোর্স: *{item.get('name', 'রিসোর্স')}*\n"
                        f"📁 ক্যাটাগরি: *PLP প্রজেক্ট*\n"
                        f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                        "🔗 নিচের বাটনে চাপ দিয়ে ড্রাইভ ফাইল ডাউনলোড করুন:",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                    return

                elif res_type == 'xml' and item.get("file_id"):
                    caption_text = (
                        f"⚡ **আপনার XML ফাইল প্রস্তুত!**\n\n"
                        f"📌 নাম: *{item.get('name', 'XML প্রজেক্ট')}*\n"
                        f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                        "📂 **সেভ করার নিয়ম:**\n"
                        "১. ফাইলে ট্যাপ করে ডাউনলোড সম্পন্ন করুন।\n"
                        "২. ডানপাশের ৩-ডটে (⋮) চাপ দিয়ে **'Save to Downloads'** করুন।"
                    )
                    bot.send_document(
                        message.chat.id,
                        item["file_id"],
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                    return

                elif item.get("file_id"):
                    caption_text = (
                        f"🎁 আপনার ফন্ট: *{item.get('name', 'ফন্ট')}*\n"
                        f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                        "📂 **ফোনে সেভ করার নিয়ম:**\n"
                        "১. ফাইলটিতে চাপ দিয়ে ডাউনলোড শেষ করুন।\n"
                        "২. ডানপাশের ৩-ডট (⋮) চেপে **'Save to Downloads'** সিলেক্ট করুন।"
                    )
                    bot.send_document(
                        message.chat.id,
                        item["file_id"],
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                    return
            else:
                bot.send_message(message.chat.id, "❌ ফাইলটি ডাটাবেজে খুঁজে পাওয়া যায়নি।", reply_markup=get_main_keyboard())
                return
        except Exception:
            bot.send_message(message.chat.id, "❌ রিসোর্স ডেলিভারিতে সমস্যা দেখা দিয়েছে।", reply_markup=get_main_keyboard())
            return

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👑 **স্বাগতম অ্যাডমিন প্যানেলে!**\n\n"
            "💡 **সহজ কমান্ডসমূহ:**\n"
            "• `/testpost` - চ্যানেলে পোস্ট যাচ্ছে কিনা টেস্ট করতে\n"
            "• `/addchannel @username` - নতুন চ্যানেল ব্রডকাস্টে যুক্ত করতে\n"
            "• `/xml` বা `/add_xml` - সরাসরি XML যোগ করতে\n"
            "• `/plp` বা `/add_plp` - সরাসরি PLP যোগ করতে\n"
            "• `/font` বা `/add_font` - সরাসরি Font যোগ করতে\n\n"
            "অথবা নিচের বাটন দিয়ে পরিচালনা করুন:",
            parse_mode="Markdown",
            reply_markup=get_admin_dashboard_keyboard()
        )
        bot.send_message(message.chat.id, "মিনি অ্যাপে যেতে নিচের বাটনে চাপুন:", reply_markup=get_main_keyboard())
    else:
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
            InlineKeyboardButton("⚡ মূল XML ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:file_id")
        )
    elif r_type == 'plp':
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ছবি", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("🔗 ড্রাইভ লিংক পরিবর্তন", callback_data=f"do_upd:{res_key}:download_link")
        )
    else:
        markup.add(
            InlineKeyboardButton("🖼️ থাম্বনেইল ছবি", callback_data=f"do_upd:{res_key}:image"),
            InlineKeyboardButton("📁 ফন্ট ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:file_id")
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
    edit_sessions[call.from_user.id] = {'key': res_key, 'field': field}
    
    prompts = {
        "name": "নতুন নামটি লিখে পাঠান:",
        "coins": "নতুন কয়েন সংখ্যাটি লিখে পাঠান (যেমন: 15):",
        "image": "নতুন থাম্বনেইল ছবিটি ফটো হিসেবে পাঠান:",
        "video": "নতুন প্রিভিউ ভিডিও ফাইলটি পাঠান (ভিডিও হিসেবে):",
        "download_link": "নতুন গুগল ড্রাইভ বা ডাউনলোড লিংকটি পাঠান:",
        "file_id": "নতুন ফাইলটি ডকুমেন্ট (Document) আকারে পাঠান:"
    }
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(
        call.message.chat.id, 
        f"✍️ **{prompts.get(field, 'নতুন মান পাঠান:')}**", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_updated_field)

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
        if not message.photo:
            bot.reply_to(message, "⚠️ দয়া করে ফটো হিসেবে ছবি পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        new_val = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
    elif field == "video":
        if not message.video:
            bot.reply_to(message, "⚠️ দয়া করে ভিডিও হিসেবে প্রিভিউ ক্লিপ পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return
        vid_id = message.video.file_id
        file_info = bot.get_file(vid_id)
        new_val = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    elif field == "download_link":
        if not message.text or not message.text.strip().startswith("http"):
            bot.reply_to(message, "⚠️ সঠিক লিংক পাঠান (যেমন: https://...):")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.text.strip()
        
    elif field == "file_id":
        if not message.document:
            bot.reply_to(message, "⚠️ মূল ফাইলটি ডকুমেন্ট (Document) হিসেবে পাঠান:")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.document.file_id

    if new_val is not None:
        try:
            requests.patch(f"{FIREBASE_BASE}/resources/{res_key}.json", json={field: new_val})
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

# --- রিসোর্স যুক্ত করার ফ্লো (বাটন ক্লিক) ---
def start_add_flow(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {}
    
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
    admin_temp_data[call.from_user.id] = {'type': cat}
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
            bot.reply_to(message, "🎬 **XML থাম্বনেইল ভিডিও পাঠান:**\n(বটের চ্যাটে ভিডিওটি আপলোড করুন)")
            bot.register_next_step_handler(message, get_xml_video)
        else:
            bot.reply_to(message, "🖼️ **থাম্বনেইল ছবি পাঠান:**\n(বটের চ্যাটে ফটো আকারে পাঠান)")
            bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েন সংখ্যায় দিন (যেমন: 15)। আবার লিখুন:")
        bot.register_next_step_handler(message, get_coins)

# ছবি প্রসেসিং (PLP / Font)
def get_image(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    if not message.photo:
        bot.reply_to(message, "একটি ফটো পাঠান:")
        bot.register_next_step_handler(message, get_image)
        return
    
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    admin_temp_data[message.from_user.id]['raw_photo_id'] = file_id
    admin_temp_data[message.from_user.id]['image'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    
    cat = admin_temp_data[message.from_user.id]['type']
    if cat == 'plp':
        bot.reply_to(message, "🔗 এটি PLP প্রজেক্ট। ফাইলটির **গুগল ড্রাইভ বা ডাউনলোড লিংক** পাঠান:")
        bot.register_next_step_handler(message, get_plp_link)
    else:
        bot.reply_to(message, "📁 এটি ফন্ট। মূল **ফন্ট ফাইলটি ডকুমেন্ট (Document) আকারে** পাঠান:")
        bot.register_next_step_handler(message, get_document_file)

# ভিডিও থাম্বনেইল প্রসেসিং (XML)
def get_xml_video(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    if not message.video:
        bot.reply_to(message, "❌ দয়া করে একটি ভিডিও ফাইল পাঠান:")
        bot.register_next_step_handler(message, get_xml_video)
        return

    vid_id = message.video.file_id
    file_info = bot.get_file(vid_id)
    admin_temp_data[message.from_user.id]['raw_video_id'] = vid_id
    admin_temp_data[message.from_user.id]['video'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    
    bot.reply_to(message, "📁 প্রিভিউ ভিডিও যুক্ত হয়েছে!\n\nএবার **মূল XML ফাইলটি ডকুমেন্ট (Document) আকারে** পাঠান:")
    bot.register_next_step_handler(message, get_document_file)

def get_plp_link(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    link = message.text.strip()
    if not link.startswith("http"):
        bot.reply_to(message, "❌ সঠিক URL পাঠান (যেমন: https://drive.google.com/...)")
        bot.register_next_step_handler(message, get_plp_link)
        return
    admin_temp_data[message.from_user.id]['download_link'] = link
    save_resource_to_firebase(message)

def get_document_file(message):
    if message.text and (message.text.startswith('/') or message.text == "❌ বাতিল করুন"):
        cancel_process(message)
        return
    if not message.document:
        bot.reply_to(message, "❌ আসল ফাইলটি ডকুমেন্ট (Document) হিসেবে পাঠান:")
        bot.register_next_step_handler(message, get_document_file)
        return
    admin_temp_data[message.from_user.id]['file_id'] = message.document.file_id
    save_resource_to_firebase(message)

def save_resource_to_firebase(message):
    resource = admin_temp_data[message.from_user.id]
    
    firebase_payload = {k: v for k, v in resource.items() if k not in ['raw_photo_id', 'raw_video_id']}
    res = requests.post(f"{FIREBASE_BASE}/resources.json", json=firebase_payload)
    
    if res.status_code == 200:
        bot.reply_to(
            message,
            f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n\n"
            f"📌 নাম: {resource['name']}\n"
            f"📁 ক্যাটাগরি: {resource['type'].upper()}\n"
            f"🪙 মূল্য: {resource['coins']} কয়েন\n\n"
            f"✅ ওয়েব অ্যাপে যুক্ত হয়েছে এবং চ্যানেলে ও ইউজারদের কাছে ব্রডকাস্ট পাঠানো শুরু হয়েছে!",
            reply_markup=get_admin_dashboard_keyboard()
        )
        Thread(target=broadcast_new_resource, args=(resource,), daemon=True).start()
    else:
        bot.reply_to(message, "❌ ফায়ারবেসে তথ্য সংরক্ষণ করা যায়নি।", reply_markup=get_admin_dashboard_keyboard())

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
    user_info = f"👤 *মেসেজ প্রেরক:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *টেক্সট:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ আপনার মেসেজটি সাপোর্ট টিমে পৌঁছেছে।")

if __name__ == "__main__":
    keep_alive()
    print("Premium Resource Delivery Bot is running with Web Server...")
    bot.infinity_polling(
        skip_pending=True, 
        allowed_updates=['message', 'callback_query', 'my_chat_member', 'chat_member']
    )
