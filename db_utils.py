import os
import aiomysql
from dotenv import load_dotenv
from logger import logger

load_dotenv()


async def create_connection():
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')

    if None in (host, user, password, db_name):
        raise ValueError("Database configuration is incomplete")

    try:
        connection = await aiomysql.connect(
            host=host,
            port=3306,
            user=user,
            password=password,
            db=db_name,
            autocommit=True
        )
        return connection
    except Exception as e:
        logger.error(f"Error creating connection to database: {e}")
        return None


async def execute_query(query, params=None, is_select=False):
    conn = await create_connection()
    if conn is None:
        raise RuntimeError("Failed to create database connection")

    try:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            try:
                await cursor.execute(query, params)
                if is_select:
                    result = await cursor.fetchall()
                    return result
                return cursor.rowcount
            except Exception as e:
                logger.error(f"Error executing query: {query} - {e}")
                raise
    finally:
        conn.close()


async def save_message(chat_message_id, user_id, username, text, chat_name, chat_id, message_date):
    query = """
    INSERT INTO messages (chat_message_id, user_id, username, text, chat_name, chat_id, message_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    try:
        await execute_query(query, (chat_message_id, user_id, username, text, chat_name, chat_id, message_date))
    except Exception as e:
        logger.error(f"Error saving message: {e}")


async def save_last_message(chat_id, last_message_id):
    check_query = """
    SELECT chat_id FROM lastmessages WHERE chat_id = %s
    """
    update_query = """
    UPDATE lastmessages SET last_message_id = %s WHERE chat_id = %s
    """
    insert_query = """
    INSERT INTO lastmessages (chat_id, last_message_id) VALUES (%s, %s)
    """
    try:
        result = await execute_query(check_query, (chat_id,), is_select=True)
        if result:
            await execute_query(update_query, (last_message_id, chat_id))
        else:
            await execute_query(insert_query, (chat_id, last_message_id))
    except Exception as e:
        logger.error(f"Error saving last message: {e}")


async def get_messages(start_date, end_date):
    query = """
    SELECT * FROM messages
    WHERE message_date BETWEEN %s AND %s
    """
    try:
        return await execute_query(query, (start_date, end_date), is_select=True)
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []
