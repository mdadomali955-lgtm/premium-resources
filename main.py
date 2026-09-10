import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, jsonify
from threading import Thread

BOT_TOKEN = "8815920877:AAGoSTAtxPHWvEzmwfLobQYCDGe0tcyGc9U"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://premium-resources.vercel.app"
CHANNEL_ID = "@PLPStoreBD0"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}
edit_sessions = {}

# --- UptimeRobot ও API এর জন্য ওয়েব সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!", 200

@app.route('/health')
def health():
    return "OK", 200

# --- চ্যানেল মেম্বারশিপ লাইভ ভেরিফিকেশন API ---
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

# --- ০. ক্যানসেল হ্যান্ডলার ---
@bot.message_handler(func=lambda m: m.text in ['/cancel', 'cancel', 'বাতিল'])
def cancel_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id in admin_temp_data:
        del admin_temp_data[message.from_user.id]
    if message.from_user.id in edit_sessions:
        del edit_sessions[message.from_user.id]
    bot.reply_to(message, "❌ চলমান প্রক্রিয়া বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())

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
        bot.send_message(message.chat.id, "⏳ আপনার রিসোর্সটি প্রস্তুত করা হচ্ছে...")
        
        try:
            res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
            item = res.json()
            
            if item:
                if item.get("download_link"):
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড করুন", url=item["download_link"]))
                    markup.add(InlineKeyboardButton("🚀 পুনরায় অ্যাপ খুলুন", web_app=WebAppInfo(url=WEB_APP_URL)))
                    
                    bot.send_message(
                        message.chat.id,
                        f"🎁 আপনার রিসোর্স: *{item.get('name', 'রিসোর্স')}*\n"
                        f"📁 ক্যাটাগরি: *PLP প্রজেক্ট*\n"
                        f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                        "🔗 নিচের বাটনে ট্যাপ করে সম্পূর্ণ ফাইলটি ডাউনলোড করে নিন:",
                        parse_mode="Markdown",
                        reply_markup=markup
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
            bot.send_message(message.chat.id, "❌ রিসোর্স ডেলিভারিতে সমস্যা দেখা দিয়েছে। পরে আবার চেষ্টা করুন।", reply_markup=get_main_keyboard())
            return

    if int(user_id) == int(ADMIN_ID):
        bot.send_message(
            message.chat.id,
            "👋 **অ্যাডমিন প্যানেল সক্রিয় আছে!**\n\n"
            "👑 *কমান্ডসমূহ:*\n"
            "▫️ /add - নতুন ফন্ট ফাইল বা PLP ড্রাইভ লিংক যুক্ত করুন\n"
            "▫️ /edit - আগের রিসোর্স আপডেট বা এডিট করুন\n"
            "▫️ /setad - ব্যানার বিজ্ঞাপন আপডেট করুন\n"
            "▫️ /cancel - যেকোনো চলমান কাজ বাতিল করুন\n\n"
            "👇 অ্যাপ ওপেন করতে নিচের বাটনে চাপ দিন:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"👋 হ্যালো {user_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে আপনাকে স্বাগতম। নিচের বাটনে চাপ দিয়ে অ্যাপ ওপেন করুন:",
            reply_markup=get_main_keyboard()
        )

# --- ব্যানার বিজ্ঞাপন সেট ---
@bot.message_handler(commands=['setad'])
def set_ad_start(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📢 বিজ্ঞাপনের শিরোনাম বা টেক্সট লিখে পাঠান:\n(বাতিল করতে /cancel লিখুন)")
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    admin_temp_data[message.from_user.id]['text'] = message.text.strip()
    bot.reply_to(message, "🔗 বিজ্ঞাপনের ক্লিক লিংকটি পাঠান (যেমন: https://...):")
    bot.register_next_step_handler(message, get_ad_link)

def get_ad_link(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    link = message.text.strip()
    ad_data = {
        "text": admin_temp_data[message.from_user.id]['text'],
        "link": link
    }
    requests.put(f"{FIREBASE_BASE}/active_ad.json", json=ad_data)
    bot.reply_to(message, "✅ বিজ্ঞাপন সফলভাবে মিনি অ্যাপে সেট হয়েছে!", reply_markup=get_main_keyboard())

# --- নতুন রিসোর্স আপলোড (/add) ---
@bot.message_handler(commands=['add'])
def add_resource_start(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    admin_temp_data[message.from_user.id] = {}
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎨 PLP প্রজেক্ট", callback_data="addcat:plp"),
        InlineKeyboardButton("🔤 ফন্ট ফাইল", callback_data="addcat:font")
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
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্স আনলক করতে ইউজারের কত কয়েন লাগবে? (যেমন: 10):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    try:
        admin_temp_data[message.from_user.id]['coins'] = int(message.text.strip())
        bot.reply_to(message, "🖼️ এবার থাম্বনেইল ছবি পাঠান:")
        bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েন সংখ্যায় দিন (যেমন: 10)। আবার লিখুন:")
        bot.register_next_step_handler(message, get_coins)

def get_image(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    if not message.photo:
        bot.reply_to(message, "একটি ছবি পাঠান (ফটো হিসেবে):")
        bot.register_next_step_handler(message, get_image)
        return
    
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    admin_temp_data[message.from_user.id]['image'] = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    
    cat = admin_temp_data[message.from_user.id]['type']
    if cat == 'plp':
        bot.reply_to(message, "🔗 এটি PLP প্রজেক্ট। ফাইলটির **গুগল ড্রাইভ বা ডাউনলোড লিংক** পাঠান:")
        bot.register_next_step_handler(message, get_plp_link)
    else:
        bot.reply_to(message, "📁 এটি ফন্ট। মূল **ফন্ট ফাইলটি ডকুমেন্ট আকারে** পাঠান:")
        bot.register_next_step_handler(message, get_font_file)

def get_plp_link(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    link = message.text.strip()
    if not link.startswith("http"):
        bot.reply_to(message, "❌ সঠিক URL পাঠান (যেমন: https://drive.google.com/...)")
        bot.register_next_step_handler(message, get_plp_link)
        return
    admin_temp_data[message.from_user.id]['download_link'] = link
    save_resource_to_firebase(message)

def get_font_file(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    if not message.document:
        bot.reply_to(message, "❌ ডকুমেন্ট হিসেবে ফন্ট ফাইল পাঠান:")
        bot.register_next_step_handler(message, get_font_file)
        return
    admin_temp_data[message.from_user.id]['file_id'] = message.document.file_id
    save_resource_to_firebase(message)

def save_resource_to_firebase(message):
    resource = admin_temp_data[message.from_user.id]
    res = requests.post(f"{FIREBASE_BASE}/resources.json", json=resource)
    
    if res.status_code == 200:
        bot.reply_to(
            message,
            f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n\n"
            f"📌 নাম: {resource['name']}\n"
            f"📁 ক্যাটাগরি: {resource['type'].upper()}\n"
            f"🪙 মূল্য: {resource['coins']} কয়েন\n\n"
            f"✅ মিনি অ্যাপে লাইভ করা হয়েছে!",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.reply_to(message, "❌ ফায়ারবেসে তথ্য সংরক্ষণ করা যায়নি।", reply_markup=get_main_keyboard())

# --- এডিট ও আপডেট সিস্টেম (/edit, edit বা এডিট যাই লিখুন কাজ করবে) ---
@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ['/edit', 'edit', 'এডিট', '/update', 'update', 'আপডেট'])
def edit_start(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        bot.reply_to(message, "⛔ আপনি এই কমান্ড ব্যবহারের অনুমতিপ্রাপ্ত নন।")
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    edit_sessions[message.from_user.id] = {}
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎨 PLP প্রজেক্ট", callback_data="edcat:plp"),
        InlineKeyboardButton("🔤 ফন্ট ফাইল", callback_data="edcat:font")
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
        "এবার যে ফাইলটি আপডেট করতে চান সেটির **নাম বা নামের কিছু অংশ** লিখে পাঠান:\n(বাতিল করতে /cancel)",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, find_resource_by_name)

def find_resource_by_name(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    
    search_name = (message.text or "").strip().lower()
    selected_type = edit_sessions[message.from_user.id]['type']
    
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
                "সঠিক নাম লিখে আবার পাঠান (বাতিল করতে /cancel):",
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
        bot.reply_to(message, f"❌ ফায়ারবেস ত্রুটি: {e}")

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
        InlineKeyboardButton("🪙 কয়েন পরিবর্তন", callback_data=f"do_upd:{res_key}:coins"),
        InlineKeyboardButton("🖼️ ছবি পরিবর্তন", callback_data=f"do_upd:{res_key}:image")
    )
    
    if item_data.get('type') == 'plp':
        markup.add(InlineKeyboardButton("🔗 ড্রাইভ লিংক পরিবর্তন", callback_data=f"do_upd:{res_key}:download_link"))
    else:
        markup.add(InlineKeyboardButton("📁 ফন্ট ফাইল পরিবর্তন", callback_data=f"do_upd:{res_key}:file_id"))
        
    markup.add(InlineKeyboardButton("🗑️ রিসোর্সটি ডিলিট করুন", callback_data=f"do_del:{res_key}"))
    markup.add(InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close_edit"))

    details = (
        f"🎯 **রিসোর্স পাওয়া গেছে!**\n\n"
        f"📌 **নাম:** {item_data.get('name')}\n"
        f"📁 **ক্যাটাগরি:** {item_data.get('type', '').upper()}\n"
        f"🪙 **কয়েন:** {item_data.get('coins')}\n\n"
        f"👇 **আপনি এর কোনটি আপডেট করতে চান?**"
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
        "download_link": "নতুন গুগল ড্রাইভ বা ডাউনলোড লিংকটি পাঠান:",
        "file_id": "নতুন আসল ফন্ট ফাইলটি ডকুমেন্ট আকারে পাঠান:"
    }
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(
        call.message.chat.id, 
        f"✍️ **{prompts.get(field, 'নতুন মান পাঠান:')}**\n\n(বাতিল করতে /cancel লিখুন)", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_updated_field)

def save_updated_field(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
        
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
            bot.reply_to(message, "⚠️ দয়া করে ছবি পাঠান (ফটো হিসেবে):")
            bot.register_next_step_handler(message, save_updated_field)
            return
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        new_val = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
    elif field == "download_link":
        if not message.text or not message.text.strip().startswith("http"):
            bot.reply_to(message, "⚠️ সঠিক লিংক পাঠান (যেমন: https://...):")
            bot.register_next_step_handler(message, save_updated_field)
            return
        new_val = message.text.strip()
        
    elif field == "file_id":
        if not message.document:
            bot.reply_to(message, "⚠️ আসল ফন্ট ফাইলটি ডকুমেন্ট হিসেবে পাঠান:")
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
                reply_markup=get_main_keyboard()
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
        bot.answer_callback_query(call.id, "রিসোর্সটি সফলভাবে মুছে ফেলা হয়েছে!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"ত্রুটি: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "close_edit")
def close_edit_box(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- সাপোর্ট রিপ্লাই (অ্যাডমিন থেকে ইউজার) ---
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

# --- ইউজার সাপোর্ট মেসেজ ফরোয়ার্ড ---
@bot.message_handler(func=lambda message: message.chat.type == 'private' and int(message.from_user.id) != int(ADMIN_ID) and not (message.text and message.text.startswith('/')))
def forward_user_message_to_admin(message):
    user_info = f"👤 *মেসেজ প্রেরক:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *টেক্সট:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ আপনার মেসেজটি সাপোর্ট টিমে পৌঁছেছে।")

if __name__ == "__main__":
    keep_alive()
    print("Premium Resource Delivery Bot is running with Web Server...")
    bot.infinity_polling(skip_pending=True)
