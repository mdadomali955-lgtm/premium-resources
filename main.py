import telebot
import requests

BOT_TOKEN = "8815920877:AAGoSTAtxPHWvEzmwfLobQYCDGe0tcyGc9U"
ADMIN_ID = 7481264433
FIREBASE_BASE = "https://premium-resources-default-rtdb.firebaseio.com"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}

# --- স্টার্ট কমান্ড & সরাসরি ফাইল সেন্ডিং ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    args = message.text.split()
    
    # মিনি অ্যাপ থেকে ইউজারের রিকোয়েস্ট আসলে
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
                    caption=f"🎁 রিসোর্স: *{item['name']}*\n🪙 কয়েন: {item['coins']}\n\nধন্যবাদ!",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(message.chat.id, "❌ ফাইলটি ডাটাবেজে খুঁজে পাওয়া যায়নি।")
        except Exception:
            bot.send_message(message.chat.id, "❌ সমস্যা হয়েছে, পরে চেষ্টা করুন।")
        return

    # সাধারণ ওয়েলকাম মেসেজ
    bot.reply_to(
        message, 
        "👋 স্বাগতম! রিসোর্স বট সক্রিয় আছে।\n\n"
        "👑 অ্যাডমিন কমান্ড:\n"
        "▫️ /add - নতুন ফাইল রিসোর্স যোগ করুন\n"
        "▫️ /setad - মিনি অ্যাপে অ্যাড/প্রমোশন ব্যানার সেট করুন"
    )

# --- ১. অ্যাড/বিজ্ঞাপন সেট করার সেকশন ---
@bot.message_handler(commands=['setad'])
def set_ad_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন।")
        return
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📢 বিজ্ঞাপনের লেখা/বিবরণ লিখে পাঠান:")
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    admin_temp_data[message.from_user.id]['text'] = message.text.strip()
    bot.reply_to(message, "🔗 এবার বিজ্ঞাপনের ক্লিক লিংক পাঠান (যেমন: চ্যানেল বা অফার লিংক):")
    bot.register_next_step_handler(message, get_ad_link)

def get_ad_link(message):
    ad_data = {
        "text": admin_temp_data[message.from_user.id]['text'],
        "link": message.text.strip()
    }
    requests.put(f"{FIREBASE_BASE}/active_ad.json", json=ad_data)
    bot.reply_to(message, "✅ সফলভাবে বিজ্ঞাপন সেট হয়েছে! মিনি অ্যাপে এটি প্রদর্শিত হচ্ছে।")

# --- ২. নতুন রিসোর্স যোগ করার সেকশন ---
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
        bot.reply_to(message, "🖼️ এবার থাম্বনেইলের ছবি পাঠান:")
        bot.register_next_step_handler(message, get_image)
    except ValueError:
        bot.reply_to(message, "কয়েন অবশ্যই সংখ্যায় হতে হবে। আবার লিখুন:")
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
        bot.reply_to(message, "❌ আপনি কোনো ফাইল পাঠাননি! ডকুমেন্ট হিসেবে ফাইলটি পাঠান:")
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
