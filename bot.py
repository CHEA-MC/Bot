import telebot
import requests
import re
import os
import time
import yt_dlp
from telebot import types

# --- CONFIGURATION ---
TOKEN = "8004829165:AAGbUIZxt7YkRj7UxRgVWNDU26aKvJP3ppI"
ADMIN_ID = 5039150238 
BOT_USERNAME = "@cheadowbot"
TUTORIAL_VIDEO = "https://t.me/khmersongs_mp3/944"
CREDIT = f"\n\n━━━━━━━━━━━━━━━\n🚀 បង្កើតដោយ៖ @CheaOfficial\n🤖 Bot: {BOT_USERNAME}"
USER_FILE = "users.txt" # ឈ្មោះ File សម្រាប់ទុក ID អ្នកប្រើប្រាស់

bot = telebot.TeleBot(TOKEN)

# Cache សម្រាប់រក្សាទុក Link បណ្តោះអាសន្ន
LINK_CACHE = {}

# --- ADMIN HELPER FUNCTIONS ---

def save_user(chat_id):
    """រក្សាទុក ID អ្នកប្រើប្រាស់ទៅក្នុង File (បើមិនទាន់មាន)"""
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w") as f: f.write("")
    
    with open(USER_FILE, "r") as f:
        users = f.read().splitlines()
    
    if str(chat_id) not in users:
        with open(USER_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def notify_admin(message, action_type, content=None):
    """ផ្ញើសារជូនដំណឹងទៅ Admin"""
    try:
        user = message.from_user
        name = f"{user.first_name} {user.last_name if user.last_name else ''}"
        username = f"@{user.username}" if user.username else "No Username"
        user_id = user.id
        
        text = f"🔔 **New Activity Notification**\n"
        text += f"👤 Name: {name}\n"
        text += f"🆔 ID: `{user_id}`\n"
        text += f"🏷 User: {username}\n"
        text += f"⚙️ Action: **{action_type}**"
        
        if content:
            text += f"\n📝 Content: `{content}`"
            
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Admin Log Error: {e}")

# --- HELPER FUNCTIONS ---

def format_size(bytes):
    """បម្លែងទំហំ Byte ទៅជា MB"""
    try:
        bytes = float(bytes)
        kb = bytes / 1024
    except:
        return "N/A"
    if kb >= 1024:
        mb = kb / 1024
        return "%.2f MB" % mb
    else:
        return "%.2f KB" % kb

def progress_bar(current, total):
    """បង្កើតរូបរាង Progress Bar"""
    if total <= 0: return "▓▓▓▓▓▓▓▓▓▓ 100%"
    percentage = current * 100 / total
    filled_length = int(percentage // 10)
    bar = '▓' * filled_length + '░' * (10 - filled_length)
    return f"{bar} {percentage:.1f}%"

def download_with_progress(url, message, chat_id, filename):
    """ដោនឡូតដោយមានបង្ហាញភាគរយ និងទំហំ (សម្រាប់ Direct Link ដូចជា FB, TikTok)"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        total_size = int(response.headers.get('content-length', 0))
        
        if not os.path.exists('downloads'): os.makedirs('downloads')
        path = f"downloads/{filename}"

        with open(path, 'wb') as f:
            start_time = time.time()
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=1024*1024): 
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if time.time() - start_time > 3:
                        try:
                            size_str = f"{format_size(downloaded)} / {format_size(total_size)}"
                            prog_str = progress_bar(downloaded, total_size)
                            bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message.message_id,
                                text=f"📥 **កំពុងដោនឡូត...**\n\n{prog_str}\n📦 ទំហំ: `{size_str}`",
                                parse_mode="Markdown"
                            )
                            start_time = time.time()
                        except: pass
        return path
    except Exception as e:
        print(e)
        return None

# Class សម្រាប់ចាប់យកភាគរយពី yt-dlp ពេលដោនឡូត YouTube
class YtDlpProgress:
    def __init__(self, bot, chat_id, message_id):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.last_update_time = time.time()

    def hook(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - self.last_update_time > 3: # អាប់ដេតរៀងរាល់ ៣ វិនាទី
                try:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    size_str = f"{format_size(downloaded)} / {format_size(total)}" if total else f"{format_size(downloaded)}"
                    prog_str = progress_bar(downloaded, total)
                    speed = d.get('_speed_str', 'N/A').strip()
                    
                    text = f"📥 **កំពុងដោនឡូតពី YouTube...**\n\n{prog_str}\n📦 ទំហំ: `{size_str}`\n⚡ ល្បឿន: `{speed}`"
                    self.bot.edit_message_text(text, self.chat_id, self.message_id, parse_mode="Markdown")
                    self.last_update_time = now
                except:
                    pass

def get_video_info(url, is_audio=False):
    """ទាញយកទាំង Link និង ចំណងជើង"""
    ydl_opts = {
        'format': 'bestaudio/best' if is_audio else 'best',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}} # បន្លំខ្លួនកុំឲ្យជាប់ 403
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url'), info.get('title', 'Video')
    except:
        return None, None

# --- ADMIN COMMANDS ---

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.chat.id == ADMIN_ID:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                count = len(f.readlines())
            bot.reply_to(message, f"📊 **ស្ថិតិ Bot**\n\n👥 ចំនួនអ្នកប្រើប្រាស់សរុប: `{count}` នាក់", parse_mode="Markdown")
        else:
            bot.reply_to(message, "មិនទាន់មានទិន្នន័យអ្នកប្រើប្រាស់។")

@bot.message_handler(commands=['cast'])
def broadcast_message(message):
    if message.chat.id == ADMIN_ID:
        msg = message.text.replace("/cast", "").strip()
        if not msg:
            bot.reply_to(message, "❌ សូមសរសេរសារដែលចង់ប្រកាស។\nឧទាហរណ៍: `/cast សួស្តីអ្នកទាំងអស់គ្នា!`", parse_mode="Markdown")
            return
        
        if not os.path.exists(USER_FILE):
            bot.reply_to(message, "❌ មិនទាន់មានអ្នកប្រើប្រាស់។")
            return

        with open(USER_FILE, "r") as f:
            users = f.read().splitlines()
        
        sent = 0
        failed = 0
        status_msg = bot.reply_to(message, f"⏳ កំពុងផ្ញើទៅកាន់ {len(users)} នាក់...")
        
        for user_id in users:
            try:
                bot.send_message(user_id, f"📢 **សេចក្តីប្រកាស**\n\n{msg}", parse_mode="Markdown")
                sent += 1
                time.sleep(0.05)
            except:
                failed += 1
        
        bot.edit_message_text(f"✅ **ការប្រកាសបានបញ្ចប់**\n\n✅ ជោគជ័យ: {sent}\n❌ បរាជ័យ: {failed}", message.chat.id, status_msg.message_id, parse_mode="Markdown")

# --- USER COMMANDS ---

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    notify_admin(message, "START BOT")
    bot.send_video(message.chat.id, TUTORIAL_VIDEO, caption=f"👋 សួស្តី! ផ្ញើ Link មកដើម្បីដោនឡូត។\n\n✅ Facebook, YouTube, TikTok, Pinterest{CREDIT}")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_links(message):
    url = message.text
    chat_id = message.chat.id
    
    save_user(chat_id)
    notify_admin(message, "SEND LINK", url)

    msg_status = bot.reply_to(message, "🔎 **កំពុងស្វែងរកទិន្នន័យ...**", parse_mode="Markdown")

    # YouTube Logic
    if "youtube.com" in url or "youtu.be" in url:
        cache_id = str(message.message_id)
        LINK_CACHE[cache_id] = url
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_1080 = types.InlineKeyboardButton("🎬 1080p", callback_data=f"yt|1080|{cache_id}")
        btn_720 = types.InlineKeyboardButton("🎬 720p", callback_data=f"yt|720|{cache_id}")
        btn_480 = types.InlineKeyboardButton("🎬 480p", callback_data=f"yt|480|{cache_id}")
        btn_360 = types.InlineKeyboardButton("🎬 360p", callback_data=f"yt|360|{cache_id}")
        btn_mp3 = types.InlineKeyboardButton("🎧 MP3 Audio", callback_data=f"yt|mp3|{cache_id}")
        
        markup.add(btn_1080, btn_720, btn_480, btn_360)
        markup.add(btn_mp3)
        
        bot.edit_message_text("🎬 **YouTube Download**\nសូមជ្រើសរើសកម្រិតវីដេអូ ឬសម្លេងខាងក្រោម៖", chat_id, msg_status.message_id, reply_markup=markup, parse_mode="Markdown")
        return

    # TikTok Logic
    if "tiktok.com" in url:
        try:
            res = requests.get(f"https://www.tikwm.com/api/?url={url}").json()
            if res.get('code') == 0:
                data = res['data']
                title = data.get('title', 'TikTok Video')
                
                cache_id = str(message.message_id)
                LINK_CACHE[cache_id] = {
                    'vid': data.get('play'),
                    'aud': data.get('music'),
                    'title': title,
                    'images': data.get('images')
                }

                if 'images' in data:
                    bot.delete_message(chat_id, msg_status.message_id)
                    for img in data['images']: bot.send_photo(chat_id, img)
                    bot.send_message(chat_id, f"✅ **{title}**{CREDIT}", parse_mode="Markdown")
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🎬 Video (No Watermark)", callback_data=f"tik|vid|{cache_id}"),
                               types.InlineKeyboardButton("🎧 MP3 (Audio)", callback_data=f"tik|aud|{cache_id}"))
                    bot.edit_message_text(f"🎵 **TikTok Download**\n\n📝 **{title}**\n\nជ្រើសរើស៖", chat_id, msg_status.message_id, reply_markup=markup)
            else:
                bot.edit_message_text("❌ រកមិនឃើញ Video ទេ។", chat_id, msg_status.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, msg_status.message_id)
        return

    try:
        # Facebook Logic
        if any(x in url for x in ["facebook.com", "fb.watch", "fb.com"]):
            fb_url, title = get_video_info(url)
            if fb_url:
                path = download_with_progress(fb_url, msg_status, chat_id, f"fb_{os.urandom(3).hex()}.mp4")
                if path:
                    bot.edit_message_text("⬆️ **កំពុងផ្ញើ...**", chat_id, msg_status.message_id, parse_mode="Markdown")
                    with open(path, 'rb') as f: 
                        bot.send_video(chat_id, f, caption=f"✅ **{title}**{CREDIT}", parse_mode="Markdown")
                    os.remove(path)
                    bot.delete_message(chat_id, msg_status.message_id)
                    return

        # Pinterest Logic
        if "pin.it" in url or "pinterest.com" in url:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            vid = re.search(r'https://[^"]+\.mp4', resp.text)
            if vid:
                video_url = vid.group(0)
                path = download_with_progress(video_url, msg_status, chat_id, f"pin_{os.urandom(3).hex()}.mp4")
                if path:
                    bot.edit_message_text("⬆️ **កំពុងផ្ញើ...**", chat_id, msg_status.message_id, parse_mode="Markdown")
                    with open(path, 'rb') as f:
                        bot.send_video(chat_id, f, caption=f"✅ Pinterest Video{CREDIT}")
                    os.remove(path)
                    bot.delete_message(chat_id, msg_status.message_id)
                    return

    except Exception as e:
        bot.edit_message_text(f"❌ Error: {e}", chat_id, msg_status.message_id)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    try:
        service, type_, cache_id = call.data.split("|")
    except: return

    # TIKTOK HANDLER
    if service == "tik":
        data = LINK_CACHE.get(cache_id)
        if not data:
            bot.answer_callback_query(call.id, "❌ ទិន្នន័យចាស់ពេក សូមផ្ញើ Link ម្តងទៀត")
            return

        link = data['vid'] if type_ == 'vid' else data['aud']
        ext = 'mp4' if type_ == 'vid' else 'mp3'
        filename = f"tiktok_{os.urandom(3).hex()}.{ext}"

        bot.edit_message_text(f"⏳ **កំពុងដោនឡូត... (0%)**", chat_id, msg_id, parse_mode="Markdown")
        path = download_with_progress(link, call.message, chat_id, filename)
        
        if path:
            bot.edit_message_text("⬆️ **កំពុងផ្ញើ...**", chat_id, msg_id, parse_mode="Markdown")
            try:
                with open(path, 'rb') as f:
                    if type_ == 'vid':
                        bot.send_video(chat_id, f, caption=f"✅ **{data['title']}**{CREDIT}", parse_mode="Markdown")
                    else:
                        bot.send_audio(chat_id, f, caption=f"✅ **{data['title']}**{CREDIT}", title=data['title'], parse_mode="Markdown")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Error sending: {e}")
            
            os.remove(path)
            bot.delete_message(chat_id, msg_id)
        else:
            bot.edit_message_text("❌ បរាជ័យក្នុងការដោនឡូត។", chat_id, msg_id)

    # YOUTUBE HANDLER 
    elif service == "yt":
        url = LINK_CACHE.get(cache_id)
        if not url:
            bot.answer_callback_query(call.id, "❌ ទិន្នន័យចាស់ពេក សូមផ្ញើ Link ម្តងទៀត")
            return

        bot.edit_message_text("⏳ **កំពុងចាប់ផ្តើមដោនឡូត...**", chat_id, msg_id, parse_mode="Markdown")
        
        if not os.path.exists('downloads'): os.makedirs('downloads')
        
        is_audio = (type_ == "mp3")
        base_name = f"downloads/yt_{os.urandom(3).hex()}"
        
        if is_audio:
            ydl_format = 'bestaudio/best'
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            ydl_format = f'bestvideo[height<={type_}][ext=mp4]+bestaudio[ext=m4a]/best[height<={type_}]/best'
            postprocessors = []

        progress_tracker = YtDlpProgress(bot, chat_id, msg_id)
        
        ydl_opts = {
            'format': ydl_format,
            'outtmpl': f"{base_name}.%(ext)s",
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_tracker.hook],
            'postprocessors': postprocessors,
            # បន្ថែមការបន្លំខ្លួនកុំឲ្យជាប់ Error 403 ពេលកំពុង Download ពិតប្រាកដ
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'YouTube Video')
                
                final_filename = ydl.prepare_filename(info)
                if is_audio:
                    final_filename = final_filename.rsplit('.', 1)[0] + '.mp3'

                bot.edit_message_text("⬆️ **កំពុងផ្ញើទៅកាន់អ្នក... អាចចំណាយពេលបន្តិចអាស្រ័យលើទំហំ**", chat_id, msg_id, parse_mode="Markdown")
                
                file_size = os.path.getsize(final_filename)
                if file_size > 50 * 1024 * 1024: 
                    bot.edit_message_text(f"❌ **បរាជ័យ:** ឯកសារមានទំហំធំពេក (`{format_size(file_size)}`) Telegram អនុញ្ញាតត្រឹម 50MB តែប៉ុណ្ណោះ។", chat_id, msg_id, parse_mode="Markdown")
                else:
                    with open(final_filename, 'rb') as f:
                        if is_audio: 
                            bot.send_audio(chat_id, f, caption=f"✅ **{title}**{CREDIT}", parse_mode="Markdown", title=title)
                        else: 
                            bot.send_video(chat_id, f, caption=f"✅ **{title}**\n🎬 Quality: {type_}p{CREDIT}", parse_mode="Markdown")
                    bot.delete_message(chat_id, msg_id)
                
                if os.path.exists(final_filename):
                    os.remove(final_filename)
                    
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "403" in error_msg:
                 bot.edit_message_text(f"❌ **Error 403 Forbidden:** YouTube កំពុងប្លុកប្រព័ន្ធ។\n\nអ្នកគ្រប់គ្រង (Admin) សូមបើក Terminal រួចវាយបញ្ជា៖\n`pip install -U yt-dlp`", chat_id, msg_id, parse_mode="Markdown")
            else:
                 bot.edit_message_text(f"❌ **បរាជ័យ:** {error_msg}", chat_id, msg_id, parse_mode="Markdown")
            print(f"YouTube Download Error: {e}")
        except Exception as e:
            bot.edit_message_text(f"❌ **មានបញ្ហាអ្វីមួយកើតឡើង:** អាចមកពីវីដេអូអត់មានទម្រង់នេះ។", chat_id, msg_id, parse_mode="Markdown")
            print(f"General Error: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
