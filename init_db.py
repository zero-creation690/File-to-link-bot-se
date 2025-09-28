import sqlite3
from config import DB_PATH

SQL = '''
CREATE TABLE IF NOT EXISTS files (
    short_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    chat_id INTEGER,
    channel_msg_id INTEGER,
    mime_type TEXT,
    channel_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_user ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_msg ON files(channel_msg_id);
'''

if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SQL)
    conn.commit()
    conn.close()
    print('Initialized DB at', DB_PATH)
