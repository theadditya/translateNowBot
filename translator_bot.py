import logging
import os
from googletrans import Translator, LANGUAGES
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ParseMode

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
        "👋 **Welcome to the On-Demand Translator Bot!**\n\n"
        "**Group Chat Mode:**\n"
        "To translate any message, simply **reply** to it with the language code you want.\n"
        "  *Example:* Reply to a message with `en` to translate it to English.\n\n"
        "**Private Chat Mode:**\n"
        "Send me a message directly using the format `lang_code: your text` to get an instant translation.\n"
        "  *Example:* `fr: Hello, how are you?`\n\n"
        "**General Commands:**\n"
        "• `/languages` - See the list of all available language codes."
    )
    update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# Handler for the /languages command
def list_languages(update: Update, context: CallbackContext):
    """Sends a list of supported language codes."""
    lang_list = [f"`{code}`: {name.capitalize()}" for code, name in LANGUAGES.items()]
    chunk_size = 25
    for i in range(0, len(lang_list), chunk_size):
        chunk = lang_list[i:i + chunk_size]
        update.message.reply_text("\n".join(chunk), parse_mode=ParseMode.MARKDOWN)

# Handler for direct translation in private chat
def direct_translate(update: Update, context: CallbackContext):
    """Translates a message sent directly to the bot in 'lang: text' format."""
    global translator
    user_text = update.message.text
    
    if ':' not in user_text:
        update.message.reply_text(
            "In a private chat, please use the format `lang_code: your text` to translate.\n"
            "*Example:* `de: Hello, how are you?`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    parts = user_text.split(':', 1)
    if len(parts) < 2 or not parts[1].strip():
        update.message.reply_text("Please provide some text after the language code.")
        return

    lang_code = parts[0].strip().lower()
    text_to_translate = parts[1].strip()

    if lang_code not in LANGUAGES:
        update.message.reply_text(f"'{lang_code}' is not a valid language code. Use /languages to see the list.")
        return

    try:
        translated = translator.translate(text_to_translate, dest=lang_code)
        detected_lang_code = translated.src
        detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()

        response = (
            f"Translated from **{detected_lang_name}** to **{LANGUAGES[lang_code].capitalize()}**:\n\n"
            f"`{translated.text}`"
        )
        update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error during direct translation: {e}")
        update.message.reply_text("Sorry, an error occurred during translation.")

# Handler for on-demand translation in group chats via reply
def reply_translate(update: Update, context: CallbackContext):
    """Translates the replied-to message."""
    global translator
    
    original_message = update.message.reply_to_message
    # The text of the new message is the target language
    target_lang = update.message.text.strip().lower()
    
    # Check if the command is a valid language code
    if target_lang not in LANGUAGES:
        # If it's not a language code, we assume it's a regular reply and do nothing.
        return

    # Check if there is text in the original message to translate
    if not original_message.text:
        return
        
    try:
        translated = translator.translate(original_message.text, dest=target_lang)
        detected_lang_code = translated.src
        detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()

        response = (
            f"Translated from **{detected_lang_name}** to **{LANGUAGES[target_lang].capitalize()}**:\n\n"
            f"`{translated.text}`"
        )
        # Reply to the original message, not the command
        original_message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        # Delete the command message (e.g., the user's "en" reply) to keep the chat clean
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)

    except Exception as e:
        logger.error(f"Could not perform reply-translate: {e}")

# Main function to start the bot
def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        print("FATAL: Telegram token not found. Please set the TELEGRAM_TOKEN environment variable.")
        return
        
    if not translator:
        print("FATAL: Translator was not initialized. Bot cannot start.")
        return
        
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("languages", list_languages))

    # Handler for on-demand translations in GROUPS via reply
    dispatcher.add_handler(MessageHandler(
        Filters.reply & Filters.text & ~Filters.command & Filters.chat_type.groups,
        reply_translate
    ))
    
    # Handler for direct translations in PRIVATE CHAT
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        direct_translate
    ))
    
    print("Starting bot polling...")
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()

