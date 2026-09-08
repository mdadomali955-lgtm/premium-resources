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
CHANNEL_ID = "@PLPStoreBD0"  # অফিসিয়াল চ্যানেল ইউজারনেম

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}

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
        # টেলিগ্রামের নিজস্ব API দিয়ে ইউজার চ্যানেলে জয়েন আছে কি না তা যাচাই
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            res = jsonify({"joined": True})
        else:
            res = jsonify({"joined": False})
    except Exception as e:
        # কোনো সমস্যা হলে বা বট অ্যাডমিন না থাকলে
        res = jsonify({"joined": False, "error": str(e)})
    
    # মিনি অ্যাপ থেকে যাতে সরাসরি রিকোয়েস্ট এক্সেপ্ট হয় (CORS Fix)
    res.headers.add("Access-Control-Allow-Origin", "*")
    return res, 200

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.daemon = True
    t.start()

# মিনি অ্যাপ খোলার বাটন তৈরির ফাংশন
def get_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 প্রিমিয়াম রিসোর্স 💎", web_app=WebAppInfo(url=WEB_APP_URL)))
    return markup

# --- ০. ক্যানসেল হ্যান্ডলার (আটকে গেলে ছাড়ানোর জন্য) ---
@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id in admin_temp_data:
        del admin_temp_data[message.from_user.id]
    bot.reply_to(message, "❌ চলমান প্রক্রিয়া বাতিল করা হয়েছে। আপনি আবার নতুন করে শুরু করতে পারেন।", reply_markup=get_main_keyboard())

# --- স্টার্ট ও ডেলিভারি হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # ডাটাবেজে ইউজার প্রোফাইল যাচাই ও তৈরি
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

    # রেফারেল রিওয়ার্ড প্রসেসিং
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if str(referrer_id) != str(user_id):
            try:
                ref_data = requests.get(f"{FIREBASE_BASE}/users/{referrer_id}.json").json()
                if ref_data:
                    requests.patch(f"{FIREBASE_BASE}/users/{referrer_id}.json", json={
                        "coins": ref_data.get('coins', 0) + 10,
                        "refers": ref_data.get('refers', 0) + 1
                    })
                    bot.send_message(referrer_id, "🎉 অভিনন্দন! নতুন মেম্বার আপনার রেফারে জয়েন করেছে। আপনি পেয়েছেন +10 🪙 কয়েন!")
            except Exception:
                pass

    # মিনি অ্যাপ থেকে ফাইল/লিংক রিকোয়েস্ট হ্যান্ডলার
    if len(args) > 1 and args[1].startswith("get_"):
        file_key = args[1].replace("get_", "").split("_from_")[0]
        bot.send_message(message.chat.id, "⏳ আপনার রিসোর্সটি প্রস্তুত করা হচ্ছে...")
        
        try:
            res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
            item = res.json()
            
            if item:
                # ১. PLP ফাইল হলে গুগল ড্রাইভ বা ডাউনলোড লিংক ডেলিভারি
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
                
                # ২. ফন্ট হলে সরাসরি ডকুমেন্ট ফাইল ডেলিভারি
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

    # সাধারণ স্বাগতম বার্তা (বাটনসহ)
    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "👋 **অ্যাডমিন প্যানেল সক্রিয় আছে!**\n\n"
            "👑 *কমান্ডসমূহ:*\n"
            "▫️ /add - নতুন ফন্ট ফাইল বা PLP ড্রাইভ লিংক যুক্ত করুন\n"
            "▫️ /setad - মিনি অ্যাপের ব্যানার বিজ্ঞাপন আপডেট করুন\n"
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

# --- ১. অ্যাডমিন ব্যানার বিজ্ঞাপন সেট ---
@bot.message_handler(commands=['setad'])
def set_ad_start(message):
    if message.from_user.id != ADMIN_ID:
        return
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

# --- ২. রিসোর্স আপলোড ---
@bot.message_handler(commands=['add'])
def add_resource_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📦 ক্যাটাগরি নির্ধারণ করুন:\nশুধুমাত্র `font` অথবা `plp` লিখুন\n(বাতিল করতে /cancel লিখুন)", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    if message.text and message.text.startswith('/'):
        return cancel_cmd(message)
    cat = (message.text or "").lower().strip()
    if cat not in ['font', 'plp']:
        bot.reply_to(message, "ভুল ইনপুট! শুধু `font` অথবা `plp` লিখুন (বাতিল করতে /cancel লিখুন):")
        bot.register_next_step_handler(message, get_category)
        return
    admin_temp_data[message.from_user.id]['type'] = cat
    bot.reply_to(message, f"✅ ক্যাটাগরি: {cat.upper()}\n\nএবার রিসোর্সের নামটি লিখুন:")
    bot.register_next_step_handler(message, get_name)

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
        bot.reply_to(message, "🔗 এটি PLP প্রজেক্ট। বড় সাইজ এড়াতে ফাইলটির **গুগল ড্রাইভ বা ডাউনলোড লিংক** পাঠান:")
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

# --- ৩. সাপোর্ট মেসেজিং সিস্টেম ---
@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.from_user.id == ADMIN_ID)
def reply_to_user_from_admin(message):
    try:
        reply_header = message.reply_to_message.text or message.reply_to_message.caption
        if reply_header and "User ID:" in reply_header:
            target_id = int(reply_header.split("User ID:")[1].split()[0])
            bot.send_message(target_id, f"💬 *সাপোর্ট টিম রিপ্লাই:*\n\n{message.text}", parse_mode="Markdown")
            bot.reply_to(message, "✅ ইউজারের কাছে উত্তর পৌঁছেছে!")
    except Exception as e:
        bot.reply_to(message, f"❌ উত্তর পাঠানো যায়নি: {e}")

@bot.message_handler(func=lambda message: message.chat.type == 'private' and message.from_user.id != ADMIN_ID)
def forward_user_message_to_admin(message):
    user_info = f"👤 *মেসেজ প্রেরক:* {message.from_user.first_name}\n🆔 User ID: `{message.from_user.id}`\n\n📝 *টেক্সট:* {message.text}"
    bot.send_message(ADMIN_ID, user_info, parse_mode="Markdown")
    bot.reply_to(message, "✅ আপনার মেসেজটি সাপোর্ট টিমে পৌঁছেছে।")

if __name__ == "__main__":
    keep_alive()
    print("Premium Resource Delivery Bot is running with Web Server...")
    bot.infinity_polling(skip_pending=True)
