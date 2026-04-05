import telebot
import requests
import re
import os
import time
import yt_dlp
from telebot import types

# --- CONFIGURATION ---
# ប្រើ Environment Variable លើ Railway ដើម្បីសុវត្ថិភាព ឬដាក់ផ្ទាល់ក៏បាន
TOKEN = os.getenv("BOT_TOKEN", "8004829165:AAGbUIZxt7YkRj7UxRgVWNDU26aKvJP3ppI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5039150238"))
BOT_USERNAME = "@cheadowbot"
CREDIT = f"\n\n━━━━━━━━━━━━━━━\n🚀 បង្កើតដោយ៖ @CheaOfficial\n🤖 Bot: {BOT_USERNAME}"

bot = telebot.TeleBot(TOKEN)
LINK_CACHE = {}

class YtDlpProgress:
    def __init__(self, bot, chat_id, message_id):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.last_update = 0

    def hook(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - self.last_update > 4:
                try:
                    p = d.get('_percent_str', '0%')
                    s = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', 'N/A'))
                    speed = d.get('_speed_str', 'N/A')
                    text = f"📥 **កំពុងដោនឡូត...**\n\n📊 ភាគរយ: `{p}`\n📦 ទំហំ: `{s}`\n⚡ ល្បឿន: `{speed}`"
                    self.bot.edit_message_text(text, self.chat_id, self.message_id, parse_mode="Markdown")
                    self.last_update = now
                except: pass

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"👋 សួស្តី! ផ្ញើ Link YouTube, TikTok ឬ FB មកខ្ញុំដើម្បីដោនឡូត។{CREDIT}")

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    url = message.text
    chat_id = message.chat.id
    
    msg_status = bot.reply_to(message, "🔎 **កំពុងឆែក Link...**", parse_mode="Markdown")

    if "youtube.com" in url or "youtu.be" in url:
        cache_id = str(message.message_id)
        LINK_CACHE[cache_id] = url
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [
            types.InlineKeyboardButton("🎬 1080p", callback_data=f"yt|1080|{cache_id}"),
            types.InlineKeyboardButton("🎬 720p", callback_data=f"yt|720|{cache_id}"),
            types.InlineKeyboardButton("🎬 480p", callback_data=f"yt|480|{cache_id}"),
            types.InlineKeyboardButton("🎧 MP3", callback_data=f"yt|mp3|{cache_id}")
        ]
        markup.add(*btns)
        bot.edit_message_text("🎬 **YouTube**\nសូមជ្រើសរើសកម្រិតវីដេអូ៖", chat_id, msg_status.message_id, reply_markup=markup)
        return
    
    # សម្រាប់ Link ផ្សេងៗ (FB/TikTok) - ប្រើកូដសាមញ្ញ
    bot.edit_message_text("⏳ **កំពុងទាញយក...**", chat_id, msg_status.message_id)
    try:
        ydl_opts = {'format': 'best', 'quiet': True, 'outtmpl': 'downloads/%(id)s.%(ext)s'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            with open(filename, 'rb') as f:
                bot.send_video(chat_id, f, caption=f"✅ រួចរាល់{CREDIT}")
            os.remove(filename)
            bot.delete_message(chat_id, msg_status.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ បរាជ័យ: {str(e)}", chat_id, msg_status.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("yt|"))
def yt_callback(call):
    _, quality, cache_id = call.data.split("|")
    url = LINK_CACHE.get(cache_id)
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if not url: return

    bot.edit_message_text("⏳ **កំពុងទាញយកវីដេអូ...**", chat_id, msg_id)
    
    folder = "downloads"
    if not os.path.exists(folder): os.makedirs(folder)
    
    is_mp3 = quality == "mp3"
    opts = {
        'format': 'bestaudio/best' if is_mp3 else f'bestvideo[height<={quality}]+bestaudio/best',
        'outtmpl': f'{folder}/%(id)s.%(ext)s',
        'progress_hooks': [YtDlpProgress(bot, chat_id, msg_id).hook],
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    
    if is_mp3:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if is_mp3: path = path.rsplit('.', 1)[0] + '.mp3'
            
            bot.edit_message_text("⬆️ **កំពុងផ្ញើឯកសារ...**", chat_id, msg_id)
            with open(path, 'rb') as f:
                if is_mp3: bot.send_audio(chat_id, f, caption=CREDIT)
                else: bot.send_video(chat_id, f, caption=f"🎬 Quality: {quality}p{CREDIT}")
            
            os.remove(path)
            bot.delete_message(chat_id, msg_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, msg_id)

if __name__ == "__main__":
    bot.infinity_polling()
