import os
import time
import discord
from discord.ext import commands, tasks
from PIL import Image
import mss
import pytesseract
from datetime import datetime, timedelta

# Configuration
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Path to the Tesseract executable
DISCORD_ID = '795498713812434964'  # Discord ID to ping. Replace placeholder as needed.
NOTIFY_LIMIT = 0  # Notification limit (0 to disable the limit)
AUTHORIZED_USERS = ['795498713812434964', '673241652688584745']  # List of authorized user IDs for requesting screenshots. Replace placeholders as needed.
CHANNEL_ID = 'CHANNEL ID HERE'  # Discord channel ID where the bot will send messages
BOT_TOKEN = 'TOKEN HERE'  # Your bot's token
MAX_SCREENSHOTS = 10  # Maximum number of screenshots to keep
MAX_DAYS = 7  # Maximum age of screenshots in days

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

# Ensure the "screenshots" directory exists
os.makedirs("screenshots", exist_ok=True)

# Function to send a message to a Discord channel
async def send_discord_message(channel, message):
    global notify_count
    await channel.send(f"<@{DISCORD_ID}> {message}")
    notify_count += 1

# Function to clean up old screenshots
def clean_up_screenshots():
    now = time.time()
    screenshots = sorted(os.listdir("screenshots"), key=lambda x: os.path.getmtime(os.path.join("screenshots", x)))

    if MAX_SCREENSHOTS != 0 and len(screenshots) > MAX_SCREENSHOTS:
        for screenshot in screenshots[:len(screenshots) - MAX_SCREENSHOTS]:
            os.remove(os.path.join("screenshots", screenshot))

    if MAX_DAYS != 0:
        for screenshot in screenshots:
            screenshot_path = os.path.join("screenshots", screenshot)
            if os.path.getmtime(screenshot_path) < now - MAX_DAYS * 86400:
                os.remove(screenshot_path)

# Function to send a screenshot to a Discord channel
async def send_screenshot(channel):
    global notify_count
    clean_up_screenshots()
    start_time = time.time()
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Assuming only one monitor
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            # Reduce image resolution to 77% of the original size
            new_width = int(img.width * 0.77)
            new_height = int(img.height * 0.77)
            img = img.resize((new_width, new_height))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join("screenshots", f"screenshot_{timestamp}.png")
            img.save(screenshot_path)


        await channel.send(file=discord.File(screenshot_path))
        elapsed_time = time.time() - start_time
        notify_count += 1
        return 200, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_message = f"Error capturing screenshot: {e}. It took {elapsed_time:.2f} seconds."
        print(error_message)
        await channel.send(error_message)
        return 500, elapsed_time

# Function to send a screenshot on disconnect with cooldown
async def send_disconnect_screenshot(channel):
    global disconnect_screenshot_cooldown
    if time.time() < disconnect_screenshot_cooldown:
        await channel.send("Cooldown: Please wait before requesting another screenshot.")
        return 429  # Too Many Requests
    status, elapsed_time = await send_screenshot(channel)
    disconnect_screenshot_cooldown = time.time() + 300  # Set cooldown for 5 minutes
    return status

# Function to check if specific text is present in the image using OCR
def text_present(img, texts):
    try:
        extracted_text = pytesseract.image_to_string(img).lower()
        print(extracted_text)  # Print the extracted text for debugging

        for text in texts:
            if text.lower() in extracted_text:
                return True
        return False
    except Exception as e:
        print(f"Error in OCR processing: {e}")
        return False

