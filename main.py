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
CHANNEL_URL = "https://t.me/PLPStoreBD0"
BOT_USERNAME = "PLPStoreOfficialBot"

bot = telebot.TeleBot(BOT_TOKEN)
admin_temp_data = {}
edit_sessions = {}
coin_sessions = {}

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

# --- ম্যানুয়াল চ্যানেল লিঙ্ক কমান্ড ---
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

# --- চ্যানেলে টেস্ট পোস্ট কমান্ড ---
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

# --- রিসোর্স ব্রডকাস্ট ফাংশন (শুধু চ্যানেলে যাবে) ---
def broadcast_new_resource(resource):
    try:
        saved_chats = requests.get(f"{FIREBASE_BASE}/connected_chats.json").json() or {}
        
        target_channels = set()
        try:
            ch_info = bot.get_chat(CHANNEL_ID)
            target_channels.add(ch_info.id)
        except Exception:
            target_channels.add(CHANNEL_ID)

        for k, v in saved_chats.items():
            raw_id = None
            if isinstance(v, dict) and 'id' in v:
                raw_id = v['id']
            elif isinstance(v, (str, int)):
                raw_id = v
            else:
                raw_id = k.replace("m_", "-")
            
            if raw_id:
                try:
                    target_channels.add(int(raw_id))
                except ValueError:
                    try:
                        resolved = bot.get_chat(raw_id)
                        target_channels.add(resolved.id)
                    except Exception:
                        target_channels.add(raw_id)

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
        
        caption_text = (
            f"🔥 **নতুন প্রিমিয়াম রিসোর্স যুক্ত হয়েছে!**\n\n"
            f"📌 **নাম:** {resource.get('name')}\n"
            f"📁 **ক্যাটাগরি:** {cat_name}\n"
            f"🪙 **মূল্য:** {resource.get('coins')} কয়েন\n\n"
            f"✨ এখনই প্রিমিয়াম রিসোর্স অ্যাপ থেকে কয়েন দিয়ে আনলক করে নিতে পারেন!"
        )
        
        channel_markup = InlineKeyboardMarkup()
        btn_text = f"🛒 {cat_name} সংগ্রহ করুন"
        channel_markup.add(InlineKeyboardButton(btn_text, url=f"https://t.me/{BOT_USERNAME}?start=open_{target_tab}"))

        raw_vid = resource.get('raw_video_id')
        raw_photo = resource.get('raw_photo_id') or resource.get('image')

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

    except Exception as e:
        print(f"Broadcast main error: {e}")

