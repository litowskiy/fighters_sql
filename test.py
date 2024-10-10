"""def create_fights_history(fighter_id):
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "fights_{fighter_id}" (
            ROUND INTEGER,
            FIGHTER_1 TEXT,
            SCORE_1 INTEGER,
            SCORE_2 INTEGER,
            FIGHTER_2 TEXT,
            FOREIGN KEY (FIGHTER_1) REFERENCES FIGHTERS (NAME),
            FOREIGN KEY (FIGHTER_2) REFERENCES FIGHTERS (NAME)
        )
        ''')

def check_scores(fighter1, score1, score2, fighter2):
    if score1 > score2:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter1, ))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter2,))
    elif score2 > score1:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter2,))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter1,))

    return jsonify(success=True)"""
import sqlite3
conn = sqlite3.connect('test.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('SELECT * FROM Fighters WHERE name = ?', ('Илья',))
kd = [row[4] for row in cursor.fetchall()]
print(kd)