# Function to capture the screens and check for the disconnect screen
@tasks.loop(seconds=10)  # Increased interval to reduce load
async def monitor_screens():
    global notify_count
    channel = bot.get_channel(int(CHANNEL_ID))  # Use the channel ID
    with mss.mss() as sct:
        screens_detected = False
        for monitor in sct.monitors[1:]:
            try:
                # Capture the screen
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                # Reduce image resolution for faster processing
                img = img.resize((img.width // 2, img.height // 2))

                # Check if the specific text is present in the image
                if text_present(img, ["Connection Lost", "Back to server list"]):
                    await send_discord_message(channel, "Alert: You have been disconnected from the Minecraft server!")
                    await send_disconnect_screenshot(channel)
                    screens_detected = True
            except Exception as e:
                print(f"Error during screen capture or processing: {e}")

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
    await channel.send("Initialized successfully. Type !cmds to see available commands.")
    monitor_screens.start()

@bot.command(name='screenshot', aliases=['ss'])
async def screenshot(ctx):
    if str(ctx.author.id) in AUTHORIZED_USERS:
        await ctx.send("Screenshot request received.")
        status, elapsed_time = await send_screenshot(ctx.channel)
        if status == 200:
            await ctx.send(f"Screenshot sent successfully in {elapsed_time:.2f} seconds.")
        else:
            await ctx.send("Failed to send screenshot.")
    else:
        await ctx.send("You are not authorized to use this command.")

@bot.command(name='adduser')
@commands.has_permissions(administrator=True)
async def add_user(ctx, user_id: int):
    if str(user_id) not in AUTHORIZED_USERS:
        AUTHORIZED_USERS.append(str(user_id))
        await ctx.send(f"User {user_id} added to authorized users.")
    else:
        await ctx.send(f"User {user_id} is already an authorized user.")

@bot.command(name='removeuser')
@commands.has_permissions(administrator=True)
async def remove_user(ctx, user_id: int):
    if str(user_id) in AUTHORIZED_USERS:
        AUTHORIZED_USERS.remove(str(user_id))
        await ctx.send(f"User {user_id} removed from authorized users.")
    else:
        await ctx.send(f"User {user_id} is not an authorized user.")

@bot.command(name='setmaxscreenshots')
@commands.has_permissions(administrator=True)
async def set_max_screenshots(ctx, max_screenshots: int):
    global MAX_SCREENSHOTS
    MAX_SCREENSHOTS = max_screenshots
    if max_screenshots == 0:
        await ctx.send("Maximum number of screenshots set to unlimited.")
    else:
        await ctx.send(f"Maximum number of screenshots set to {MAX_SCREENSHOTS}.")

@bot.command(name='setmaxdays')
@commands.has_permissions(administrator=True)
async def set_max_days(ctx, max_days: int):
    global MAX_DAYS
    MAX_DAYS = max_days
    if max_days == 0:
        await ctx.send("Maximum age of screenshots set to unlimited.")
    else:
        await ctx.send(f"Maximum age of screenshots set to {MAX_DAYS} days.")

@bot.command(name='status')
async def status(ctx):
    status_message = (
        f"Monitoring Status: {'Running' if monitor_screens.is_running() else 'Stopped'}\n"
        f"Number of Screenshots Taken: {notify_count}\n"
        f"Notification Limit: {NOTIFY_LIMIT}\n"
        f"Authorized Users: {AUTHORIZED_USERS}\n"
        f"Cooldown Time Remaining: {max(0, int(disconnect_screenshot_cooldown - time.time()))} seconds\n"
        f"Maximum Screenshots: {'Unlimited' if MAX_SCREENSHOTS == 0 else MAX_SCREENSHOTS}\n"
        f"Maximum Screenshot Age: {'Unlimited' if MAX_DAYS == 0 else MAX_DAYS} days"
    )
    await ctx.send(status_message)

@bot.command(name='cmds')
async def custom_help(ctx):
    help_message = (
        "Available commands:\n"
        "!screenshot or !ss - Request a screenshot (Authorized users only).\n"
        "!adduser <user_id> - Add an authorized user (Admin only).\n"
        "!removeuser <user_id> - Remove an authorized user (Admin only).\n"
        "!setmaxscreenshots <number> - Set the maximum number of screenshots to keep, set this to 0 to disable (Admin only).\n"
        "!setmaxdays <number> - Set the maximum age of screenshots in days, set this to 0 to disable (Admin only).\n"
        "!status - Check the bot's status.\n"
        "!cmds - Show this help message."
    )
    await ctx.send(help_message)


if __name__ == "__main__":
    # Run the Discord bot
    bot.run(BOT_TOKEN)

   