# --- ক্যানসেল হ্যান্ডলার ---
def cancel_process(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id in admin_temp_data:
        del admin_temp_data[message.from_user.id]
    if message.from_user.id in edit_sessions:
        del edit_sessions[message.from_user.id]
    if message.from_user.id in coin_sessions:
        del coin_sessions[message.from_user.id]
    
    if int(message.from_user.id) == int(ADMIN_ID):
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

    if is_user_member(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=False)
        
        if target_arg.startswith("get_"):
            process_resource_delivery(call.message.chat.id, target_arg)
        else:
            bot.send_message(
                call.message.chat.id,
                f"👋 স্বাগতম {call.from_user.first_name}!\n\n💎 প্রিমিয়াম রিসোর্স অ্যাপে আপনাকে স্বাগতম। নিচের বাটনে চাপ দিয়ে অ্যাপ ওপেন করুন:",
                reply_markup=get_main_keyboard()
            )
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনও চ্যানেলে জয়েন করেননি! আগে জয়েন করুন।", show_alert=True)

# ফাইল ডেলিভারি ফাংশন
def process_resource_delivery(chat_id, arg_text):
    file_key = arg_text.replace("get_", "").split("_from_")[0]
    bot.send_message(chat_id, "⏳ আপনার ফাইল(সমূহ) প্রস্তুত করা হচ্ছে...")
    try:
        res = requests.get(f"{FIREBASE_BASE}/resources/{file_key}.json")
        item = res.json()
        if item:
            res_type = item.get("type", "plp").upper()
            if item.get("download_link"):
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("📥 সরাসরি ফাইল ডাউনলোড করুন", url=item["download_link"]))
                markup.add(InlineKeyboardButton("🚀 পুনরায় অ্যাপ খুলুন", web_app=WebAppInfo(url=WEB_APP_URL)))
                bot.send_message(
                    chat_id,
                    f"🎁 আপনার রিসোর্স: *{item.get('name', 'রিসোর্স')}*\n"
                    f"📁 ক্যাটাগরি: *{res_type}*\n"
                    f"🪙 ব্যবহৃত কয়েন: {item.get('coins', 0)}\n\n"
                    "🔗 নিচের বাটনে চাপ দিয়ে ড্রাইভ/ডাউনলোড লিঙ্ক থেকে ফাইল সংগ্রহ করুন:",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return

            file_ids = item.get("file_ids") or ([] if not item.get("file_id") else [item.get("file_id")])
            if file_ids:
                total_f = len(file_ids)
                for idx, fid in enumerate(file_ids, 1):
                    cap = (
                        f"🎁 ফাইল ({idx}/{total_f}): *{item.get('name', 'রিসোর্স')}*\n"
                        f"📁 ক্যাটাগরি: *{res_type}*\n\n"
                        "📂 সেভ করতে ফাইলে ট্যাপ করুন ও ডাউনলোড শেষে ৩-ডট (⋮) চেপে **'Save to Downloads'** করুন।"
                    )
                    bot.send_document(chat_id, fid, caption=cap, parse_mode="Markdown")
                    time.sleep(0.3)
                bot.send_message(chat_id, "✅ আপনার সমস্ত ফাইল ডেলিভার করা হয়েছে!", reply_markup=get_main_keyboard())
                return
        else:
            bot.send_message(chat_id, "❌ ফাইলটি ডাটাবেজে খুঁজে পাওয়া যায়নি।", reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, "❌ রিসোর্স ডেলিভারিতে সমস্যা দেখা দিয়েছে।", reply_markup=get_main_keyboard())

# --- স্টার্ট ও ডেলিভারি হ্যান্ডলার (ফোর্স সাবস্ক্রিপশন যুক্ত) ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # ইউজার রেজিস্ট্রেশন
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

    # রেফারেল হ্যান্ডলার
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

    # অ্যাডমিন প্যানেল হ্যান্ডলার
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

    # সাধারণ ইউজারের জন্য চ্যানেল জয়েন ভেরিফিকেশন চেক
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

    # রিসোর্স ডেলিভারি হ্যান্ডলার
    if len(args) > 1 and args[1].startswith("get_"):
        process_resource_delivery(message.chat.id, args[1])
        return

    # স্বাভাবিক ইউজার ওয়েলকাম
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
        "image": "নতুন থাম্বনেইল ছবিটি ফটো হিসেবে পাঠান:",
        "video": "নতুন প্রিভিউ ভিডিও ফাইলটি পাঠান (ভিডিও হিসেবে):",
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
                f"🎉 **সফলভাবে ফাইল আপডেট হয়েছে!**\n\nমোট **{len(file_list)}টি** ফাইল সেভ করা হয়েছে।",
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
            f"📥 ফাইল ({count}) গ্রহণ করা হয়েছে!\n\nআরও ফাইল থাকলে পাঠান, অথবা শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন।"
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

# --- রিসোর্স যুক্ত করার ফ্লো (বাটন ক্লিক) ---
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
        bot.reply_to(
            message, 
            "📂 **PLP ফাইল বা লিঙ্ক পাঠান:**\n\n"
            "• **ছোট ফাইল হলে:** ১টি বা একাধিক ফাইল পাঠান এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন।\n"
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
    
    bot.reply_to(
        message, 
        "📁 প্রিভিউ ভিডিও যুক্ত হয়েছে!\n\nএবার **XML ফাইল(সমূহ) পাঠান** এবং সব পাঠানো শেষ হলে নিচের **✅ আপলোড সম্পন্ন** বাটনে চাপুন:",
        reply_markup=get_file_collection_keyboard(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, get_batch_files_or_link)

# ব্যাচ ফাইল অথবা লিংক হ্যান্ডলার
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

    firebase_payload = {k: v for k, v in resource.items() if k not in ['raw_photo_id', 'raw_video_id']}
    res = requests.post(f"{FIREBASE_BASE}/resources.json", json=firebase_payload)
    
    if res.status_code == 200:
        total_files = len(resource.get('file_ids', []))
        file_info_msg = f"📦 মোট ফাইল: {total_files}টি" if total_files > 0 else "🔗 লিঙ্ক সংযুক্ত"
        
        bot.reply_to(
            message,
            f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n\n"
            f"📌 নাম: {resource['name']}\n"
            f"📁 ক্যাটাগরি: {resource['type'].upper()}\n"
            f"🪙 মূল্য: {resource['coins']} কয়েন\n"
            f"{file_info_msg}\n\n"
            f"✅ ওয়েব অ্যাপে যুক্ত হয়েছে এবং চ্যানেলে ব্রডকাস্ট পাঠানো হয়েছে!",
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
