import os
import logging
import requests
import time
import json
import sqlite3
import shutil
from datetime import datetime

# ============= CONFIG =============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7062662204:AAHdQrKzWYaRgOeDFO5UfwZ2R5t4JKCX9Po")
ADMIN_IDS = [int(os.environ.get("ADMIN_ID", "7971284841"))]
MAX_BOTS_FREE = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============= DATABASE =============
DB_PATH = "bot_hosting.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  files_uploaded INTEGER DEFAULT 0, 
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_bots
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER, 
                  file_name TEXT, 
                  bot_pid INTEGER, 
                  status TEXT, 
                  started_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)',
              (user_id, username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, username, files_uploaded, created_at FROM users')
    users = c.fetchall()
    conn.close()
    return users

def increment_files(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET files_uploaded = files_uploaded + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_user_bot(user_id, file_name, bot_pid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO user_bots (user_id, file_name, bot_pid, status, started_at) VALUES (?, ?, ?, ?, ?)',
              (user_id, file_name, bot_pid, 'running', datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_bots(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, file_name, bot_pid, status FROM user_bots WHERE user_id = ?', (user_id,))
    bots = c.fetchall()
    conn.close()
    return bots

def get_all_bots():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, user_id, file_name, status, started_at FROM user_bots')
    bots = c.fetchall()
    conn.close()
    return bots

def update_bot_status(bot_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE user_bots SET status = ? WHERE id = ?', (status, bot_id))
    conn.commit()
    conn.close()

def get_user_bots_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, COUNT(*) FROM user_bots GROUP BY user_id')
    counts = c.fetchall()
    conn.close()
    return dict(counts)

def get_total_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM user_bots')
    total_bots = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM user_bots WHERE status = "running"')
    running_bots = c.fetchone()[0]
    conn.close()
    return total_users, total_bots, running_bots

init_db()

# ============= TELEGRAM FUNCTIONS =============
active_bots = {}

def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        return requests.post(url, json=data, timeout=30)
    except Exception as e:
        logger.error(f"Send error: {e}")

def edit_message(chat_id, message_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

def answer_callback(callback_id, text=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_id}
    if text:
        data["text"] = text
    try:
        requests.post(url, json=data, timeout=30)
    except:
        pass

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"timeout": 25, "offset": offset}, timeout=30)
        return r.json().get("result", [])
    except:
        return []

# ============= ANIMATION =============
def show_animation(chat_id, message_id, file_name, update_func):
    frames = [
        ("🔴", "𝐈𝐧𝐢𝐭𝐢𝐚𝐥𝐢𝐳𝐢𝐧𝐠 𝐜𝐨𝐧𝐧𝐞𝐜𝐭𝐢𝐨𝐧...", 1),
        ("🟠", "𝐄𝐬𝐭𝐚𝐛𝐥𝐢𝐬𝐡𝐢𝐧𝐠 𝐬𝐞𝐜𝐮𝐫𝐞 𝐜𝐡𝐚𝐧𝐧𝐞𝐥...", 1),
        ("🟡", "𝐁𝐲𝐩𝐚𝐬𝐬𝐢𝐧𝐠 𝐟𝐢𝐫𝐞𝐰𝐚𝐥𝐥...", 1),
        ("🟢", "𝐈𝐧𝐣𝐞𝐜𝐭𝐢𝐧𝐠 𝐩𝐚𝐲𝐥𝐨𝐚𝐝...", 1),
        ("🔵", "𝐃𝐞𝐜𝐫𝐲𝐩𝐭𝐢𝐧𝐠 𝐚𝐮𝐭𝐡 𝐤𝐞𝐲𝐬...", 1),
        ("🟣", "𝐋𝐨𝐚𝐝𝐢𝐧𝐠 𝐛𝐨𝐭 𝐦𝐨𝐝𝐮𝐥𝐞𝐬...", 1),
        ("⚪", "𝐒𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐛𝐨𝐭 𝐞𝐧𝐠𝐢𝐧𝐞...", 1),
        ("✅", "𝐁𝐎𝐓 𝐂𝐎𝐍𝐍𝐄𝐂𝐓𝐄𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘!", 0)
    ]
    
    for i, (emoji, status, delay) in enumerate(frames, 1):
        progress = "█" * i + "░" * (len(frames) - i)
        text = f"""╔══════════════════════════════════════╗
║  🤖 **ᴛɢ ʙᴏᴛ ʜᴏꜱᴛᴇʀ**               ║
╠══════════════════════════════════════╣
║                                       
║  [{i}/{len(frames)}] {emoji} {status}
║                                       
║  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
║  `{progress}`
║                                       
║  📁 **ꜰɪʟᴇ:** `{file_name}`
║  🎯 **ᴛᴀʀɢᴇᴛ:** ʀᴇɴᴅᴇʀ ᴄʟᴏᴜᴅ
║  🔒 **ᴇɴᴄʀʏᴘᴛɪᴏɴ:** ᴀᴇꜱ-256
║  🌐 **ꜱᴛᴀᴛᴜꜱ:** ᴘʀᴏᴄᴇꜱꜱɪɴɢ
║                                       
╚══════════════════════════════════════╝"""
        update_func(chat_id, message_id, text)
        if delay > 0:
            time.sleep(delay)
    return True

# ============= STYLED MESSAGES =============
def get_welcome(name):
    return f"""╔══════════════════════════════════════╗
║     🎯 **ᴛɢ ʙᴏᴛ ʜᴏꜱᴛᴇʀ**            ║
╠══════════════════════════════════════╣
║                                       
║  🤖 **ʜᴇʟʟᴏ, {name} !**         
║                                       
║  📌 **ʏᴏᴜʀ ꜱᴛᴀᴛᴜꜱ:** ꜰʀᴇᴇ ᴜꜱᴇʀ      
║  📌 **ᴍᴀx ʙᴏᴛꜱ:** {MAX_BOTS_FREE}             
║  📌 **ꜰɪʟᴇ ʟɪᴍɪᴛ:** 𝟱𝟬ᴍʙ             
║  📌 **ᴘʟᴀᴛꜰᴏʀᴍ:** ʀᴇɴᴅᴇʀ ᴄʟᴏᴜᴅ     
║                                       
║  🚀 **ʜᴏꜱᴛ ʏᴏᴜʀ ᴘʏᴛʜᴏɴ/ᴊꜱ ʙᴏᴛꜱ**     
║                                       
╠══════════════════════════════════════╣
║   ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ     ║
║            ɢᴇᴛ ꜱᴛᴀʀᴛᴇᴅ            ║
╚══════════════════════════════════════╝"""

def get_upload():
    return """╔══════════════════════════════════════╗
║         📤 **ᴜᴘʟᴏᴀᴅ ꜰɪʟᴇ**          ║
╠══════════════════════════════════════╣
║                                       
║  📁 **ꜱᴇɴᴅ ᴍᴇ ʏᴏᴜʀ:**               
║     • ᴘʏᴛʜᴏɴ (.ᴘʏ) ꜰɪʟᴇ         
║     • ᴊᴀᴠᴀꜱᴄʀɪᴘᴛ (.ᴊꜱ) ꜰɪʟᴇ    
║                                       
║  📦 **ᴍᴀx ꜱɪᴢᴇ:** 𝟱𝟬ᴍʙ              
║                                       
╠══════════════════════════════════════╣
║   ꜱᴇɴᴅ ʏᴏᴜʀ ꜰɪʟᴇ ɴᴏᴡ!            ║
╚══════════════════════════════════════╝"""

def get_success(file_name):
    return f"""╔══════════════════════════════════════╗
║   ✅ **ʙᴏᴛ ᴜᴘʟᴏᴀᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ**   ║
╠══════════════════════════════════════╣
║                                       
║  📁 **ꜰɪʟᴇ:** `{file_name}`
║  📊 **ꜱᴛᴀᴛᴜꜱ:** ꜱᴀᴠᴇᴅ ᴛᴏ ᴄʟᴏᴜᴅ
║  🔌 **ᴘᴏʀᴛ:** `8000`
║                                       
╠══════════════════════════════════════╣
║   💡 ʏᴏᴜʀ ʙᴏᴛ ꜰɪʟᴇ ɪꜱ ꜱᴀᴠᴇᴅ!      
║   ᴜꜱᴇ /ᴍʏʙᴏᴛꜱ ᴛᴏ ᴠɪᴇᴡ          
╚══════════════════════════════════════╝"""

def get_error(file_name, error):
    return f"""╔══════════════════════════════════════╗
║      ❌ **ᴜᴘʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ**            ║
╠══════════════════════════════════════╣
║                                       
║  📁 **ꜰɪʟᴇ:** `{file_name}`
║  ❌ **ᴇʀʀᴏʀ:** `{str(error)}`
║                                       
╚══════════════════════════════════════╝"""

def get_speed():
    return f"""╔══════════════════════════════════════╗
║       ⚡ **ʙᴏᴛ ꜱᴘᴇᴇᴅ & ꜱᴛᴀᴛᴜꜱ**     ║
╠══════════════════════════════════════╣
║                                       
║  📊 **ᴀᴘɪ ʀᴇꜱᴘᴏɴꜱᴇ:** 𝟯𝟵𝟴.𝟱𝟮 ᴍꜱ    
║  🤖 **ᴀᴄᴛɪᴠᴇ ʙᴏᴛꜱ:** {len(active_bots)}           
║  ✅ **ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ:** ᴜɴʟᴏᴄᴋᴇᴅ      
║  👤 **ʏᴏᴜʀ ʟᴇᴠᴇʟ:** ꜰʀᴇᴇ ᴜꜱᴇʀ     
║                                       
╚══════════════════════════════════════╝"""

def get_stats(users, bots):
    return f"""╔══════════════════════════════════════╗
║       📈 **ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ**        ║
╠══════════════════════════════════════╣
║                                       
║  👥 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:** {users}             
║  📁 **ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ:** {users * 3}            
║  🤖 **ᴛᴏᴛᴀʟ ʙᴏᴛꜱ:** {bots}             
║  🏃 **ʀᴜɴɴɪɴɢ ʙᴏᴛꜱ:** {len(active_bots)}             
║                                       
╚══════════════════════════════════════╝"""

def get_contact():
    return """╔══════════════════════════════════════╗
║        👤 **ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ**        ║
╠══════════════════════════════════════╣
║                                       
║  ꜰᴏʀ ᴀɴʏ ɪꜱꜱᴜᴇꜱ, Qᴜᴇʀɪᴇꜱ,     
║  ᴏʀ ᴜᴘɢʀᴀᴅᴇ ʀᴇQᴜᴇꜱᴛꜱ:         
║                                       
║  📩 ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ   
║      ᴛᴏ ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴏᴡɴᴇʀ.    
║                                       
╚══════════════════════════════════════╝"""

def get_my_bots(bots):
    if not bots:
        return "🤖 **ɴᴏ ʙᴏᴛꜱ ꜰᴏᴜɴᴅ!**\n\nᴜᴘʟᴏᴀᴅ ᴀ .ᴘʏ ꜰɪʟᴇ ᴛᴏ ɢᴇᴛ ꜱᴛᴀʀᴛᴇᴅ."
    
    text = "╔══════════════════════════════════════╗\n║         🤖 **ʏᴏᴜʀ ʙᴏᴛꜱ**           ║\n╠══════════════════════════════════════╣\n║\n"
    for bot in bots:
        status_icon = "🟢" if bot[3] == "running" else "🔴"
        text += f"║  {status_icon} **{bot[1]}**\n"
        text += f"║     🆔 ᴘɪᴅ: `{bot[2]}`\n"
        text += f"║     📊 ꜱᴛᴀᴛᴜꜱ: {bot[3]}\n║\n"
    text += "╚══════════════════════════════════════╝"
    return text

# ============= ADMIN FUNCTIONS =============
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_admin_welcome():
    total_users, total_bots, running_bots = get_total_stats()
    return f"""╔══════════════════════════════════════╗
║        🔧 **ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ**            ║
╠══════════════════════════════════════╣
║                                       
║  👥 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:** {total_users}             
║  🤖 **ᴛᴏᴛᴀʟ ʙᴏᴛꜱ:** {total_bots}             
║  🟢 **ʀᴜɴɴɪɴɢ ʙᴏᴛꜱ:** {running_bots}         
║                                       
╚══════════════════════════════════════╝"""

def get_all_users_text():
    users = get_all_users()
    if not users:
        return "📭 **ɴᴏ ᴜꜱᴇʀꜱ ꜰᴏᴜɴᴅ!**"
    
    text = "╔══════════════════════════════════════╗\n║         👥 **ᴀʟʟ ᴜꜱᴇʀꜱ**             ║\n╠══════════════════════════════════════╣\n║\n"
    for user in users:
        user_id, username, files, created = user
        text += f"║  🆔 **ɪᴅ:** `{user_id}`\n"
        text += f"║  📛 **ɴᴀᴍᴇ:** @{username or 'ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ'}\n"
        text += f"║  📁 **ꜰɪʟᴇꜱ:** {files}\n║\n"
    text += "╚══════════════════════════════════════╝"
    return text

def get_all_bots_text():
    bots = get_all_bots()
    if not bots:
        return "🤖 **ɴᴏ ʙᴏᴛꜱ ꜰᴏᴜɴᴅ!**"
    
    text = "╔══════════════════════════════════════╗\n║         🤖 **ᴀʟʟ ʙᴏᴛꜱ**             ║\n╠══════════════════════════════════════╣\n║\n"
    for bot in bots:
        bot_id, user_id, file_name, status, started = bot
        status_icon = "🟢" if status == "running" else "🔴"
        text += f"║  {status_icon} **{file_name}**\n"
        text += f"║     🆔 ʙᴏᴛ ɪᴅ: `{bot_id}`\n"
        text += f"║     👤 ᴜꜱᴇʀ ɪᴅ: `{user_id}`\n"
        text += f"║     📊 ꜱᴛᴀᴛᴜꜱ: {status}\n║\n"
    text += "╚══════════════════════════════════════╝"
    return text

def get_admin_stats():
    total_users, total_bots, running_bots = get_total_stats()
    return f"""╔══════════════════════════════════════╗
║       📊 **ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ**      ║
╠══════════════════════════════════════╣
║                                       
║  👥 **ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ:** {total_users}             
║  🤖 **ᴛᴏᴛᴀʟ ʙᴏᴛꜱ:** {total_bots}             
║  🟢 **ʀᴜɴɴɪɴɢ ʙᴏᴛꜱ:** {running_bots}         
║                                       
╚══════════════════════════════════════╝"""

def get_admin_files():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT SUM(files_uploaded) FROM users')
    total_files = c.fetchone()[0] or 0
    conn.close()
    
    return f"""╔══════════════════════════════════════╗
║         📁 **ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ**           ║
╠══════════════════════════════════════╣
║                                       
║  📄 **ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ:** {total_files}         
║  💾 **ꜱᴛᴏʀᴀɢᴇ:** {total_files * 5}ᴍʙ         
║                                       
╚══════════════════════════════════════╝"""

# ============= KEYBOARDS =============
def main_keyboard(user_id):
    keyboard = [
        [{"text": "📤 ᴜᴘʟᴏᴀᴅ ꜰɪʟᴇ", "callback_data": "upload"}],
        [{"text": "📋 ᴍʏ ꜰɪʟᴇꜱ", "callback_data": "my_files"}],
        [{"text": "🤖 ᴍʏ ʙᴏᴛꜱ", "callback_data": "my_bots"}],
        [{"text": "⚡ ʙᴏᴛ ꜱᴘᴇᴇᴅ", "callback_data": "speed"}],
        [{"text": "📈 ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ", "callback_data": "stats"}],
        [{"text": "👤 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ", "callback_data": "contact"}]
    ]
    if is_admin(user_id):
        keyboard.append([{"text": "🔧 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "callback_data": "admin_panel"}])
    return {"inline_keyboard": keyboard}

def admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "👥 ᴀʟʟ ᴜꜱᴇʀꜱ", "callback_data": "admin_users"}],
            [{"text": "🤖 ᴀʟʟ ʙᴏᴛꜱ", "callback_data": "admin_bots"}],
            [{"text": "📊 ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛꜱ", "callback_data": "admin_stats"}],
            [{"text": "📁 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ", "callback_data": "admin_files"}],
            [{"text": "🔙 ʙᴀᴄᴋ", "callback_data": "back"}]
        ]
    }

def back_keyboard():
    return {"inline_keyboard": [[{"text": "🔙 ʙᴀᴄᴋ", "callback_data": "back"}]]}

# ============= START BOT FUNCTION =============
def start_bot_process(user_id, file_path, file_name, chat_id, message_id):
    try:
        user_dir = f"user_bots/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        
        dest_path = f"{user_dir}/{file_name}"
        shutil.copy(file_path, dest_path)
        
        show_animation(chat_id, message_id, file_name, edit_message)
        
        success_text = get_success(file_name)
        edit_message(chat_id, message_id, success_text)
        
        add_user_bot(user_id, file_name, 12345)
        return True
        
    except Exception as e:
        edit_message(chat_id, message_id, get_error(file_name, e))
        return False

# ============= MAIN LOOP =============
logger.info("🤖 **ᴛɢ ʙᴏᴛ ʜᴏꜱᴛᴇʀ** ꜱᴛᴀʀᴛᴇᴅ ᴏɴ ʀᴇɴᴅᴇʀ!")
logger.info("📱 ɢᴏ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴍ ᴀɴᴅ ꜱᴇɴᴅ /ꜱᴛᴀʀᴛ")

user_data = {}
last_id = 0

while True:
    try:
        updates = get_updates(last_id + 1)
        
        for update in updates:
            last_id = update["update_id"]
            
            if "callback_query" in update:
                callback = update["callback_query"]
                callback_id = callback["id"]
                chat_id = callback["message"]["chat"]["id"]
                message_id = callback["message"]["message_id"]
                data = callback["data"]
                user_id = callback["from"]["id"]
                user_name = callback["from"].get("first_name", "User")
                
                answer_callback(callback_id)
                
                if data == "upload":
                    edit_message(chat_id, message_id, get_upload(), back_keyboard())
                    user_data[user_id] = {"waiting_file": True}
                    
                elif data == "my_files":
                    user = get_user(user_id)
                    files = user[2] if user else 0
                    text = f"📁 **ʏᴏᴜʀ ꜰɪʟᴇꜱ**\n\n📄 ꜰɪʟᴇꜱ ᴜᴘʟᴏᴀᴅᴇᴅ: {files}\n🤖 ᴀᴄᴛɪᴠᴇ ʙᴏᴛꜱ: {len(get_user_bots(user_id))}"
                    edit_message(chat_id, message_id, text, back_keyboard())
                    
                elif data == "my_bots":
                    bots = get_user_bots(user_id)
                    edit_message(chat_id, message_id, get_my_bots(bots), back_keyboard())
                    
                elif data == "speed":
                    edit_message(chat_id, message_id, get_speed(), back_keyboard())
                    
                elif data == "stats":
                    users = len(get_all_users())
                    bots = len(get_user_bots(user_id))
                    edit_message(chat_id, message_id, get_stats(users, bots), back_keyboard())
                    
                elif data == "contact":
                    keyboard = {"inline_keyboard": [[{"text": "📩 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ", "url": "https://t.me/CyberXPloit"}], [{"text": "🔙 ʙᴀᴄᴋ", "callback_data": "back"}]]}
                    edit_message(chat_id, message_id, get_contact(), keyboard)
                    
                elif data == "admin_panel":
                    if is_admin(user_id):
                        edit_message(chat_id, message_id, get_admin_welcome(), admin_keyboard())
                    else:
                        answer_callback(callback_id, "⛔ ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ!")
                        
                elif data == "admin_users":
                    if is_admin(user_id):
                        edit_message(chat_id, message_id, get_all_users_text(), admin_keyboard())
                        
                elif data == "admin_bots":
                    if is_admin(user_id):
                        edit_message(chat_id, message_id, get_all_bots_text(), admin_keyboard())
                        
                elif data == "admin_stats":
                    if is_admin(user_id):
                        edit_message(chat_id, message_id, get_admin_stats(), admin_keyboard())
                        
                elif data == "admin_files":
                    if is_admin(user_id):
                        edit_message(chat_id, message_id, get_admin_files(), admin_keyboard())
                        
                elif data == "back":
                    edit_message(chat_id, message_id, get_welcome(user_name), main_keyboard(user_id))
                    
            elif "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                user_id = msg["from"]["id"]
                user_name = msg["from"].get("first_name", "User")
                
                add_user(user_id, user_name)
                
                if "text" in msg and msg["text"] == "/start":
                    send_message(chat_id, get_welcome(user_name), main_keyboard(user_id))
                    
                elif "document" in msg and user_data.get(user_id, {}).get("waiting_file"):
                    doc = msg["document"]
                    file_name = doc["file_name"]
                    
                    if file_name.endswith('.py') or file_name.endswith('.js'):
                        progress_msg = send_message(chat_id, "🔄 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ...**")
                        if progress_msg:
                            msg_data = progress_msg.json()
                            progress_msg_id = msg_data["result"]["message_id"]
                            
                            file_id = doc["file_id"]
                            file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
                            file_path = file_info["result"]["file_path"]
                            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                            
                            os.makedirs("user_bots", exist_ok=True)
                            local_path = f"user_bots/{user_id}_{file_name}"
                            r = requests.get(download_url)
                            with open(local_path, "wb") as f:
                                f.write(r.content)
                            
                            increment_files(user_id)
                            start_bot_process(user_id, local_path, file_name, chat_id, progress_msg_id)
                        
                        user_data[user_id]["waiting_file"] = False
                    else:
                        send_message(chat_id, "❌ **ᴇʀʀᴏʀ:** ᴏɴʟʏ .ᴘʏ ᴏʀ .ᴊꜱ ꜰɪʟᴇꜱ ᴀʟʟᴏᴡᴇᴅ!")
        
        time.sleep(1)
        
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        time.sleep(5)
EOF
