from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, \
    ConversationHandler
from db_utils import save_message, save_last_message, get_messages
from logger import logger
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import csv
import io

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHOOSING, CUSTOM_RANGE = range(2)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        chat_id = update.message.chat_id
        if update.message.chat.type == 'private':
            return

        message_id = update.message.message_id
        user_id = update.message.from_user.id
        username = update.message.from_user.username
        text = update.message.text
        chat_name = update.message.chat.title if update.message.chat else 'Private'
        message_date = update.message.date

        try:
            await save_message(message_id, user_id, username, text, chat_name, chat_id, message_date)
            await save_last_message(chat_id, message_id)
            logger.info(f"Processed message from {chat_name}: {message_id}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")


async def start_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("За день", callback_data='day'),
            InlineKeyboardButton("За неделю", callback_data='week'),
        ],
        [
            InlineKeyboardButton("За месяц", callback_data='month'),
            InlineKeyboardButton("Все время", callback_data='all_time'),
        ],
        [InlineKeyboardButton("Выбрать диапазон", callback_data='custom_range')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('За какой период вы хотите экспортировать сообщения?', reply_markup=reply_markup)
    return CHOOSING


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    period = query.data

    if period == 'day':
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
    elif period == 'week':
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
    elif period == 'month':
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
    elif period == 'all_time':
        start_date = datetime.min
        end_date = datetime.now()
    else:
        await update.callback_query.message.reply_text('Введите диапазон дат в формате YYYY-MM-DD YYYY-MM-DD:')
        return CUSTOM_RANGE

    messages = await get_messages(start_date, end_date)
    csv_output = generate_csv(messages)
    csv_file = io.BytesIO(csv_output)
    csv_file.name = 'messages.csv'

    await context.bot.send_document(chat_id=update.effective_chat.id, document=csv_file, filename='messages.csv')

    return ConversationHandler.END


async def custom_range_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text:
        try:
            date_range = update.message.text.split()
            start_date_str, end_date_str = date_range
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            messages = await get_messages(start_date, end_date)
            csv_output = generate_csv(messages)
            csv_file = io.BytesIO(csv_output)
            csv_file.name = 'messages.csv'
            await update.message.reply_document(document=csv_file, filename='messages.csv')
        except Exception as e:
            logger.error(f"Error in process messages from database: {e}")
            await update.message.reply_text("Ошибка при обработке диапазона дат. Убедитесь, что вы используете формат "
                                            "YYYY-MM-DD YYYY-MM-DD.")
    return ConversationHandler.END


def generate_csv(messages):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['message_id', 'chat_message_id', 'user_id', 'username', 'text', 'chat_name', 'chat_id',
                     'message_date'])
    for msg in messages:
        writer.writerow(
            [msg['message_id'], msg['chat_message_id'], msg['user_id'], msg['username'], msg['text'], msg['chat_name'],
             msg['chat_id'], msg['message_date']])
    output.seek(0)
    return output.read().encode('utf-8')


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("export", start_export)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            CUSTOM_RANGE: [MessageHandler(filters.TEXT, custom_range_handler)]
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

