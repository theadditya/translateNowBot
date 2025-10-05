import logging
import os # Import the 'os' module
from googletrans import Translator, LANGUAGES
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update

# --- Configuration ---
# We will get the token from an environment variable.
# This is much more secure and flexible for deployment.
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
    """Sends a welcome message when the /start command is issued."""
    welcome_text = (
        "👋 Hello! I am your friendly translation bot.\n\n"
        "Here's how to use me:\n\n"
        "1.  **Direct Translation:** Just send me any text and I will translate it to English by default.\n\n"
        "2.  **Translate to a Specific Language:** Use the format `lang_code: your text`.\n"
        "    *Example:* `es: Hello, how are you?`\n\n"
        "3.  **Reply to Translate:** In a group, reply to any message with a language code (e.g., `en`, `hi`, `fr`) and I will translate that message for you.\n\n"
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

# Main translation logic
def translate_text(update: Update, context: CallbackContext):
    """Detects and translates user-provided text."""
    global translator
    
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message.text
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
        return

    user_text = update.message.text
    target_lang = 'en'

    if ':' in user_text:
        parts = user_text.split(':', 1)
        lang_code = parts[0].strip().lower()
        if lang_code in LANGUAGES:
            target_lang = lang_code
            user_text = parts[1].strip()

    if not user_text:
        update.message.reply_text("Please provide some text to translate.")
        return

    try:
        translated = translator.translate(user_text, dest=target_lang)
        detected_lang_code = translated.src
        detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()

        response = (
            f"Translated from **{detected_lang_name}** to **{LANGUAGES[target_lang].capitalize()}**:\n\n"
            f"`{translated.text}`"
        )
        update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during translation: {e}")
        update.message.reply_text("Sorry, an error occurred while trying to translate.")

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
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, translate_text))
    
    print("Starting bot polling...")
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()

