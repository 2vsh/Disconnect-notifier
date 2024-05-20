import time
import discord
from discord.ext import commands, tasks
from PIL import Image
import mss
import pytesseract
import os

# Configuration
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Path to the Tesseract executable
DISCORD_ID = '795498713812434964'  # Discord ID to ping.  Replace placeholder as needed.
NOTIFY_LIMIT = 0  # Notification limit (0 to disable the limit)
AUTHORIZED_USERS = ['795498713812434964','673241652688584745']  # List of authorized user IDs for requesting screenshots. Replace placeholders as needed.
CHANNEL_ID = '[CHANNEL ID HERE]'  # Discord channel ID where the bot will send messages
BOT_TOKEN = '[BOT TOKEN HERE]'  # Your bot's token

# Initialize Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD_PATH

# Cooldown timestamp for sending screenshots on disconnect
disconnect_screenshot_cooldown = 0

# Create a Discord bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Counter for the number of notifications sent
notify_count = 0

# Function to send a message to a Discord channel
async def send_discord_message(channel, message):
    global notify_count
    await channel.send(f"<@{DISCORD_ID}> {message}")
    notify_count += 1

# Function to send a screenshot to a Discord channel
async def send_screenshot(channel):
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Assuming only one monitor
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        img.save("screenshot.png")

    await channel.send(file=discord.File("screenshot.png"))
    os.remove("screenshot.png")
    return 200

# Function to send a screenshot on disconnect with cooldown
async def send_disconnect_screenshot(channel):
    global disconnect_screenshot_cooldown
    if time.time() < disconnect_screenshot_cooldown:
        return 429  # Too Many Requests
    status = await send_screenshot(channel)
    disconnect_screenshot_cooldown = time.time() + 300  # Set cooldown for 5 minutes
    return status

# Function to check if specific text is present in the image using OCR
def text_present(img, texts):
    extracted_text = pytesseract.image_to_string(img).lower()
    print(extracted_text)  # Print the extracted text for debugging

    for text in texts:
        if text.lower() in extracted_text:
            return True
    return False

# Function to capture the screens and check for the disconnect screen
@tasks.loop(seconds=5)
async def monitor_screens():
    global notify_count
    channel = bot.get_channel(int(CHANNEL_ID))  # Use the channel ID
    with mss.mss() as sct:
        screens_detected = False
        for monitor in sct.monitors[1:]:
            # Capture the screen
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            # Check if the specific text is present in the image
            if text_present(img, ["Connection Lost", "Back to server list"]):
                await send_discord_message(channel, "Alert: You have been disconnected from the Minecraft server!")
                await send_disconnect_screenshot(channel)
                screens_detected = True

        if not screens_detected:
            print("No disconnection text detected on any screen.")
        
        # Check if notification limit has been reached (only if NOTIFY_LIMIT is not 0)
        if NOTIFY_LIMIT != 0 and notify_count >= NOTIFY_LIMIT:
            print(f"Notification limit reached. Stopping monitoring after {notify_count} notifications.")
            monitor_screens.stop()

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    channel = bot.get_channel(int(CHANNEL_ID))
    await channel.send("Initialized successfully. Type !screenshot to send a screenshot request.")
    monitor_screens.start()

@bot.command(name='screenshot')
async def screenshot(ctx):
    if str(ctx.author.id) in AUTHORIZED_USERS:
        status = await send_screenshot(ctx.channel)
        if status == 200:
            await ctx.send("Screenshot sent successfully.")
        else:
            await ctx.send("Failed to send screenshot.")
    else:
        await ctx.send("You are not authorized to use this command.")

if __name__ == "__main__":
    # Run the Discord bot
    bot.run(BOT_TOKEN)
