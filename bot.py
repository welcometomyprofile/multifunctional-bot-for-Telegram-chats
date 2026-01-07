import json
import os
import asyncio
import random
import re
import math
import textwrap
import requests
import numpy as np
from scipy.ndimage import map_coordinates
from datetime import datetime, time, timedelta

# --- EXTERNAL LIBRARIES ---
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont
from telegram import Update, BotCommand, InputMediaVideo, InputMediaPhoto, InputMediaAudio
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from yt_dlp import YoutubeDL
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import instaloader

# ================= CONFIGURATION =================

# 1. BOT TOKEN
BOT_TOKEN = "xxxxxxxxxxx"

# 2. Spotify Keys
SPOTIPY_CLIENT_ID = "xxxxxxxxxxx"
SPOTIPY_CLIENT_SECRET = "xxxxxxxxxxx"

# 3. Instagram Login
INSTAGRAM_LOGIN = 'xxxxxxxxxxx'       
INSTAGRAM_PASSWORD = 'xxxxxxxxxxx'

# 4. File Settings and Constants
LOG_FILE = "chat_log.txt"
FONT_FILE = "Arial.ttf"
TRIGGERS_FILE = "triggers.json"
xxxxxxxxxxx_ID = "xxxxxxxxxxx"
STATS_FILE = "casino_balances.json"
last_bet_messages = {}
IG_COOKIES_FILE = "cookies.txt"
UPLOAD_TIMEOUT = 3600
DARTS_TOURNAMENT_FILE = "darts_tournament.json"
DARTS_COST = 1000
last_darts_messages = {}


# Regex Patterns
MEDIA_REGEX = r'(https?://(?:www\.|m\.|vm\.|vt\.|music\.|www\.)?(?:tiktok\.com|instagram\.com|threads\.net|youtube\.com|youtu\.be|twitter\.com|x\.com)[^\s]+)'
SPOTIFY_REGEX = r'(https?://(?:open\.)?spotify\.com/track/[a-zA-Z0-9]+)'
INSTA_POST_REGEX = r'(https?:\/\/(?:www\.)?instagram\.com\/(?:p)\/([a-zA-Z0-9_-]+)\/?)'

ALIASES = {
    "@киев": "@kyiv", "@kiev": "@kyiv",
    "@beton": "@бетон",
}

WORKERS = [
    "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", 
    "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx", 
    "xxxxxxxxxxx", "xxxxxxxxxxx", "xxxxxxxxxxx"
]


# ================= SERVICES (INIT) =================

# --- Spotify ---
sp = None
if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET
        ))
        print("✅ Spotify API connected.")
    except Exception as e:
        print(f"❌ Spotify connection error: {e}")

# --- Instaloader ---
L = instaloader.Instaloader()
session_file_path = f"session-{INSTAGRAM_LOGIN}"

if INSTAGRAM_LOGIN and INSTAGRAM_PASSWORD:
    print(f"🔄 Instagram: Logging in as {INSTAGRAM_LOGIN}...")
    try:
        # Try to load session
        L.load_session_from_file(INSTAGRAM_LOGIN, filename=session_file_path)
        print("✅ Session restored.")
    except FileNotFoundError:
        try:
            # Login with password
            L.login(INSTAGRAM_LOGIN, INSTAGRAM_PASSWORD)
            L.save_session_to_file(filename=session_file_path)
            print("✅ Logged in, session saved.")
        except Exception as e:
            print(f"❌ Instagram login error: {e}")


# ================= UTILITIES AND HELPERS =================

