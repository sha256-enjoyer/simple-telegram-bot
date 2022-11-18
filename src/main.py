"""
Simple Telegram bot for BADIP table info getting.
"""
import logging
import sys
import json
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
from telegram.ext.filters import Filters
from decouple import config


with open(config('settings'), 'r') as f:
    SETTINGS = json.load(f)


def fetch_chat_id(update: Updater) -> int:
    return int(update.effective_chat.id)


def start(update: Updater, context: CallbackContext) -> None:
    global SETTINGS

    chat_id = fetch_chat_id(update)
    SETTINGS['users'][chat_id] = int(config('default_channel'))
    context.bot.send_message(chat_id=chat_id,
                             text=config('start_message'),
                             parse_mode=config('default_parse_mode'))


def add_channel(update: Updater, context: CallbackContext) -> None:
    global SETTINGS

    chat_id = fetch_chat_id(update)
    if chat_id < 0 and int(update.message.from_user.id) == int(config('admin_id')):
        name = " ".join(update.message.text.split()[1:])
        SETTINGS['channels'][name] = chat_id
        context.bot.send_message(chat_id=chat_id,
                                 text=f'This chat (id: {chat_id}) has been added to settings as "{name}".')


def messages_exchange(update: Updater, context: CallbackContext) -> None:
    global SETTINGS

    chat_id = fetch_chat_id(update)
    if chat_id > 0:
        SETTINGS['messages'][str(update.message.message_id + 1)] = chat_id
        try:
            gcid = int(config('default_channel'))
        except ValueError:
            logging.warning('Please set default channel in .env')
            return 
            
        if str(chat_id) in SETTINGS['users']:
            gcid = int(SETTINGS['users'][str(chat_id)])

        context.bot.copy_message(gcid, chat_id, update.message.message_id)
        logging.debug(f'message_repost: forward from {chat_id} to {gcid}, message {update.message.message_id}')

    if chat_id < 0:
        try:
            reply_id = int(update.message.reply_to_message.message_id)
        except AttributeError:
            logging.debug('Nobody reply.')
            return 
            
        if str(reply_id) in SETTINGS['messages']:
            context.bot.copy_message(SETTINGS['messages'][str(reply_id)], chat_id, int(update.message.message_id))
            logging.debug(f'message_repost: reply from {chat_id} for {SETTINGS["messages"][str(reply_id)]}, message {update.message.message_id}')


def send_your_id(update: Updater, context: CallbackContext) -> None:
    chat_id = fetch_chat_id(update)
    if chat_id > 0:
        context.bot.send_message(chat_id=chat_id, text=f'Your ID: `{chat_id}`.', parse_mode='Markdown')


def set_channel(update: Updater, context: CallbackContext) -> None:
    global SETTINGS

    chat_id = fetch_chat_id(update)
    if chat_id > 0:
        SETTINGS['users'][str(chat_id)] = int(SETTINGS['channels'][update.message.text.split('/')[1]])
        logging.debug(f"set {SETTINGS['users'][str(chat_id)]} for user {chat_id}")


def save_settings() -> None:
    with open(config('settings'), 'w') as f:
        json.dump(SETTINGS, f)


class SimpleTelegramBot:
    def __init__(self):

        handlers_map = {
            'start': start,
            'add': add_channel,
            'id': send_your_id,
        }

        for channel in SETTINGS['channels']:
            handlers_map[channel] = set_channel

        bot_logger = logging.getLogger()
        bot_logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        filehandler = logging.FileHandler('bot.log')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        filehandler.setFormatter(formatter)
        bot_logger.addHandler(handler)
        bot_logger.addHandler(filehandler)

        updater = Updater(token=config('token'), use_context=True)

        for command in handlers_map:
            updater.dispatcher.add_handler(CommandHandler(command, handlers_map[command]))

        updater.dispatcher.add_handler(MessageHandler(Filters.text, messages_exchange))
        updater.dispatcher.add_handler(MessageHandler(Filters.animation, messages_exchange))
        updater.dispatcher.add_handler(MessageHandler(Filters.document, messages_exchange))
        updater.dispatcher.add_handler(MessageHandler(Filters.audio, messages_exchange))
        updater.dispatcher.add_handler(MessageHandler(Filters.photo, messages_exchange))

        updater.start_polling()
        updater.idle()

        save_settings()


if __name__ == "__main__":
    SimpleTelegramBot()
