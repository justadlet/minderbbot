import logging
import sqlite3
import telegram
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, ConversationHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import bot_messages
from functools import wraps


LIST_OF_ADMINS = [251961384]

READ_NEW_TASK = 0
READ_TASK_NUM = 1
READ_MINUTES = 2
READ_FEEDBACK = 3
READ_CLEAR_CONFIRMATION = 4

connection = sqlite3.connect('userTasks.db', check_same_thread = False)

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level = logging.INFO)

updater = Updater(token = '968884156:AAFyhu8JqNvl__rB_G7DW9cSk9bSY7erl6c', use_context = True)

"""Commands with database"""

custom_keyboard = [['/add', '/delete'],
                   ['/set', '/stop'],
                   ['/clear', '/showtasks'],
                   ['/feedback', '/help'],
                   ['/admin_help']]
reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)

def sql_table(connection):
    cur = connection.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS tasks(id integer PRIMARY KEY, user_id integer, task text)")
    connection.commit()

sql_table(connection)

def sql_insert(connection, entities):
    cur = connection.cursor()
    cur.execute('INSERT INTO tasks(user_id, task) VALUES(?, ?)', entities)
    connection.commit()

def sql_clear(user_id):
    cur = connection.cursor()
    cur.execute('DELETE FROM tasks WHERE user_id = ?', (user_id, ))
    connection.commit()

def sql_delete(user_id, task_number):
    cur = connection.cursor()
    task_number = task_number - 1
    cur.execute('DELETE FROM tasks WHERE id in (SELECT id FROM tasks WHERE user_id = ? LIMIT 1 OFFSET ?)', (user_id, task_number))
    connection.commit()

def sql_number_of_tasks(user_id):
    cur = connection.cursor()
    cur.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id, ))
    number_of_tasks = cur.fetchall()
    result = number_of_tasks[0][0]
    connection.commit()
    return result

def sql_get_tasks(user_id):
    cur = connection.cursor()
    cur.execute('SELECT task FROM tasks WHERE user_id = ?', (user_id, ))
    tasks = cur.fetchall()
    print("/showtasks: User #" + str(user_id) + " wanted to show his tasks: ")
    connection.commit()
    return tasks

def sql_get_distinct_ids():
    cur = connection.cursor()
    cur.execute('SELECT COUNT (DISTINCT user_id) FROM tasks')
    distinct_ids = cur.fetchall()
    connection.commit()
    return distinct_ids[0][0]

def sql_get_ids():
    cur = connection.cursor()
    cur.execute('SELECT DISTINCT user_id FROM tasks')
    ids = cur.fetchall()
    user_ids = []
    for i in ids:
        user_ids.append(i[0])
    connection.commit()
    return user_ids

def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            context.bot.send_message(chat_id = update.message.chat_id, text = "К сожалению, это функция доступна только админам 😬", reply_markup = reply_markup)
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def add_to_database(user_id, new_task):
    print("/add: User with id: " + str(user_id) + " added a new task: ")
    entities = (user_id, new_task)
    sql_insert(connection, entities)

def get_text(user_id):
    ith = 0
    text = ""
    tasks = sql_get_tasks(user_id)
    for task_i in tasks:
        ith = ith + 1
        ith_text = str(ith) + ". " + task_i[0] + "\n"
        text = text + ith_text
    return text

def cancel(update, context):
    user_id = update.message.from_user.id
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.cancelled_successfully, reply_markup = reply_markup)
    return ConversationHandler.END

@restricted
def admin_send_to_all(update, context):
    try:
        user_ids = sql_get_ids()
        text = context.args[0]
        ith = 0
        for word in context.args:
            ith = ith + 1
            if ith > 1:
                text = text + " " + word
        for sending_id in user_ids:
            context.bot.send_message(chat_id = sending_id, text = text, reply_markup = reply_markup)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_success_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_error_command_response, reply_markup = reply_markup)

@restricted
def admin_send_to(update, context):
    try:
        user_id = context.args[0]
        text = context.args[1]
        ith = 0
        for word in context.args:
            ith = ith + 1
            if ith > 2:
                text = text + " " + word
        context.bot.send_message(chat_id = user_id, text = text, reply_markup = reply_markup)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_success_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_error_command_response, reply_markup = reply_markup)

@restricted
def admin_get_distinct(update, context):
    distinct_users_number = sql_get_distinct_ids()
    context.bot.send_message(chat_id = update.message.chat_id, text = distinct_users_number, reply_markup = reply_markup)

@restricted
def admin_help(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.admin_help_command_response, reply_markup = reply_markup)