def load_darts_tournament():
    if not os.path.exists(DARTS_TOURNAMENT_FILE): return {}
    try:
        with open(DARTS_TOURNAMENT_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_darts_tournament(data):
    with open(DARTS_TOURNAMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_num(n: int) -> str:
    """Formats number with spaces as thousand separators"""
    return f"{n:,}".replace(",", " ")

def load_stats():
    if not os.path.exists(STATS_FILE): return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f: 
            stats = json.load(f)
            if xxxxxxxxxxx_ID in stats:
                stats[xxxxxxxxxxx_ID]["score"] = 1488
            return stats
    except: return {}

def save_stats(stats):
    if xxxxxxxxxxx_ID in stats:
        stats[xxxxxxxxxxx_ID]["score"] = 1488
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def generate_markov_text():
    if not os.path.exists(LOG_FILE):
        return "Dictionary is empty."
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_words = []
            for line in f:
                words = line.strip().split()
                all_words.extend(words)
        
        if not all_words:
            return "Dictionary is empty."
        
        max_length = min(30, len(all_words))
        target_length = random.randint(1, max_length)

        result_words = random.choices(all_words, k=target_length)

        random.shuffle(result_words)
        
        return " ".join(result_words).capitalize()
    except Exception as e:
        return f"Generation error: {e}"

def swap_layout(text: str) -> str:
    en = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"
    ru = "йцукенгшщзхъфывапролджэячсмитьбю."
    enU, ruU = en.upper(), ru.upper()
    out = []
    for ch in text:
        if ch in en: out.append(ru[en.index(ch)])
        elif ch in enU: out.append(ruU[enU.index(ch)])
        elif ch in ru: out.append(en[ru.index(ch)])
        elif ch in ruU: out.append(enU[ruU.index(ch)])
        else: out.append(ch)
    return "".join(out)

def load_triggers() -> dict:
    if not os.path.exists(TRIGGERS_FILE): return {}
    try:
        with open(TRIGGERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_triggers(triggers: dict) -> None:
    with open(TRIGGERS_FILE, "w", encoding="utf-8") as f:
        json.dump(triggers, f, ensure_ascii=False, indent=2)

def get_andre_bday_message() -> str:
    now = datetime.now()
    target_date = datetime(now.year, 8, 30)
    
    if target_date < now: 
        target_date = datetime(now.year + 1, 8, 30)
    
    delta = target_date - now
    days = delta.days
    hours = int(delta.total_seconds() // 3600)
    months = round(days / 30.44, 1)
    
    return (
        f"Time until Andre's B-day: {days} days, "
        f"or {months} months, "
        f"or {hours} hours."
    )

TRIGGERS = load_triggers()


# ================= IMAGE PROCESSING =================

def get_casino_rules():
    return (
        "CASINO RULES\n\n"
        "1. Earnings: +2 points for every message in the chat.\n"
        "2. Bonus: command /bonus.\n"
        "3. Game: command /bet [amount] (minimum bet 10).\n\n"
        "Winning combinations:\n"
        "🔥 777 (Jackpot) — x10\n"
        "🎉 Three in a row — x4\n"
        "✅ Two identical — x2\n"
        "🌚 Nothing matches — bet lost.\n\n"
        "Commands: /bal — balance, /top — leaders, /send — transfer points."
    )

def create_quote_image(text: str, name: str, user_photo_path: str = None) -> str:
    width, height = 1200, 600
    bg_color = (20, 20, 20)
    text_color = (255, 255, 255)
    name_color = (150, 150, 150)
    
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_size = 55
        font_main = ImageFont.truetype(FONT_FILE, font_size)
        font_author = ImageFont.truetype(FONT_FILE, 40)
    except:
        font_main = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_size = 40 # Fallback

    # Avatar
    avatar_size = 400
    avatar_x = 50
    avatar_y = (height - avatar_size) // 2
    
    if user_photo_path and os.path.exists(user_photo_path):
        try:
            avatar = Image.open(user_photo_path).convert("RGBA")
            avatar = ImageOps.fit(avatar, (avatar_size, avatar_size), centering=(0.5, 0.5))
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            draw.ellipse((avatar_x-5, avatar_y-5, avatar_x + avatar_size + 5, avatar_y + avatar_size + 5), fill=(255, 255, 255))
            img.paste(avatar, (avatar_x, avatar_y), mask)
        except Exception:
            draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=(50, 50, 50))
    else:
        draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=(50, 50, 50))

    # Text
    text_x = 500
    text_max_width = 650
    full_text = f"«{text}»"
    
    avg_char_width = 28 
    chars_per_line = int(text_max_width / avg_char_width)
    lines = textwrap.wrap(full_text, width=chars_per_line)
    
    line_height = font_size + 15
    text_height_total = len(lines) * line_height
    current_y = (height - text_height_total) // 2 - 30
    if current_y < 50: current_y = 50

    for line in lines:
        draw.text((text_x, current_y), line, font=font_main, fill=text_color)
        current_y += line_height

    draw.text((text_x + 50, current_y + 20), f"— {name}", font=font_author, fill=name_color)

    out_path = f"quote_{random.randint(1000, 9999)}.jpg"
    img.save(out_path, quality=95)
    return out_path


def make_liquid_image(image_path: str) -> str | None:
    try:
        img = Image.open(image_path).convert("RGB")
        # Limit size for speed
        img.thumbnail((600, 600))
        data = np.array(img)
        h, w, c = data.shape

        # Create coordinate grid
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)

        # "Wild distortion" effect (like DistortBot)
        # We create 3-5 zones of strong compression/stretching
        for _ in range(random.randint(3, 5)):
            # Random "collapse" center point
            cx, cy = random.randint(0, w), random.randint(0, h)
            # Distortion strength
            strength = random.uniform(0.4, 0.8)
            # Scale (how large the distorted spot is)
            scale = random.uniform(100, 250)

            dx = x - cx
            dy = y - cy
            dist_sq = dx**2 + dy**2
            
            # Lens formula that "flattens" space
            mask = np.exp(-dist_sq / (2 * scale**2))
            
            x -= dx * mask * strength
            y -= dy * mask * strength

        # Apply coordinates (interpolation)
        distorted = np.zeros_like(data)
        for i in range(c):
            distorted[..., i] = map_coordinates(data[..., i], [y, x], order=1)

        final_img = Image.fromarray(distorted)
        
        # Final touches for memeness: contrast and sharpness
        final_img = ImageEnhance.Contrast(final_img).enhance(1.3)
        final_img = ImageEnhance.Sharpness(final_img).enhance(1.5)
        
        out_path = f"{image_path}_distort.jpg"
        final_img.save(out_path, quality=90)
        return out_path
    except Exception as e:
        print(f"Distort Error: {e}")
        return None
    
def make_kek_image(image_path: str) -> str | None:
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        left_half = img.crop((0, 0, w // 2, h))
        new_img = Image.new("RGB", (w, h))
        new_img.paste(left_half, (0, 0))
        new_img.paste(ImageOps.mirror(left_half), (w // 2, 0))
        out_path = f"{image_path}_kek.jpg"
        new_img.save(out_path, quality=90)
        return out_path
    except: return None

def make_kuk_image(image_path: str) -> str | None:
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        top_half = img.crop((0, 0, w, h // 2))
        new_img = Image.new("RGB", (w, h))
        new_img.paste(top_half, (0, 0))
        new_img.paste(ImageOps.flip(top_half), (0, h // 2))
        out_path = f"{image_path}_kuk.jpg"
        new_img.save(out_path, quality=90)
        return out_path
    except: return None


# ================= DOWNLOADERS =================

def get_spotify_track_info(url: str) -> str | None:
    if not sp: return None
    try:
        track = sp.track(url)
        return f"{track['artists'][0]['name']} - {track['name']}"
    except Exception as e:
        print(f"❌ SPOTIFY API ERROR: {e}") 
        return None

def download_instagram_smart(url: str) -> dict | None:
    try:
        match = re.search(INSTA_POST_REGEX, url)
        if not match: return None
        
        shortcode = match.group(2)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        if post.is_video and post.typename != 'GraphSidecar': return None

        files, types = [], []
        base_name = f"insta_{shortcode}_{random.randint(1000,9999)}"

        def download_url_to_file(img_url, suffix):
            try:
                r = requests.get(img_url)
                if r.status_code == 200:
                    fname = f"{base_name}_{suffix}.jpg"
                    with open(fname, 'wb') as f: f.write(r.content)
                    return os.path.abspath(fname)
            except: pass
            return None

        if post.typename == 'GraphSidecar':
            i = 0
            for node in post.get_sidecar_nodes():
                if not node.is_video:
                    f_path = download_url_to_file(node.display_url, i)
                    if f_path:
                        files.append(f_path)
                        types.append("photo")
                        i += 1
        elif post.typename == 'GraphImage':
            f_path = download_url_to_file(post.url, 0)
            if f_path:
                files.append(f_path)
                types.append("photo")
        
        if not files: return None

        return {
            "files": files,
            "types": types,
            "caption": post.caption if post.caption else "", 
            "title": "Instagram Post"
        }
    except Exception as e:
        print(f"Instaloader Error: {e}")
        return None

def download_media(url: str, audio_only: bool = False, is_search: bool = False) -> dict | str | None:
    if not is_search and ("youtube.com" in url or "youtu.be" in url) and "music.youtube" not in url:
        try:
            with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                if duration > 180:
                    return "long_video_error"
        except Exception as e:
            print(f"Duration check error: {e}")

    def _detect_type(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]: return "photo"
        if ext in [".mp3", ".m4a", ".wav"]: return "audio"
        return "video"

    base_name = f"media_{random.randint(10000, 99999)}_{int(datetime.now().timestamp())}"
    cookie_path = IG_COOKIES_FILE if (IG_COOKIES_FILE and os.path.exists(IG_COOKIES_FILE)) else None
    
    # Determine if it is a video (for Instagram/Threads)
    is_video_content = True
    if "instagram.com" in url or "threads.net" in url:
        try:
            with YoutubeDL({"quiet": True, "cookiefile": cookie_path}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and (info.get('_type') == 'playlist' or info.get('vcodec') == 'none'):
                    is_video_content = False
        except: pass

    ydl_opts = {
        "outtmpl": f"{base_name}.%(ext)s",
        "quiet": True, 
        "no_warnings": True,
        "ignoreerrors": True, 
        "noplaylist": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    }
    if cookie_path: ydl_opts["cookiefile"] = cookie_path

    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    elif is_video_content:
        # Optimal choice for all platforms
        ydl_opts["format"] = "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best"
        ydl_opts["merge_output_format"] = "mp4"
        
        # Only the most necessary compatibility parameters
        ydl_opts["postprocessor_args"] = [
            "-c:v", "libx264", 
            "-pix_fmt", "yuv420p", 
            "-preset", "ultrafast",
            "-c:a", "aac", 
            "-movflags", "+faststart"
        ]
    else:
        ydl_opts["format"] = "best"

    target_url = f"ytsearch1:{url}" if is_search else url
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if not info: return None
            
            # Look for the final file (after merging video and audio)
            files = sorted([
                os.path.abspath(f) for f in os.listdir() 
                if f.startswith(base_name) and os.path.getsize(f) > 0
            ])
            if not files: return None

            # If yt-dlp didn't change the extension, force .mp4 for video
            final_files = []
            for f in files:
                if _detect_type(f) == "video" and not f.endswith(".mp4"):
                    new_path = f.rsplit('.', 1)[0] + ".mp4"
                    os.rename(f, new_path)
                    final_files.append(new_path)
                else:
                    final_files.append(f)

            caption = info.get('description') or info.get('title') or ""
            return {
                "files": final_files, 
                "types": [_detect_type(f) for f in final_files], 
                "title": info.get('title', 'Media'), 
                "caption": caption
            }
    except Exception as e:
        print(f"DL Error: {e}")
        return None


# ================= COMMAND HANDLERS =================
async def daily_darts_reset(context: ContextTypes.DEFAULT_TYPE):
    tournament = load_darts_tournament()
    if not tournament:
        return

    # Sort winners
    sorted_top = sorted(tournament.items(), key=lambda x: x[1]['score'], reverse=True)
    stats = load_stats()
    rewards = [1000000, 500000, 300000]
    
    announcement = "<b>🏁 DARTS TOURNAMENT RESULTS!</b>\n\n"
    
    for i, (uid, data) in enumerate(sorted_top[:3]):
        prize = rewards[i]
        if uid in stats:
            stats[uid]["score"] += prize
        announcement += f"{['🥇', '🥈', '🥉'][i]} {data['name']} receives +{format_num(prize)} points!\n"
    
    save_stats(stats)
    save_darts_tournament({}) # Full reset for the next day
    
    # Send message to chat (Set chat ID if needed, otherwise it's logged)
    # await context.bot.send_message(chat_id="YOUR_CHAT_ID", text=announcement, parse_mode="HTML")

async def darts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name
    stats = load_stats()

    # --- CHAT CLEANUP (Like casino) ---
    if user_id in last_darts_messages:
        for msg_id in last_darts_messages[user_id]:
            try: await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except: pass
    last_darts_messages[user_id] = []

    try: await update.message.delete()
    except: pass

    # Check balance
    if user_id not in stats or stats[user_id]["score"] < DARTS_COST:
        msg = await update.effective_chat.send_message(f"❌ {name}, you need {format_num(DARTS_COST)} points to throw!")
        last_darts_messages[user_id].append(msg.message_id)
        return

    # Deduct points
    stats[user_id]["score"] -= DARTS_COST
    save_stats(stats)

    # Throw dart
    dice_msg = await update.effective_chat.send_dice(emoji='🎯')
    last_darts_messages[user_id].append(dice_msg.message_id)
    
    # Score map: 1 - miss, 6 - bullseye
    score_map = {1: 0, 2: 100, 3: 200, 4: 500, 5: 1000, 6: 2500}
    points = score_map[dice_msg.dice.value]

    # Record in tournament table
    tournament = load_darts_tournament()
    if user_id not in tournament:
        tournament[user_id] = {"name": name, "score": 0}
    
    tournament[user_id]["score"] += points
    save_darts_tournament(tournament)

    await asyncio.sleep(3.5)
    
    res_text = "🎯 Miss! 0 points." if points == 0 else f"🎯 Nice shot! +{points} points to tournament."
    
    result_msg = await update.effective_chat.send_message(
        f"👤 {name}\n"
        f"📊 Result: {res_text}\n"
        f"🏆 Total tournament score: `{format_num(tournament[user_id]['score'])}`"
    )
    last_darts_messages[user_id].append(result_msg.message_id)

async def darts_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tournament = load_darts_tournament()
    if not tournament:
        return await update.message.reply_text("🏆 Tournament hasn't started yet. Be the first! Command: /darts")
    
    sorted_top = sorted(tournament.values(), key=lambda x: x['score'], reverse=True)[:10]
    text = "<b>🏆 DARTS RATING (24h):</b>\n\n"
    for i, user in enumerate(sorted_top, 1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        text += f"{medal} {user['name']} — <code>{format_num(user['score'])}</code> points\n"
    
    text += f"\n💰 Cost per throw: {format_num(DARTS_COST)} points\n🏁 Results summary at 12:00"
    await update.message.reply_text(text, parse_mode="HTML")


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = str(update.effective_user.id)
    name = update.effective_user.first_name
    stats = load_stats()

    # 1. Check for reply
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the person you want to send points to!")

    recipient = update.message.reply_to_message.from_user
    recipient_id = str(recipient.id)
    recipient_name = recipient.first_name

    # IMPROVEMENT 1: Ban topping up BetonBot (ID: 7955961094)
    if recipient_id == "7955961094":
        return await update.message.reply_text("🤖 Bot doesn't need points, keep them!")

    if sender_id == recipient_id:
        return await update.message.reply_text("🤔 Why send points to yourself?")

    # 2. Check amount
    try:
        if not context.args:
            raise ValueError
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await update.message.reply_text("⚠️ Specify the transfer amount in digits. Example: `/send 100`")

    # 3. Check sender balance
    if sender_id not in stats or stats[sender_id]["score"] < amount:
        return await update.message.reply_text(f"❌ {name}, you don't have enough points.")

    # Register recipient
    if recipient_id not in stats:
        stats[recipient_id] = {"name": recipient_name, "score": 100}

    # Execute transfer
    stats[sender_id]["score"] -= amount
    stats[recipient_id]["score"] += amount
    save_stats(stats)

    await update.message.reply_text(f"💸 **{name}** transferred `{format_num(amount)}` points to **{recipient_name}**!", parse_mode="Markdown")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.effective_user.first_name
    stats = load_stats()

    if user_id not in stats:
        stats[user_id] = {"name": name, "score": 100}
        save_stats(stats)

    balance = stats[user_id]["score"]
    await update.message.reply_text(f"{name}, your balance: {format_num(balance)} points")

async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.effective_user.first_name
    stats = load_stats()
    
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Check user registration
    if user_id not in stats:
        stats[user_id] = {"name": name, "score": 100, "last_bonus": ""}

    # Check if bonus already received today
    if stats[user_id].get("last_bonus") == today:
        # Calculate time until next midnight
        tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
        remaining = tomorrow - now
        
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return await update.message.reply_text(
            f"{name}, you already received your bonus today.\n"
            f"Next bonus available in: {hours}h {minutes}m"
        )

    # Award bonus
    bonus_amount = 100000
    stats[user_id]["score"] += bonus_amount
    stats[user_id]["last_bonus"] = today
    save_stats(stats)
    
    await update.message.reply_text(
        f"🎁 {name}, bonus awarded!\n"
        f"You received: +100 000 points\n"
        f"💰 Your balance is now: {format_num(stats[user_id]['score'])}"
    )

async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name
    stats = load_stats()

    # --- 1. CHAT CLEANUP ---
    if user_id in last_bet_messages:
        for msg_id in last_bet_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except: pass
    last_bet_messages[user_id] = []

    try:
        await update.message.delete()
    except: pass

    # --- 2. CHECK REGISTRATION ---
    if user_id not in stats:
        stats[user_id] = {"name": name, "score": 100}
    
    current_score = stats[user_id]["score"]

    # --- 3. BET LOGIC (DEFAULT 10) ---
    if not context.args:
        bet = 10
    else:
        arg = context.args[0].lower()
        if arg == "all":
            bet = current_score
        elif arg == "half":
            bet = current_score // 2
        else:
            try:
                bet = int(arg)
            except ValueError:
                msg = await update.effective_chat.send_message(f"⚠️ {name}, specify amount in digits or `/bet all`")
                last_bet_messages[user_id].append(msg.message_id)
                return

    # --- 4. CHECK LIMITS ---
    if bet <= 0:
        msg = await update.effective_chat.send_message(f"⚠️ {name}, bet must be greater than 0")
        last_bet_messages[user_id].append(msg.message_id)
        return

    if bet > current_score:
        msg = await update.effective_chat.send_message(
            f"❌ {name}, not enough points!\nYour balance: `{current_score}`", 
            parse_mode="Markdown"
        )
        last_bet_messages[user_id].append(msg.message_id)
        return

    # --- 5. GAME ---
    stats[user_id]["score"] -= bet
    save_stats(stats)

    dice_msg = await update.effective_chat.send_dice(emoji='🎰')
    last_bet_messages[user_id].append(dice_msg.message_id)
    
    # Calculate reels
    res = dice_msg.dice.value - 1
    reels = [res % 4, (res // 4) % 4, res // 16]
    
    win_multiplier = 0
    if reels[0] == reels[1] == reels[2]:
        win_multiplier = 10 if reels[0] == 3 else 4
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        win_multiplier = 2
    
    if win_multiplier > 0:
        win_amount = int(bet * win_multiplier)
        stats[user_id]["score"] += win_amount
        res_text = f"✅ Win: +{format_num(win_amount)}!"
    else:
        res_text = f"🌚 Loss. Minus {format_num(bet)}."

    save_stats(stats)
    await asyncio.sleep(2.5)
    
    # UPDATED MESSAGE (added bet amount)
    result_msg = await update.effective_chat.send_message(
        f"👤 {name}\n"
        f"🎰 Bet: `{format_num(bet)}`\n"
        f"📊 Result: {res_text}\n"
        f"💰 Balance: `{format_num(stats[user_id]['score'])}`",
        parse_mode="Markdown"
    )
    last_bet_messages[user_id].append(result_msg.message_id)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_stats()
    if not stats: return await update.message.reply_text("Casino is empty yet!")
    
    sorted_users = sorted(stats.values(), key=lambda x: x['score'], reverse=True)[:10]
    text = "<b>💎 RICHEST PLAYERS:</b>\n\n"
    for i, user in enumerate(sorted_users, 1):
        text += f"{i}. {user['name']} — <code>{format_num(user['score'])}</code>\n"
    
    await update.message.reply_text(text, parse_mode="HTML")

async def markov_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = generate_markov_text()
    await update.message.reply_text(text)

async def swap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    src = update.message.reply_to_message.text if (update.message.reply_to_message and update.message.reply_to_message.text) else " ".join(context.args)
    if not src: return await update.message.reply_text("Reply with /swap to a message.")
    await update.message.reply_text(swap_layout(src))

async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"My choice fell on: {random.choice(WORKERS)}")

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args_text = " ".join(context.args).strip()
    reply = update.message.reply_to_message
    
    if args_text:
        text, target_user = args_text, update.message.from_user
    elif reply and (reply.text or reply.caption):
        text, target_user = (reply.text or reply.caption), reply.from_user
    else:
        return await update.message.reply_text("Usage: `/quote text` or reply.")

    status_msg = await update.message.reply_text("🎨 Painting...")
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

    avatar_path = None
    try:
        photos = await target_user.get_profile_photos(limit=1)
        if photos.total_count > 0:
            avatar_path = f"avatar_{target_user.id}.jpg"
            await (await photos.photos[0][-1].get_file()).download_to_drive(avatar_path)

        # Truncate text
        text = text[:200] + "..." if len(text) > 200 else text
        
        quote_file = await asyncio.to_thread(create_quote_image, text, target_user.full_name, avatar_path)

        if quote_file:
            await update.message.reply_photo(photo=open(quote_file, "rb"))
            os.remove(quote_file)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Generation error.")

        if avatar_path and os.path.exists(avatar_path): os.remove(avatar_path)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")

async def run_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd_type: str):
    target_msg = update.message.reply_to_message if update.message.reply_to_message else update.message
    
    # Check if media exists
    photo = target_msg.photo[-1] if target_msg.photo else None
    if not photo and target_msg.document and "image" in str(target_msg.document.mime_type):
        photo = target_msg.document
    
    if not photo:
        return await update.message.reply_text("Send a photo with caption or reply to a photo.")

    status_msg = await update.message.reply_text("⏳ Processing...")
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

    file_name = f"temp_{cmd_type}_{random.randint(1000,9999)}.jpg"
    try:
        await (await photo.get_file()).download_to_drive(file_name)
        
        func_map = {'liq': make_liquid_image, 'kek': make_kek_image, 'kuk': make_kuk_image}
        res = await asyncio.to_thread(func_map[cmd_type], file_name)

        if res and os.path.exists(res):
            await update.message.reply_photo(photo=open(res, "rb"))
            os.remove(res)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Processing error.")
    except Exception as e:
        await status_msg.edit_text("❌ Error.")
    finally:
        if os.path.exists(file_name): os.remove(file_name)

async def liq_command(u, c): await run_image_command(u, c, 'liq')
async def kek_command(u, c): await run_image_command(u, c, 'kek')
async def kuk_command(u, c): await run_image_command(u, c, 'kuk')

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a message and type: /add <trigger>")
    
    key = " ".join(context.args).strip().lower()
    reply = update.message.reply_to_message
    trigger_data = {}

    # Determine content type
    if reply.text:
        trigger_data = {"type": "text", "content": reply.text.strip()}
    elif reply.photo:
        trigger_data = {"type": "photo", "content": reply.photo[-1].file_id, "caption": reply.caption}
    elif reply.video:
        trigger_data = {"type": "video", "content": reply.video.file_id, "caption": reply.caption}
    elif reply.animation: # GIFs
        trigger_data = {"type": "animation", "content": reply.animation.file_id, "caption": reply.caption}
    elif reply.audio: # Audio files
        trigger_data = {"type": "audio", "content": reply.audio.file_id, "caption": reply.caption}
    elif reply.voice: # Voice messages
        trigger_data = {"type": "voice", "content": reply.voice.file_id}
    else:
        return await update.message.reply_text("❌ This media type is not supported yet.")

    TRIGGERS.setdefault(key, [])
    
    # Check for duplicates
    if trigger_data not in TRIGGERS[key]:
        TRIGGERS[key].append(trigger_data)
        save_triggers(TRIGGERS)
        await update.message.reply_text(f"✅ Saved as {trigger_data['type']} for trigger '{key}'")
    else:
        await update.message.reply_text("Element already exists in this trigger.")

async def del_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    key = " ".join(context.args).strip().lower()
    if key in TRIGGERS:
        del TRIGGERS[key]
        save_triggers(TRIGGERS)
        await update.message.reply_text(f"Deleted '{key}'")

async def tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\n".join(["Triggers:"] + list(TRIGGERS.keys())) if TRIGGERS else "Empty")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "**BetonBot**\n\n"
        "🎞 **Media:** TikTok, Insta, YouTube, Spotify\n"
        "🎨 **Image FX:** `/liq`, `/kek`, `/kuk`\n"
        "🛠 **Tools:** `/add`, `/del`, `/tags`, `/swap`, `/random`, `/quote`"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")


# ================= MAIN LOGIC ROUTER =================

def clean_hashtags(text: str) -> str:
    if not text: return ""
    # Remove hashtags and extra spaces
    cleaned = re.sub(r'#\w+', '', text)
    return cleaned.strip()

async def reply_on_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get message
    message = update.message
    if not message: return
    
    # Get text
    text = message.text or message.caption or ""
    if not text: return
    
    text_strip = text.strip()
    text_lower = text_strip.lower()

    # First determine user name for all logs and games
    user = message.from_user
    name = user.first_name if user.first_name else (user.last_name if user.last_name else user.username)
    if not name: name = "Anonymous"

    user_id = user.id
    bot_id = context.bot.id

    # 1. Save logic for /markov AND point scoring
    if not text_strip.startswith('/') and user_id != bot_id:
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        tag_pattern = r'@[^\s]+'
        
        # If it's a normal message (not a link and not a tag)
        if not re.search(url_pattern, text_strip) and not re.search(tag_pattern, text_strip):
            # Write to log for markov
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{name}: {text_strip}\n")
            
            # --- POINT EARNING SYSTEM ---
            stats = load_stats()
            u_id_str = str(user_id)
            
            if u_id_str not in stats:
                # Give starting capital to new player
                stats[u_id_str] = {"name": name, "score": 100}
            
            # Add 2 points for every message
            stats[u_id_str]["score"] += 2
            save_stats(stats)
            # -------------------------------

    # 2. Reply to saveasbot (Context specific: Traitor/Betrayal)
    if "saveasbot" in text_lower:
        await message.reply_text("Traitor bot!")

    # 3. Handle media links (TikTok, Insta, YouTube, etc.)
    is_spotify = re.search(SPOTIFY_REGEX, text)
    is_media = re.search(MEDIA_REGEX, text)

    if is_spotify or is_media:  
        status = await update.effective_chat.send_message("👀 Downloading...")
        res = None
        
        try:
            url = (is_spotify.group(0) if is_spotify else is_media.group(0))
            is_insta_post = "instagram.com" in url and "/p/" in url
            is_threads_post = "threads.net" in url
            
            if is_spotify:
                query = await asyncio.to_thread(get_spotify_track_info, url)
                if query:
                    res = await asyncio.to_thread(download_media, query, True, True)
            else:
                is_audio = "music.youtube" in url or any(word in text.lower() for word in ["mp3", "audio"])
                if is_insta_post:
                    res = await asyncio.to_thread(download_instagram_smart, url)
                if not res:
                    res = await asyncio.to_thread(download_media, url, is_audio, False)

            if res and isinstance(res, dict):
                if is_spotify or (is_media and is_audio):
                    type_word = "music"
                elif is_threads_post or (is_insta_post and "photo" in res['types']):
                    type_word = "post"
                else:
                    type_word = "video"

                link_part = f"{name} shared <a href='{url}'>{type_word}</a>"
                
                if (is_insta_post or is_threads_post) and res.get('caption'):
                    cleaned_text = clean_hashtags(res['caption'])
                    final_caption = f"{link_part}\n\nDescription:\n{cleaned_text}" if cleaned_text else link_part
                else:
                    final_caption = link_part

                files, types = res['files'], res['types']
                for i in range(0, len(files), 10):
                    chunk_files = files[i:i+10]
                    chunk_types = types[i:i+10]
                    
                    if len(chunk_files) > 1:
                        media_group = []
                        for j, (p, t) in enumerate(zip(chunk_files, chunk_types)):
                            cap = final_caption if (i == 0 and j == 0) else ""
                            if t == 'photo':
                                media_group.append(InputMediaPhoto(open(p, 'rb'), caption=cap, parse_mode='HTML'))
                            else:
                                media_group.append(InputMediaVideo(open(p, 'rb'), caption=cap, parse_mode='HTML'))
                        await update.effective_chat.send_media_group(media=media_group, write_timeout=UPLOAD_TIMEOUT)
                    else:
                        f, t = chunk_files[0], chunk_types[0]
                        with open(f, 'rb') as f_data:
                            if t == 'audio': 
                                await update.effective_chat.send_audio(audio=f_data, caption=final_caption, parse_mode='HTML', write_timeout=UPLOAD_TIMEOUT)
                            elif t == 'photo': 
                                await update.effective_chat.send_photo(photo=f_data, caption=final_caption, parse_mode='HTML')
                            else: 
                                await update.effective_chat.send_video(video=f_data, caption=final_caption, parse_mode='HTML', write_timeout=UPLOAD_TIMEOUT)
                
            elif res == "long_video_error":
                await status.edit_text("❌ Video is longer than 3 minutes.")
            else:
                await status.edit_text("❌ Failed to download.")

        except Exception as e:
            print(f"General Error: {e}")
            try:
                await status.edit_text("❌ Error during processing.")
            except: pass

        finally:
            # 1. Delete status "Downloading..."
            try: await status.delete()
            except: pass

            # 2. Delete link ONLY on success
            if res and isinstance(res, dict):
                try: await message.delete()
                except: pass

            # 3. Clean up files
            if res and isinstance(res, dict) and 'files' in res:
                for p in res['files']:
                    if os.path.exists(p):
                        try: os.remove(p)
                        except: pass



    # --- 3. TEXT TRIGGERS ---
    text_lower = text.lower()
    normalized = " ".join(text_lower.split())

    # Andre's B-day
    has_andre = "andre" in normalized
    has_25 = "25" in normalized
    bday_triggers = ["andre bday", "andre birthday", "bday andre"]
    
    if (has_andre and has_25) or any(phrase in normalized for phrase in bday_triggers):
        await update.effective_chat.send_message(get_andre_bday_message())
        return
    
    # Check for "casino rules" trigger
    if "casino rules" in normalized:
        await update.effective_chat.send_message(get_casino_rules())
        return
    


    # Custom triggers from JSON
    key = ALIASES.get(normalized, normalized)
    if key in TRIGGERS:
        all_items = TRIGGERS[key]
        # Process trigger items in batches of 4
        for i in range(0, len(all_items), 4):
            chunk = all_items[i:i+4]
            reply_id = message.message_id
            
            # Collect all text messages from this batch into one
            texts_to_send = []
            
            for item in chunk:
                try:
                    # If it's just a string (old format)
                    if isinstance(item, str):
                        texts_to_send.append(item)
                    
                    # If it's a dictionary (new format)
                    elif isinstance(item, dict):
                        t_type = item.get("type")
                        content = item.get("content")
                        caption = item.get("caption", "")

                        if t_type == "text":
                            texts_to_send.append(content)
                        elif t_type == "photo":
                            await update.effective_chat.send_photo(photo=content, caption=caption, reply_to_message_id=reply_id)
                        elif t_type == "video":
                            await update.effective_chat.send_video(video=content, caption=caption, reply_to_message_id=reply_id)
                        elif t_type == "animation":
                            await update.effective_chat.send_animation(animation=content, caption=caption, reply_to_message_id=reply_id)
                        elif t_type == "audio":
                            await update.effective_chat.send_audio(audio=content, caption=caption, reply_to_message_id=reply_id)
                        elif t_type == "voice":
                            await update.effective_chat.send_voice(voice=content, reply_to_message_id=reply_id)
                
                except Exception as e:
                    print(f"Error sending item: {e}")

            # If there were text elements in the batch, send them as one message (reply)
            if texts_to_send:
                combined_text = "\n".join(texts_to_send)
                await update.effective_chat.send_message(combined_text, reply_to_message_id=reply_id)
            
            # Short pause between batches
            await asyncio.sleep(0.15)


# ================= BOT STARTUP =================

async def post_init(app: Application):
    """Set commands in the bot menu"""
    await app.bot.set_my_commands([
        BotCommand("bet", "make a bet"),
        BotCommand("bal", "my balance"),
        BotCommand("bonus", "daily bonus"),
        BotCommand("top", "list of rich players"),
        BotCommand("darts", "play darts"),
        BotCommand("dtop", "darts top players"),
        BotCommand("markov", "chat summary"),
        BotCommand("liq", "liquidate image"),
        BotCommand("kek", "mirror vertical"),
        BotCommand("kuk", "mirror horizontal"),
        BotCommand("add", "add trigger"),
        BotCommand("del", "delete trigger"),
        BotCommand("help", "help"),
        BotCommand("swap", "fix keyboard layout"),
        BotCommand("quote", "make a quote"),
        BotCommand("random", "roulette")
   ])

def main():
    print("🚀 Bot starting...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Register commands
    app.add_handler(CommandHandler("bet", bet_command))
    app.add_handler(CommandHandler("bal", balance_command))
    app.add_handler(CommandHandler("bonus", bonus_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("darts", darts_command))
    app.add_handler(CommandHandler("dtop", darts_top_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("del", del_command))
    app.add_handler(CommandHandler("tags", tags_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("random", question_command))
    app.add_handler(CommandHandler("swap", swap_command))
    app.add_handler(CommandHandler("quote", quote_command))
    app.add_handler(CommandHandler("send", send_command))
    
    # Register image processing commands
    app.add_handler(CommandHandler("liq", liq_command))
    app.add_handler(CommandHandler("kek", kek_command))
    app.add_handler(CommandHandler("kuk", kuk_command))
    
    # Text handler (triggers, links)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply_on_trigger))
    app.add_handler(CommandHandler("markov", markov_command))

    print("✅ Bot started! Polling...")
    
    # Timer setup for 12:00 daily
    # UTC time (if server is in Europe, 12:00 Kyiv is approx 10:00 UTC)
    app.job_queue.run_daily(daily_darts_reset, time=time(hour=10, minute=0))

    app.run_polling()

if __name__ == "__main__":
    main()
