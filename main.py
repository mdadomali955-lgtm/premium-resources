import telebot
import requests

BOT_TOKEN = "8815920877:AAGoSTAtxPHWvEzmwfLobQYCDGe0tcyGc9U"
ADMIN_ID = 7481264433
FIREBASE_URL = "https://premium-resources-default-rtdb.firebaseio.com/resources.json"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    args = message.text.split()
    
    # ইউজার যদি মিনি অ্যাপ থেকে ফাইলের জন্য আসে (Deep Link)
    if len(args) > 1 and args[1].startswith("get_"):
        file_key = args[1].replace("get_", "")
        bot.send_message(message.chat.id, "⏳ ফাইলটি পাঠানো হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
        
        try:
            res = requests.get(f"https://premium-resources-default-rtdb.firebaseio.com/resources/{file_key}.json")
            item = res.json()
            if item and 'file_id' in item:
                bot.send_document(
                    message.chat.id, 
                    item['file_id'], 
                    caption=f"🎁 আপনার কাঙ্ক্ষিত রিসোর্স: *{item['name']}*\n\nধন্যবাদ আমাদের সাথে থাকার জন্য!",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(message.chat.id, "❌ দুঃখিত, ফাইলটি খুঁজে পাওয়া যায়নি।")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ কোনো সমস্যা হয়েছে, পরে আবার চেষ্টা করুন।")
        return

    # সাধারণ স্টার্ট মেসেজ
    bot.reply_to(message, "👋 স্বাগতম! রিসোর্স বট সক্রিয় আছে।\n\nঅ্যাডমিন হলে রিসোর্স যোগ করতে /add লিখুন।")

@bot.message_handler(commands=['add'])
def start_add_resource(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি এই কমান্ড ব্যবহারের অনুমতিপ্রাপ্ত নন।")
        return
    
    admin_temp_data[message.from_user.id] = {}
    bot.reply_to(message, "📦 নতুন রিসোর্স যোগ করা হচ্ছে!\n\nক্যাটাগরি বেছে নিন:\nলিখুন `font` অথবা `plp`", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    cat = message.text.lower().strip()
    if cat not in ['font', 'plp']:
        bot.reply_to(message, "ভুল ইনপুট! শুধু `font` অথবা `plp` লিখে পাঠান।")
        return
    admin_temp_data[message.from_user.id]['type'] = cat
    bot.reply_to(message, f"✅ ক্যাটাগরি: {cat.upper()}\n\nএবার রিসোর্সের নাম লিখে পাঠান:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    admin_temp_data[message.from_user.id]['name'] = message.text.strip()
    bot.reply_to(message, "🪙 এই রিসোর্সের জন্য কত কয়েন লাগবে? (যেমন: 10):")
    bot.register_next_step_handler(message, get_coins)

def get_coins(message):
    try:
        coins = int(message.text.strip())
        admin_temp_data[message.from_user.id]['coins'] = coins
        bot.reply_to(message, "🖼️ এবার থাম্বনেইলের প্রিভিউ ছবি পাঠান:")
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
    bot.reply_to(message, "📁 এবার মূল ফাইলটি (ZIP / TTF / PLP ডকুমেন্ট ফাইল হিসেবে) সরাসরি এখানে পাঠিয়ে দিন:")
    bot.register_next_step_handler(message, get_file_document)

def get_file_document(message):
    if not message.document:
        bot.reply_to(message, "❌ আপনি কোনো ফাইল পাঠাননি! দয়া করে ফাইল হিসেবে (Document) পাঠান:")
        bot.register_next_step_handler(message, get_file_document)
        return

    doc_file_id = message.document.file_id
    admin_temp_data[message.from_user.id]['file_id'] = doc_file_id
    resource = admin_temp_data[message.from_user.id]
    
    # ফায়ারবেসে তথ্য সেভ করা
    res = requests.post(FIREBASE_URL, json=resource)
    if res.status_code == 200:
        bot.reply_to(message, f"🎉 দারুণ! ফাইল সফলভাবে যুক্ত হয়েছে!\n\n📌 নাম: {resource['name']}\n📁 ক্যাটাগরি: {resource['type'].upper()}\n🪙 কয়েন: {resource['coins']}\n\n✅ মিনি অ্যাপে এটি লাইভ হয়ে গেছে এবং ইউজার ইনবক্সেই ফাইল পেয়ে যাবে!")
    else:
        bot.reply_to(message, "❌ ফায়ারবেসে তথ্য সংরক্ষণ করা যায়নি।")

print("Admin Bot is running...")
bot.infinity_polling()
