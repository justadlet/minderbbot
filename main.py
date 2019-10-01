import logging
import sqlite3
import telegram
import time
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, ConversationHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import bot_messages
from functools import wraps

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level = logging.INFO)
updater = Updater(token = '968884156:AAFyhu8JqNvl__rB_G7DW9cSk9bSY7erl6c', use_context = True)
custom_keyboard = [['/add', '/delete'],
                   ['/set', '/stop'],
                   ['/clear', '/showtasks'],
                   ['/feedback', '/help'],
                   ['/admin_help']]
reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)

def start(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.start_command_response, reply_markup = reply_markup)
def unknown(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.unknown_command_response, reply_markup = reply_markup)

def main():
    dp = updater.dispatcher
    start_handler = CommandHandler('start', start)
    unknown_handler = MessageHandler(Filters.command, unknown)

    dp.add_handler(start_handler)
    dp.add_handler(unknown_handler)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
