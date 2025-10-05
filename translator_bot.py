import logging
import os
from googletrans import Translator, LANGUAGES
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PicklePersistence
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
        "👋 **Welcome to the Personal Translator Bot!**\n\n"
        "This bot can automatically translate group messages into your preferred language.\n\n"
        "**Available Commands:**\n"
        "• `/setlang <lang_code>` - Set your preferred language. All messages not in your language will be translated for you.\n"
        "  *Example:* `/setlang es`\n\n"
        "• `/clearlang` - Stop receiving automatic translations.\n\n"
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

# Command to set a user's preferred language
def set_language(update: Update, context: CallbackContext):
    """Saves the user's preferred language preference."""
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("Please provide a language code. Example: `/setlang en`")
        return

    lang_code = context.args[0].lower()
    if lang_code not in LANGUAGES:
        update.message.reply_text(f"'{lang_code}' is not a valid language code. Use /languages to see the list.")
        return
    
    # Initialize the user preferences dictionary if it doesn't exist
    if 'user_prefs' not in context.chat_data:
        context.chat_data['user_prefs'] = {}
    
    context.chat_data['user_prefs'][user_id] = lang_code
    language_name = LANGUAGES[lang_code].capitalize()
    update.message.reply_text(f"Your preferred language has been set to **{language_name}**.", parse_mode=ParseMode.MARKDOWN)

# Command to clear a user's language preference
def clear_language(update: Update, context: CallbackContext):
    """Removes the user's language preference."""
    user_id = update.effective_user.id
    if 'user_prefs' in context.chat_data and user_id in context.chat_data['user_prefs']:
        del context.chat_data['user_prefs'][user_id]
        update.message.reply_text("Your language preference has been cleared. You will no longer receive automatic translations.")
    else:
        update.message.reply_text("You don't have a preferred language set.")

# Main handler for automatic translation of group messages
def auto_translate_group_messages(update: Update, context: CallbackContext):
    """Auto-translates messages for users with set preferences."""
    global translator
    message = update.message
    
    # Ignore messages that are too short or have no text
    if not message.text or len(message.text) < 3:
        return

    # Get user preferences for the current chat
    user_prefs = context.chat_data.get('user_prefs', {})
    if not user_prefs:
        return

    try:
        detected = translator.detect(message.text)
        source_lang = detected.lang
        
        translations_to_post = []
        # Keep track of languages we've already translated to, to avoid duplicates
        processed_langs = {source_lang}

        for user_id, target_lang in user_prefs.items():
            # Translate if the target language is different and not already processed
            if target_lang != source_lang and target_lang not in processed_langs:
                translated = translator.translate(message.text, dest=target_lang)
                lang_name = LANGUAGES[target_lang].capitalize()
                translations_to_post.append(f"**{lang_name}**:\n`{translated.text}`")
                processed_langs.add(target_lang)
        
        if translations_to_post:
            full_translation_text = "\n\n".join(translations_to_post)
            # Reply to the original message with all translations
            message.reply_text(full_translation_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Could not auto-translate message: {e}")

# Main function to start the bot
def main():
    """Start the bot with persistence."""
    if not TELEGRAM_TOKEN:
        print("FATAL: Telegram token not found. Please set the TELEGRAM_TOKEN environment variable.")
        return
        
    if not translator:
        print("FATAL: Translator was not initialized. Bot cannot start.")
        return
        
    # Create a persistence object to save user data
    persistence = PicklePersistence(filename='bot_data')

    updater = Updater(TELEGRAM_TOKEN, use_context=True, persistence=persistence)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("languages", list_languages))
    dispatcher.add_handler(CommandHandler("setlang", set_language))
    dispatcher.add_handler(CommandHandler("clearlang", clear_language))

    # Add the handler for automatic translations in groups
    # It will only trigger for text messages that are not commands in a group chat
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.groups,
        auto_translate_group_messages
    ))
    
    print("Starting bot polling...")
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()

