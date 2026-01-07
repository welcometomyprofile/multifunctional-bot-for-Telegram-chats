# 🤖 BetonBot

This is my personal bot that my friends and I use for various functions in our correspondence. The first and main idea was to download videos from links that are sent to the chat from various resources and are often not opened. The bot immediately sends the video or post via the link to the chat.
A multifunctional entertainment and utility bot for Telegram chats, built with Python. It combines a media downloader, a meme generator, and a mini-casino system.

## 🚀 Key Features

### 📥 Media Downloader
Automatically detects links and downloads content directly to the chat:
* **TikTok / Instagram (Reels, Posts, Stories)** — without watermarks.
* **YouTube** — video and audio downloads.
* **Spotify** — track info and preview/metadata.
* **Threads** — media handling.

### 💰 Economy & Games
Built-in points system (JSON-based persistence):
* **Earning:** +2 points for every chat message, daily rewards via `/bonus`.
* **Casino:** Slots (`/bet`) with x2, x4, and x10 multipliers.
* **Darts:** Daily tournaments (`/darts`) with a leaderboard (`/dtop`) and prize pool.
* **Transfers:** Send points to other users via `/send`.

### 🎨 Image Processing (Meme Maker)
Commands for on-the-fly image manipulation:
* `/quote` — Generates a quote image from a user's message (includes avatar).
* `/liq` — "Liquid" distortion effect (content-aware scaling).
* `/kek` — Mirror effect (Left-Right).
* `/kuk` — Mirror effect (Top-Bottom).

### 🛠 Utilities & Triggers
* **Custom Triggers:** Add reactions (text/photo/gif/voice) to specific phrases using `/add` and `/del`.
* **Markov Chain:** Generates random text based on chat history (`/markov`).
* **Layout Fix:** Switches text layout (QWERTY ↔ ЙЦУКЕН) via `/swap`.
* **Random:** Picks a random user from a predefined list (`/random`).

## ⚙️ Tech Stack
* **Python 3.10+**
* `python-telegram-bot` (v20+) — Async framework.
* `yt-dlp` — Media extraction engine.
* `Pillow (PIL)` — Image manipulation.
* `instaloader` & `spotipy` — API integrations.
* `numpy` & `scipy` — Advanced image distortion algorithms.
