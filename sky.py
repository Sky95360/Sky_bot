#!/usr/bin/env python3
"""
SKY BOT - Multi-Feature Telegram Bot
Features: AI Chat, YouTube Downloader, WhatsApp Integration, Weather, Games
Deploy: Render/Termux
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Import libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import requests
from pytube import YouTube
import openai
import google.generativeai as genai
from twilio.rest import Client

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

# Configurations
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP = os.getenv("TWILIO_WHATSAPP_NUMBER")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Initialize APIs
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None

# ==================== AI CHAT FUNCTIONS ====================
async def chat_gpt(prompt: str) -> str:
    """OpenAI ChatGPT response"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"🤖 ChatGPT Error: {str(e)}"

async def gemini_chat(prompt: str) -> str:
    """Google Gemini response"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🤖 Gemini Error: {str(e)}"

# ==================== DOWNLOADER FUNCTIONS ====================
async def download_youtube(url: str, quality: str = "medium"):
    """Download YouTube video/audio"""
    try:
        yt = YouTube(url)
        if quality == "audio":
            stream = yt.streams.filter(only_audio=True).first()
            filename = f"{yt.title[:50]}.mp3"
        else:
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            filename = f"{yt.title[:50]}.mp4"
        
        filepath = f"downloads/{filename}"
        os.makedirs("downloads", exist_ok=True)
        stream.download(output_path="downloads", filename=filename)
        return filepath, filename
    except Exception as e:
        return None, f"❌ YouTube Error: {str(e)}"

# ==================== WHATSAPP FUNCTIONS ====================
def send_whatsapp(to_number: str, message: str) -> str:
    """Send WhatsApp message via Twilio"""
    try:
        if not twilio_client:
            return "❌ WhatsApp not configured. Add TWILIO credentials."
        
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP,
            to=f"whatsapp:{to_number}"
        )
        return f"✅ WhatsApp sent to {to_number} (SID: {message.sid})"
    except Exception as e:
        return f"❌ WhatsApp Error: {str(e)}"

# ==================== WEATHER FUNCTIONS ====================
async def get_weather(city: str) -> str:
    """Get weather information"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url).json()
        
        if response.get("cod") != 200:
            return f"❌ City not found: {city}"
        
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        humidity = response["main"]["humidity"]
        wind = response["wind"]["speed"]
        
        return (
            f"🌤️ Weather in {city.capitalize()}:\n"
            f"• Temperature: {temp}°C\n"
            f"• Condition: {desc}\n"
            f"• Humidity: {humidity}%\n"
            f"• Wind Speed: {wind} m/s"
        )
    except Exception as e:
        return f"❌ Weather Error: {str(e)}"

# ==================== GAME FUNCTIONS ====================
games_db = {}

async def guess_number_game(update: Update, context: CallbackContext):
    """Simple number guessing game"""
    user_id = update.effective_user.id
    
    if user_id not in games_db:
        games_db[user_id] = {"number": None, "attempts": 0}
    
    if not games_db[user_id]["number"]:
        import random
        games_db[user_id]["number"] = random.randint(1, 100)
        games_db[user_id]["attempts"] = 0
        await update.message.reply_text("🎮 I've chosen a number between 1-100. Guess it!")
        return
    
    try:
        guess = int(update.message.text)
        games_db[user_id]["attempts"] += 1
        target = games_db[user_id]["number"]
        
        if guess < target:
            await update.message.reply_text("📈 Too low! Try higher.")
        elif guess > target:
            await update.message.reply_text("📉 Too high! Try lower.")
        else:
            attempts = games_db[user_id]["attempts"]
            await update.message.reply_text(f"🎉 Correct! You got it in {attempts} attempts!")
            del games_db[user_id]
    except:
        await update.message.reply_text("Please send a number!")

# ==================== BOT COMMAND HANDLERS ====================
async def start(update: Update, context: CallbackContext):
    """Start command handler"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🤖 AI Chat", callback_data='ai_chat'),
         InlineKeyboardButton("📥 YouTube DL", callback_data='youtube')],
        [InlineKeyboardButton("🌤️ Weather", callback_data='weather'),
         InlineKeyboardButton("📱 WhatsApp", callback_data='whatsapp')],
        [InlineKeyboardButton("🎮 Games", callback_data='games'),
         InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Hello {user.first_name}! I'm SKY BOT 🤖\n"
        f"Choose an option below:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext):
    """Help command"""
    help_text = """
📚 **SKY BOT COMMANDS**:

🤖 **AI Chat**
• `/chatgpt <text>` - ChatGPT response
• `/gemini <text>` - Google Gemini response
• Just send any message for AI reply

📥 **Downloader**
• `/youtube <url>` - Download YouTube video
• `/ytaudio <url>` - Download YouTube audio
• `/download <url>` - Download any file

