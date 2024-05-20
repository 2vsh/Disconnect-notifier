import time
import requests
from PIL import Image
import numpy as np
import mss
import pytesseract
import sys

# Replace with your Discord webhook URL
WEBHOOK_URL = '[HOOK HERE]'

# Path to the Tesseract executable (if not in PATH)
# Adjust the path if necessary
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Install at https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.4.20240503.exe

# Function to send a message to the Discord webhook
def send_discord_message(message):
    data = {
        "content": message,
        "username": "Minecraft Client Monitor"
    }
    response = requests.post(WEBHOOK_URL, json=data)
    return response.status_code

# Function to check if specific text is present in the image using OCR
def text_present(img, texts):
    extracted_text = pytesseract.image_to_string(img).lower()
    print(extracted_text)  # Print the extracted text for debugging

    for text in texts:
        if text.lower() in extracted_text:
            return True
    return False

# Function to capture the screens and check for the disconnect screen
def monitor_screens():
    with mss.mss() as sct:
        while True:
            screens_detected = False
            for monitor in sct.monitors[1:]:
                # Capture the screen
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

                # Check if the specific text is present in the image
                if text_present(img, ["Connection Lost", "Back to server list"]):
                    send_discord_message("Alert: You have been disconnected from the Minecraft server!")
                    screens_detected = True

            if not screens_detected:
                print("No disconnection text detected on any screen.")

            # Sleep for a while before capturing the screens again
            time.sleep(1)

if __name__ == "__main__":
    # Send a test message to the Discord webhook
    test_status = send_discord_message("Test: Monitoring initiated successfully.")
    if test_status == 204:
        print("Test message sent successfully. Monitoring started.")
        monitor_screens()
    else:
        print(f"Failed to send test message: {test_status}. Exiting program.")
 