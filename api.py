import sqlite3
import requests
import urllib.parse
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from config import DB_PATH, BOT_TOKEN

app = FastAPI()
TELEGRAM_FILE_API = f'https://api.telegram.org/bot{BOT_TOKEN}/getFile'
TELEGRAM_DOWNLOAD_BASE = f'https://api.telegram.org/file/bot{BOT_TOKEN}'


def db_get(short_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT * FROM files WHERE short_id = ?', (short_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def telegram_file_path(file_id: str) -> str:
    # Call getFile to obtain file_path
    res = requests.get(TELEGRAM_FILE_API, params={'file_id': file_id}, timeout=15)
    data = res.json()
    if not data.get('ok'):
        raise Exception('Telegram getFile failed: ' + str(data))
    return data['result']['file_path']


@app.get('/api/download/{name_shortid}')
def download(name_shortid: str):
    # name_shortid like <cleanname>-<shortid>
    if '-' not in name_shortid:
        raise HTTPException(404, 'Not found')
    short_id = name_shortid.split('-')[-1]
    rec = db_get(short_id)
    if not rec:
        raise HTTPException(404, 'File not found')

    try:
        file_path = telegram_file_path(rec['file_id'])
        file_url = TELEGRAM_DOWNLOAD_BASE + '/' + urllib.parse.quote(file_path)
        # Redirect to Telegram file URL
        return RedirectResponse(file_url)
    except Exception as e:
        raise HTTPException(500, f'Error fetching file: {e}')


@app.get('/api/stream/{name_shortid}')
def stream_page(name_shortid: str):
    if '-' not in name_shortid:
        raise HTTPException(404, 'Not found')
    short_id = name_shortid.split('-')[-1]
    rec = db_get(short_id)
    if not rec:
        raise HTTPException(404, 'File not found')

    try:
        file_path = telegram_file_path(rec['file_id'])
        file_url = TELEGRAM_DOWNLOAD_BASE + '/' + urllib.parse.quote(file_path)
    except Exception as e:
        raise HTTPException(500, f'Error fetching file: {e}')

    # Return a simple player page (video or audio)
    if (rec['mime_type'] or '').startswith('audio'):
        html = f"""
        <html><head><meta charset='utf-8'><title>{rec['file_name']}</title></head>
        <body>
        <h3>{rec['file_name']}</h3>
        <audio controls style='width:100%'>
          <source src='{file_url}' type='audio/mpeg'>
          Your browser does not support the audio element.
        </audio>
        </body></html>
        """
    else:
        # default to video player
        html = f"""
        <html><head><meta charset='utf-8'><title>{rec['file_name']}</title></head>
        <body>
        <h3>{rec['file_name']}</h3>
        <video controls playsinline style='width:100%;max-width:960px'>
          <source src='{file_url}' type='video/mp4'>
          Your browser does not support the video tag.
        </video>
        </body></html>
        """

    return HTMLResponse(content=html)
