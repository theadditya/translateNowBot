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
        "To translate any message, simply **reply** to it with the command `/translate <lang_code>`.\n"
        "  *Example:* Reply to a message with `/translate en` to translate it to English.\n\n"
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

# Handler for the /translate command used as a reply in groups
def translate_command_reply(update: Update, context: CallbackContext):
    """Translates a message when a user replies with /translate <lang_code>."""
    global translator
    
    original_message = update.message.reply_to_message
    if not original_message:
        update.message.reply_text("Please use this command as a reply to the message you want to translate.")
        return

    if not context.args:
        update.message.reply_text("Please provide a language code after the command. Example: `/translate en`")
        return

    target_lang = context.args[0].lower()
    if target_lang not in LANGUAGES:
        update.message.reply_text(f"'{target_lang}' is not a valid language code. Use /languages to see the list.")
        return

    if not original_message.text:
        return # Don't try to translate messages without text
        
    try:
        translated = translator.translate(original_message.text, dest=target_lang)
        detected_lang_code = translated.src
        detected_lang_name = LANGUAGES.get(detected_lang_code, "Unknown").capitalize()

        response = (
            f"Translated from **{detected_lang_name}** to **{LANGUAGES[target_lang].capitalize()}**:\n\n"
            f"`{translated.text}`"
        )
        original_message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        # Safely attempt to delete the command message
        try:
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except Exception as e:
            logger.warning(f"Could not delete message. Is the bot an admin? Error: {e}")

    except Exception as e:
        logger.error(f"Could not perform reply-translate command: {e}")
        update.message.reply_text("Sorry, an error occurred during translation.", quote=False)

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
    dispatcher.add_handler(CommandHandler("translate", translate_command_reply, filters=Filters.chat_type.groups))

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