def alarm(context):
    job = context.job
    user_id = job.context['user_id']
    user_tasks = get_text(user_id)
    whole_text = bot_messages.checking_todo_list_words + user_tasks + bot_messages.checked_todo_list_words
    context.bot.send_message(job.context['chat_id'], text = whole_text, reply_markup = reply_markup)

def clear(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.clear_command_confirmation, reply_markup = reply_markup)
    return READ_CLEAR_CONFIRMATION

def read_clear_confirmation(update, context):
    text = update.message.text
    if text == 'Да':
        user_id = update.message.from_user.id
        user_tasks = sql_number_of_tasks(user_id)
        if user_tasks > 0:
            sql_clear(user_id)
            print("/clear: User with id: " + str(user_id) + " cleared all his tasks")
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.clear_successfully_command_response, reply_markup = reply_markup)
        else:
            print("/clear: User with id: " + str(user_id) + " could not clear his tasks")
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.tasks_empty_command_response, reply_markup = reply_markup)
    elif text == 'Нет':
        context.bot.send_message(chat_id = update.message.chat_id, text = "Окей 😉", reply_markup = reply_markup)
    return ConversationHandler.END

def add_task(update, context):
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.add_task_write_task, reply_markup = reply_markup)
        return READ_NEW_TASK
    new_task = context.args[0]
    ith = 0
    for word in context.args:
        ith = ith + 1
        if ith > 1:
            new_task = new_task + " " + word
    user_id = update.message.from_user.id
    add_to_database(user_id, new_task)
    whole_text = bot_messages.updated_tasks_command_response + get_text(user_id)
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)

def read_new_task(update, context):
    new_task = update.message.text
    user_id = update.message.from_user.id
    add_to_database(user_id, new_task)
    whole_text = bot_messages.updated_tasks_command_response + get_text(user_id)
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)
    return ConversationHandler.END

def delete_task(update, context):
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_write_task, reply_markup = reply_markup)
        return READ_TASK_NUM
    task = context.args[0]
    try:
        task_number = int(task)
        user_id = update.message.from_user.id
        number_of_tasks = sql_number_of_tasks(user_id)
        if task_number < 1 or task_number > number_of_tasks:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_wrong_number_command_response, reply_markup = reply_markup)
            return
        sql_delete(user_id, task_number)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_successfully_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_error_command_response, reply_markup = reply_markup)

def read_task_num(update, context):
    task = update.message.text
    try:
        task_number = int(task)
        user_id = update.message.from_user.id
        number_of_tasks = sql_number_of_tasks(user_id)
        if task_number < 1 or task_number > number_of_tasks:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_wrong_number_command_response, reply_markup = reply_markup)
            return ConversationHandler.END
        sql_delete(user_id, task_number)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_successfully_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_error_command_response, reply_markup = reply_markup)
    return ConversationHandler.END
def set_timer(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.set_timer_write_time, reply_markup = reply_markup)
        return READ_MINUTES
    text = context.args[0]
    try:
        updated = 0
        due = int(text)
        if due < 1 or due > 1440:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.error_time_command_response, reply_markup = reply_markup)
            return
        if 'job' in context.chat_data:
            updated = 1;
            old_job = context.chat_data['job']
            old_job.schedule_removal()

        user_id = update.message.from_user.id
        new_job = context.job_queue.run_repeating(alarm, due * 60, context = {"chat_id": chat_id, "user_id": user_id})
        context.chat_data['job'] = new_job
        if updated is 0:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.set_timer_successfully_command_response, reply_markup = reply_markup)
        else:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.updated_timer_successfully_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.set_timer_error_command_response, reply_markup = reply_markup)

def read_minutes(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    text = update.message.text
    try:
        updated = 0
        due = int(text)
        if due < 1 or due > 1440:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.error_time_command_response, reply_markup = reply_markup)
            return ConversationHandler.END
        if 'job' in context.chat_data:
            updated = 1;
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        user_id = update.message.from_user.id
        new_job = context.job_queue.run_repeating(alarm, due * 60, context = {"chat_id": chat_id, "user_id": user_id})
        context.chat_data['job'] = new_job
        if updated is 0:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.set_timer_successfully_command_response, reply_markup = reply_markup)
        else:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.updated_timer_successfully_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.set_timer_error_command_response, reply_markup = reply_markup)
    return ConversationHandler.END

