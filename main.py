import telebot
import requests

BOT_TOKEN = "8815920877:AAGoSTAtxPHWvEzmwfLobQYCDGe0tcyGc9U"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # ইউজার রেকর্ড আপডেট
    try:
        u_res = requests.get(f"{FIREBASE_BASE}/users/{user_id}.json").json()
        if not u_res:
            requests.put(f"{FIREBASE_BASE}/users/{user_id}.json", json={
                "name": user_name,
                "username": message.from_user.username or "",
                "coins": 20,
                "refers": 0
            })
    except Exception:
        pass

    # ১. রেফারেল লিঙ্ক দিয়ে জয়েন করলে
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "")
        if str(referrer_id) != str(user_id):
            try:
                ref_data = requests.get(f"{FIREBASE_BASE}/users/{referrer_id}.json").json()
                if ref_data:
                    new_coins = ref_data.get('coins', 0) + 10
                    new_refers = ref_data.get('refers', 0) + 1
                    requests.patch(f"{FIREBASE_BASE}/users/{referrer_id}.json", json={"coins": new_coins, "refers": new_refers})
                    bot.send_message(referrer_id, f"🎉 অভিনন্দন! একজন নতুন মেম্বার আপনার রেফারে জয়েন করেছে। আপনি পেয়েছেন +10 🪙 কয়েন!")
            except Exception:
                pass

    # ২. মিনি অ্যাপ থেকে ফাইল চাওয়ার লিঙ্ক
    if len(args) > 1 and args[1].startswith("get_"):
        file_key = args[1].replace("get_", "")
        bot.send_message(message.chat.id, "⏳ আপনার ফাইলটি পাঠানো হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
        try:
            res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
            item = res.json()
            if item and 'file_id' in item:
                bot.send_document(
                    message.chat.id, 
                    item['file_id'], 
                    caption=f"🎁 আপনার রিসোর্স: *{item['name']}*\n🪙 কয়েন: {item['coins']}\n\nসফলভাবে ডাউনলোড সম্পন্ন হয়েছে!",
                    parse_mode="Markdown"
                )
                return
            else:
                bot.send_message(message.chat.id, "❌ দুঃখিত, ফাইলটি ডাটাবেজে পাওয়া যায়নি।")
                return
        except Exception:
            bot.send_message(message.chat.id, "❌ কোনো সমস্যা হয়েছে, পরে আবার চেষ্টা করুন।")
            return

    # সাধারণ ওয়েলকাম
    bot.reply_to(
        message, 
        f"👋 হ্যালো {user_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে আপনাকে স্বাগতম। নিচে থাকা বোতামে চাপ দিয়ে মিনি অ্যাপটি ওপেন করুন।\n\n"
        "👑 অ্যাডমিন কমান্ড:\n"
        "▫️ /add - নতুন ফাইল যোগ করুন\n"
        "▫️ /setad - মিনি অ্যাপে বিজ্ঞাপন দিন"
    )

# --- বিজ্ঞাপন সেট ---
@bot.message_handler(commands=['setad'])
def set_ad_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন।")
        return
    bot.reply_to(message, "📢 বিজ্ঞাপনের টেক্সট বা বিবরণ লিখে পাঠান:")
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    admin_temp_data[message.from_user.id] = {'text': message.text.strip()}
    bot.reply_to(message, "🔗 এবার বিজ্ঞাপনের ক্লিক লিংক পাঠান:")
    bot.register_next_step_handler(message, get_ad_link)

def get_ad_link(message):
    ad_data = {
        "text": admin_temp_data[message.from_user.id]['text'],
        "link": message.text.strip()
    }
    requests.put(f"{FIREBASE_BASE}/active_ad.json", json=ad_data)
    bot.reply_to(message, "✅ সফলভাবে বিজ্ঞাপন সেট হয়েছে! মিনি অ্যাপে এটি প্রদর্শিত হচ্ছে।")

# --- রিসোর্স অ্যাড ---
@bot.message_handler(commands=['add'])
def add_resource_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন।")
        return
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📦 নতুন রিসোর্স যোগ করা হচ্ছে!\n\nক্যাটাগরি লিখুন: `font` অথবা `plp`", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    cat = message.text.lower().strip()
    if cat not in ['font', 'plp']:
        bot.reply_to(message, "ভুল ইনপুট! শুধু `font` অথবা `plp` লিখুন।")
        return
    admin_temp_data[message.from_user.id]['type'] = cat
    bot.reply_to(message, f"✅ ক্যাটাগরি: {cat.upper()}\n\nএবার রিসোর্সের নাম লিখুন:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্সের জন্য কত কয়েন লাগবে? (যেমন: 10):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    try:
        coins = int(message.text.strip())
        admin_temp_data[message.from_user.id]['coins'] = coins
        bot.reply_to(message, "🖼️ এবার থাম্বনেইল ছবি পাঠান:")
        bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েন সংখ্যায় দিন। আবার লিখুন:")
        bot.register_next_step_handler(message, get_coins)

def get_image(message):
    if not message.photo:
        bot.reply_to(message, "অনুগ্রহ করে একটি ছবি পাঠান।")
        return
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    img_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    admin_temp_data[message.from_user.id]['image'] = img_url
    bot.reply_to(message, "📁 এবার মূল ফাইলটি (ZIP / TTF / PLP ডকুমেন্ট হিসেবে) পাঠান:")
    bot.register_next_step_handler(message, get_file_document)

def get_file_document(message):
    if not message.document:
        bot.reply_to(message, "❌ আপনি ফাইল পাঠাননি! ডকুমেন্ট হিসেবে ফাইলটি পাঠান:")
        bot.register_next_step_handler(message, get_file_document)
        return
    admin_temp_data[message.from_user.id]['file_id'] = message.document.file_id
    resource = admin_temp_data[message.from_user.id]

    res = requests.post(f"{FIREBASE_BASE}/resources.json", json=resource)
    if res.status_code == 200:
        bot.reply_to(message, f"🎉 সফলভাবে যুক্ত হয়েছে!\n\n📌 নাম: {resource['name']}\n📁 ক্যাটাগরি: {resource['type'].upper()}\n🪙 কয়েন: {resource['coins']}\n\n✅ মিনি অ্যাপে লাইভ করা হয়েছে!")
    else:
        bot.reply_to(message, "❌ ফায়ারবেসে তথ্য সংরক্ষণ করা যায়নি।")

print("Admin Bot is running...")
bot.infinity_polling()
