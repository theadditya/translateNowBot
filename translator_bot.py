import logging
import os
import re
from googletrans import Translator, LANGUAGES
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update

# --- Configuration ---
# Get the token from an environment variable for secure deployment.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot Logic ---
translator = None
try:
    print("Initializing translator...")
    translator = Translator()
    print("Translator initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize Translator. Error: {e}")
    exit()

# Handler for the /start command
def start(update: Update, context: CallbackContext):
    """Sends a welcome message with updated instructions."""
    welcome_text = (
        "👋 Hello! I am your friendly translation bot.\n\n"
        "I only translate messages when you ask me to. Here's how:\n\n"
        "1.  **Translate Your Own Text:** Send a message using the format `lang_code: your text`.\n"
        "    *Example:* `es: Hello, how are you?`\n\n"
        "2.  **Translate Someone Else's Message:** In a group, reply to any message with just the language code you want to translate it to.\n"
        "    *Example Reply:* `en`\n\n"
        "Use the /languages command to see a list of all supported language codes."
    )
    update.message.reply_text(welcome_text)

# Handler for the /languages command
def list_languages(update: Update, context: CallbackContext):
    """Sends a list of supported language codes."""
    message = "Here are the supported language codes:\n"
    lang_list = [f"`{code}`: {name.capitalize()}" for code, name in LANGUAGES.items()]
    chunk_size = 25
    for i in range(0, len(lang_list), chunk_size):
        chunk = lang_list[i:i + chunk_size]
        update.message.reply_text("\n".join(chunk), parse_mode="Markdown")

# Main translation logic for explicit triggers
def handle_translation_request(update: Update, context: CallbackContext):
    """Translates text based on a reply or a specific format."""
    global translator
    
    # Case 1: The user replied to a message to translate it.
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message.text
        # The reply text should be the target language code.
        target_lang = update.message.text.lower().strip()

        if target_lang in LANGUAGES:
            try:
                translated = translator.translate(original_message, dest=target_lang)
                detected_lang_code = translated.src
                detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()
                
                response = (
                    f"Translated from **{detected_lang_name}** to **{LANGUAGES[target_lang].capitalize()}**:\n\n"
                    f"`{translated.text}`"
                )
                update.message.reply_text(response, parse_mode="Markdown")

            except Exception as e:
                logger.error(f"Error during reply translation: {e}")
                update.message.reply_text("Sorry, I couldn't translate that message.")
        # If the reply text is not a valid language code, the bot does nothing.
        return

    # Case 2: The user sent a message in the format "lang_code: text".
    user_text = update.message.text
    parts = user_text.split(':', 1)
    lang_code = parts[0].strip().lower()
    text_to_translate = parts[1].strip()

    if not text_to_translate:
        update.message.reply_text("Please provide some text after the language code to translate.")
        return

    try:
        translated = translator.translate(text_to_translate, dest=lang_code)
        detected_lang_code = translated.src
        detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()

        response = (
            f"Translated from **{detected_lang_name}** to **{LANGUAGES[lang_code].capitalize()}**:\n\n"
            f"`{translated.text}`"
        )
        update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during direct translation: {e}")
        update.message.reply_text("Sorry, an error occurred. Make sure you are using a valid language code.")

# Main function to start the bot
def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        print("FATAL: Telegram token not found in environment variables. Please set the TELEGRAM_TOKEN.")
        return
        
    if not translator:
        print("FATAL: Translator was not initialized. Bot cannot start.")
        return

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("languages", list_languages))

    # This new filter triggers the translation handler ONLY for replies or messages in the "lang: text" format.
    # It will ignore all other messages.
    translation_filter = (Filters.reply | Filters.regex(r'^[a-zA-Z-]{2,7}:.*')) & Filters.text & ~Filters.command
    dispatcher.add_handler(MessageHandler(translation_filter, handle_translation_request))
    
    print("Starting bot polling...")
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()