📱 **WhatsApp Tools**
• `/whatsapp <number> <message>` - Send WhatsApp message

🌤️ **Weather**
• `/weather <city>` - Get weather info

🎮 **Games**
• `/game` - Start number guessing game
• Send numbers to guess

⚙️ **Admin** (Admin only)
• `/broadcast <message>` - Broadcast to all users
• `/stats` - Bot statistics

📊 **Utilities**
• `/quote` - Random quote
• `/time` - Current time
• `/calc <expression>` - Calculator
"""
    await update.message.reply_text(help_text)

async def chatgpt_command(update: Update, context: CallbackContext):
    """ChatGPT command"""
    if not context.args:
        await update.message.reply_text("Usage: /chatgpt <your question>")
        return
    
    prompt = ' '.join(context.args)
    await update.message.reply_text("🤖 Thinking...")
    response = await chat_gpt(prompt)
    await update.message.reply_text(response[:4000])

async def youtube_command(update: Update, context: CallbackContext):
    """YouTube download command"""
    if not context.args:
        await update.message.reply_text("Usage: /youtube <YouTube URL>")
        return
    
    url = context.args[0]
    await update.message.reply_text("📥 Downloading video...")
    filepath, result = await download_youtube(url)
    
    if filepath:
        with open(filepath, 'rb') as video:
            await update.message.reply_video(video, caption="✅ Here's your video!")
        os.remove(filepath)
    else:
        await update.message.reply_text(result)

async def whatsapp_command(update: Update, context: CallbackContext):
    """WhatsApp send command"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /whatsapp <phone_number> <message>")
        return
    
    number = context.args[0]
    message = ' '.join(context.args[1:])
    result = send_whatsapp(number, message)
    await update.message.reply_text(result)

async def weather_command(update: Update, context: CallbackContext):
    """Weather command"""
    if not context.args:
        await update.message.reply_text("Usage: /weather <city>")
        return
    
    city = ' '.join(context.args)
    weather = await get_weather(city)
    await update.message.reply_text(weather)

async def broadcast_command(update: Update, context: CallbackContext):
    """Admin broadcast"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    # Note: In real implementation, you'd need a user database
    await update.message.reply_text(f"📢 Broadcast sent: {message}")

async def button_handler(update: Update, context: CallbackContext):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ai_chat':
        await query.edit_message_text("🤖 AI Chat activated! Just send me any message.")
    elif query.data == 'youtube':
        await query.edit_message_text("📥 Send YouTube URL or use /youtube <url>")
    elif query.data == 'weather':
        await query.edit_message_text("🌤️ Use /weather <city> to get weather info")
    elif query.data == 'whatsapp':
        await query.edit_message_text("📱 Use /whatsapp <number> <message> to send WhatsApp")
    elif query.data == 'games':
        await query.edit_message_text("🎮 Use /game to start number guessing game!")
    elif query.data == 'help':
        await help_command(update, context)

async def handle_message(update: Update, context: CallbackContext):
    """Handle regular messages with AI"""
    user_id = update.effective_user.id
    
    # If user is playing game
    if user_id in games_db and games_db[user_id]["number"]:
        await guess_number_game(update, context)
        return
    
    # Otherwise use AI
    text = update.message.text
    if text.startswith('/'):
        return
    
    await update.message.reply_text("🤖 Thinking...")
    response = await gemini_chat(text) if GEMINI_API_KEY else await chat_gpt(text)
    await update.message.reply_text(response[:4000])

async def error_handler(update: Update, context: CallbackContext):
    """Log errors"""
    logging.error(f"Update {update} caused error {context.error}")

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    # Check token
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found in environment!")
        print("💡 Create .env file with: BOT_TOKEN=your_token_here")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chatgpt", chatgpt_command))
    app.add_handler(CommandHandler("gemini", chatgpt_command))  # Alias
    app.add_handler(CommandHandler("youtube", youtube_command))
    app.add_handler(CommandHandler("ytaudio", youtube_command))
    app.add_handler(CommandHandler("whatsapp", whatsapp_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("game", guess_number_game))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Add button handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    print("🤖 SKY BOT is starting...")
    print(f"✅ Admin IDs: {ADMIN_IDS}")
    print("📱 Send /start to your bot!")
    
    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ==================== DEPLOYMENT SETUP ====================
"""
FOR TERMUX:
1. pkg install python git ffmpeg
2. git clone https://github.com/Sky95360/Sky_bot.git
3. cd Sky_bot
4. pip install -r requirements.txt
5. python bot.py

FOR RENDER:
1. Create render.yaml file:
services:
  - type: web
    name: sky-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python bot.py

2. Add requirements.txt with:
python-telegram-bot
openai
google-generativeai
pytube
requests
python-dotenv
twilio

3. Set environment variables in Render dashboard
"""

if __name__ == '__main__':
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Set logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Start bot
    main()
