import sqlite3

conn = sqlite3.connect('test.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS FIGHTERS_NEW (
    ID INTEGER PRIMARY KEY,
    NAME TEXT NOT NULL,
    WINS INTEGER NOT NULL DEFAULT 0,
    LOSES INTEGER NOT NULL DEFAULT 0,
    KD FLOAT
);''')

cursor.execute('''INSERT INTO FIGHTERS_NEW (ID, NAME, WINS, LOSES, KD)
SELECT ID, NAME, WINS, LOSES, KD FROM FIGHTERS;
''')

conn.commit()
conn.close()