def feedback(update, context):
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_write_text,  reply_markup = reply_markup)
        return READ_FEEDBACK
    text = context.args[0]
    ith = 0
    for word in context.args:
        ith = ith + 1
        if ith > 1:
            text = text + " " + word
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    text = "❗️Хей, пользоветель бота отправил новый фидбэк всем админам: ❗️\n\nFeedback:\n" + text + "\n\nUsername: @" + str(username) + "\n\nUser ID: " + str(user_id)
    for admin_id in LIST_OF_ADMINS:
        context.bot.send_message(chat_id = admin_id, text = text)
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_success_command_response, reply_markup = reply_markup)

def read_feedback(update, context):
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    text =  "❗️Хей, пользоветель бота отправил новый фидбэк всем админам: ❗️\n\nFeedback:\n" + text + "\n\nUsername: @" + str(username) + "\n\nUser ID: " + str(user_id)
    for admin_id in LIST_OF_ADMINS:
        context.bot.send_message(chat_id = admin_id, text = text)
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_success_command_response, reply_markup = reply_markup)
    return ConversationHandler.END

def show_tasks(update, context):
    user_id = update.message.from_user.id
    tasks = sql_get_tasks(user_id)
    user_tasks = sql_number_of_tasks(user_id)
    if user_tasks > 0:
        whole_text = bot_messages.show_tasks_command_response + get_text(user_id)
    else:
        whole_text = bot_messages.tasks_empty_command_response
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)

def stop(update, context):
    """ Stop the timer """
    if 'job' not in context.chat_data:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.did_not_set_command_response, reply_markup = reply_markup)
        return
    job = context.chat_data['job']
    job.schedule_removal()
    del context.chat_data['job']
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.stopped_successfully_command_response, reply_markup = reply_markup)


def start(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.start_command_response, reply_markup = reply_markup)

def help(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.help_command_response, reply_markup = reply_markup)

def unknown(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.unknown_command_response, reply_markup = reply_markup)

def main():
    dp = updater.dispatcher
    feedback_handler = CommandHandler('feedback', feedback, pass_args = True, pass_chat_data = True)
    clear_handler = CommandHandler('clear', clear)
    delete_handler = CommandHandler('delete', delete_task, pass_args = True, pass_chat_data = True)
    show_tasks_handler = CommandHandler('showtasks', show_tasks)
    add_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('add', add_task)],

        states = {
            READ_NEW_TASK: [MessageHandler(Filters.text, read_new_task)]
        },

        fallbacks = [CommandHandler('cancel', cancel)]
    )
    del_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('delete', delete_task)],

        states = {
            READ_TASK_NUM: [MessageHandler(Filters.text, read_task_num)]
        },

        fallbacks = [CommandHandler('cancel', cancel)]
    )
    set_timer_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('set', set_timer)],

        states = {
            READ_MINUTES: [MessageHandler(Filters.text, read_minutes)]
        },

        fallbacks = [CommandHandler('cancel', cancel)]
    )
    feedback_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('feedback', feedback)],

        states = {
            READ_FEEDBACK: [MessageHandler(Filters.text, read_feedback)]
        },

        fallbacks = [CommandHandler('cancel', cancel)]
    )
    clear_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('clear', clear)],

        states = {
            READ_CLEAR_CONFIRMATION: [MessageHandler(Filters.text, read_clear_confirmation)]
        },

        fallbacks = [CommandHandler('cancel', cancel)]
    )
    add_handler = CommandHandler('add', add_task)
    set_timer_handler = CommandHandler('set', set_timer)
    stop_handler = CommandHandler('stop', stop, pass_chat_data = True)
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    admin_help_handler = CommandHandler('admin_help', admin_help)
    admin_send_to_all_handler = CommandHandler('admin_send_to_all', admin_send_to_all, pass_args = True, pass_chat_data = True)
    admin_send_to_handler = CommandHandler('admin_send_to', admin_send_to, pass_args = True, pass_chat_data = True)
    admin_get_distinct_handler = CommandHandler('admin_get_distinct', admin_get_distinct)

    unknown_handler = MessageHandler(Filters.command, unknown)

    dp.add_handler(clear_conv_handler)
    dp.add_handler(feedback_conv_handler)
    dp.add_handler(del_conv_handler)
    dp.add_handler(add_conv_handler)
    dp.add_handler(set_timer_conv_handler)
    dp.add_handler(feedback_handler)
    dp.add_handler(clear_handler)
    dp.add_handler(delete_handler)
    dp.add_handler(show_tasks_handler)
    dp.add_handler(add_handler)
    dp.add_handler(set_timer_handler)
    dp.add_handler(stop_handler)
    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(admin_help_handler)
    dp.add_handler(admin_send_to_all_handler)
    dp.add_handler(admin_get_distinct_handler)
    dp.add_handler(admin_send_to_handler)
    dp.add_handler(unknown_handler)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
