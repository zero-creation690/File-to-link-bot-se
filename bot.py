import os
import random
import sqlite3
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID, BASE_URL, MAX_FILE_SIZE, DB_PATH

app = Client('filmzi_bot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Helpers

def random_id():
    return random.randint(10000000, 99999999)


def format_file_size(size_bytes):
    if size_bytes == 0:
        return '0 B'
    size_names = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def save_to_db(file_data: dict):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO files(short_id, file_id, file_name, file_size, user_id, timestamp, chat_id, channel_msg_id, mime_type, channel_id)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (
        file_data['short_id'], file_data['file_id'], file_data['file_name'], file_data['file_size'], file_data['user_id'], file_data['timestamp'], file_data['chat_id'], file_data['channel_msg_id'], file_data['mime_type'], file_data.get('channel_id', CHANNEL_ID)
    ))
    conn.commit()
    conn.close()
    return True


def get_from_db(short_id: str):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM files WHERE short_id = ?', (short_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_file_keyboard(file_id, is_video=False):
    keyboard = []
    if is_video:
        keyboard.append([
            InlineKeyboardButton('📺 STREAM', callback_data=f'stream_{file_id}'),
            InlineKeyboardButton('⬇️ DOWNLOAD', callback_data=f'download_{file_id}')
        ])
    else:
        keyboard.append([
            InlineKeyboardButton('⬇️ DOWNLOAD', callback_data=f'download_{file_id}')
        ])
    keyboard.append([
        InlineKeyboardButton('🔗 SHARE', callback_data=f'share_{file_id}'),
        InlineKeyboardButton('🗑️ REVOKE', callback_data=f'revoke_{file_id}')
    ])
    keyboard.append([
        InlineKeyboardButton('❌ CLOSE', callback_data='close')
    ])
    return InlineKeyboardMarkup(keyboard)


@app.on_message(filters.command('start'))
async def start_command(client, message):
    text = '🎬 Welcome to Filmzi permanent link bot! Send any file to get permanent streaming & download links.'
    await message.reply_text(text)


@app.on_message(filters.media & filters.private)
async def handle_media(client, message):
    try:
        # Determine file attributes (document, video, audio, photo)
        if message.document:
            f = message.document
            file_name = f.file_name or f'doc_{random_id()}'
            file_size = f.file_size or 0
            mime_type = f.mime_type or 'document'
            file_id = f.file_id
        elif message.video:
            f = message.video
            file_name = f.file_name or f'video_{random_id()}.mp4'
            file_size = f.file_size or 0
            mime_type = 'video'
            file_id = f.file_id
        elif message.audio:
            f = message.audio
            file_name = f.file_name or f'audio_{random_id()}.mp3'
            file_size = f.file_size or 0
            mime_type = 'audio'
            file_id = f.file_id
        elif message.photo:
            f = message.photo
            file_name = f'photo_{random_id()}.jpg'
            file_size = f.file_size or 0
            mime_type = 'photo'
            file_id = f.file_id
        else:
            await message.reply_text('❌ Unsupported file type.')
            return

        if file_size > MAX_FILE_SIZE:
            await message.reply_text(f'❌ File too large! Max is {format_file_size(MAX_FILE_SIZE)}')
            return

        short_id = str(random_id())

        # Forward to channel
        try:
            forwarded = await message.forward(CHANNEL_ID)
            channel_msg_id = forwarded.id
        except Exception as e:
            await message.reply_text('❌ Failed to store file in channel. Check CHANNEL_ID and bot permissions.')
            print('Forward error:', e)
            return

        file_data = {
            'short_id': short_id,
            'file_id': file_id,
            'file_name': file_name,
            'file_size': file_size,
            'user_id': message.from_user.id,
            'timestamp': int(time.time()),
            'chat_id': message.chat.id,
            'channel_msg_id': channel_msg_id,
            'mime_type': mime_type,
            'channel_id': CHANNEL_ID
        }

        save_to_db(file_data)

        clean_name = file_name.replace(' ', '.')
        download_link = f"{BASE_URL}/api/download/{clean_name}-{short_id}"
        stream_link = f"{BASE_URL}/api/stream/{clean_name}-{short_id}"
        share_link = f"https://t.me/{(await client.get_me()).username}?start=file_{short_id}"

        is_media = mime_type.startswith('video') or mime_type.startswith('audio')

        resp = (
            f"✅ **Your Link Generated!**\n\n"
            f"📁 **FILE NAME:** `{file_name}`\n"
            f"💾 **FILE SIZE:** {format_file_size(file_size)}\n\n"
            f"⬇️ **Download:** `{download_link}`\n"
        )
        if is_media:
            resp += f"📺 **Watch:** `{stream_link}`\n"
        resp += f"🔗 **Share:** `{share_link}`"

        keyboard = create_file_keyboard(short_id, is_media)

        await message.reply_text(resp, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    except Exception as e:
        print('Media handler error:', e)
        await message.reply_text('❌ Error processing file.')


@app.on_callback_query()
async def cb_handler(client, callback_query):
    data = callback_query.data or ''
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    try:
        if data.startswith('stream_'):
            short_id = data.split('_', 1)[1]
            record = get_from_db(short_id)
            if record and record['user_id'] == user_id:
                stream_link = f"{BASE_URL}/api/stream/{record['file_name']}-{short_id}"
                await callback_query.answer('📺 Opening stream...')
                await client.send_message(chat_id, f'📺 **Stream Link:**\n`{stream_link}`', parse_mode=ParseMode.MARKDOWN)
            else:
                await callback_query.answer('❌ File not found or permission denied', show_alert=True)

        elif data.startswith('download_'):
            short_id = data.split('_', 1)[1]
            record = get_from_db(short_id)
            if record and record['user_id'] == user_id:
                dl = f"{BASE_URL}/api/download/{record['file_name']}-{short_id}"
                await callback_query.answer('⬇️ Download link sent!')
                await client.send_message(chat_id, f'⬇️ **Download Link:**\n`{dl}`', parse_mode=ParseMode.MARKDOWN)
            else:
                await callback_query.answer('❌ File not found or permission denied', show_alert=True)

        elif data.startswith('share_'):
            short_id = data.split('_', 1)[1]
            record = get_from_db(short_id)
            if record and record['user_id'] == user_id:
                share = f"https://t.me/{(await app.get_me()).username}?start=file_{short_id}"
                await callback_query.answer('🔗 Share link sent!')
                await client.send_message(chat_id, f'🔗 **Share Link:**\n`{share}`', parse_mode=ParseMode.MARKDOWN)
            else:
                await callback_query.answer('❌ File not found or permission denied', show_alert=True)

        elif data.startswith('revoke_'):
            short_id = data.split('_', 1)[1]
            # Simple revoke: delete DB row (file remains in channel unless you delete channel message)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('DELETE FROM files WHERE short_id = ?', (short_id,))
            conn.commit()
            conn.close()
            await callback_query.answer('🗑️ File revoked!')
            await client.send_message(chat_id, f'🗑️ File with ID `{short_id}` revoked.', parse_mode=ParseMode.MARKDOWN)

        elif data == 'close':
            await callback_query.message.delete()
            await callback_query.answer('Closed')

        else:
            await callback_query.answer('❌ Unknown action')

    except Exception as e:
        print('Callback error:', e)
        await callback_query.answer('❌ Error')


if __name__ == '__main__':
    print('🎬 Filmzi Bot Started')
    app.run()
