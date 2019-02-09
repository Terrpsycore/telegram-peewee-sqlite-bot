#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from peewee import  SqliteDatabase, Model, IntegerField, CharField, BooleanField

db = SqliteDatabase('db.sqlite')


class User(Model):
    user_id = IntegerField()
    chat_id = IntegerField()
    first_name = CharField()
    last_name = CharField(null=True)
    username = CharField(null=True)
    ready = BooleanField(default=False)

    class Meta:
        database = db


db.connect()
User.create_table(True)
db.close()


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(bot, update, job_queue):
    """Write new user into database and create delayed action."""
    current_user = update.message.from_user
    chat_id = update.message.chat_id
    db.connect()
    if not User.select().where(User.user_id == current_user.id):
        new_user = User.create(
            user_id=current_user.id,
            chat_id=chat_id,
            first_name=current_user.first_name,
            last_name=current_user.last_name, 
            username=current_user.username
            )
        new_user.save()
    db.close()

    job_queue.run_once(ready_check, 5, context={'chat_id':chat_id, 'full_name':current_user.full_name})

    update.message.reply_text('Hello!')


def ready_check(bot, job):
    """Send a message with Ready inline-button."""
    keyboard = [[InlineKeyboardButton(text="I am ready!", callback_data='ready_answer')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(
        job.context['chat_id'],
        job.context['full_name'] + ', are you ready?',
        reply_markup=reply_markup
        )


def button(bot, update):
    """Handle inline-button interactions."""
    query = update.callback_query

    if query.data == 'ready_answer':
        db.connect()
        current_user = User.select().where(User.user_id == update.effective_user.id).get()
        current_user.ready = True
        current_user.save()
        db.close()
        query.message.reply_text('Nice! Type /users to see all users.')


def show_user_list(bot, update):
    """Show list of users that pressed Ready button."""
    db.connect()
    users = [filter(lambda x: x is not None, [u.first_name, u.last_name]) for u in User.select().where(User.ready == True)]
    db.close()
    text = 'User list:\n'
    for user in users:
        text += ' '.join(user) + '\n'
    update.message.reply_text(text)


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Type /users to see all users.')


def error(bot, error):
    """Log Errors."""
    logger.warning('Error "%s" happened!', error)


def main():
    """Start the bot."""
    updater = Updater("%YOUR_BOT_TOKEN%")

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_job_queue=True))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("users", show_user_list))
    dp.add_handler(CallbackQueryHandler(button))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
