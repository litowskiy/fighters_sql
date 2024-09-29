from flask import Flask, redirect, url_for, render_template, request, flash, jsonify
import sqlite3
from datetime import datetime

#TODO: Переписать всю логику по бойцам в id


app = Flask(__name__)
app.secret_key = 'your_secret_key'

conn = sqlite3.connect('test.db', check_same_thread=False)
cursor = conn.cursor()

@app.route('/')
def home():
    return redirect(url_for('main'))

@app.route('/main', methods=['GET', 'POST'])
def main():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        if 'name' in request.form:
            name = request.form['name']
            cursor.execute('SELECT * FROM Fighters WHERE name = ?', (name,))
            fighter_exists = cursor.fetchone()
            if fighter_exists:
                flash('Имя уже существует!', 'error')
            else:
                cursor.execute('INSERT INTO Fighters (name, wins, loses) VALUES (?, ?, ?)', (name, 0, 0))
                conn.commit()
                flash('Боец добавлен успешно!', 'success')
        elif 'delete' in request.form:
            name = request.form['delete']
            cursor.execute('DELETE FROM Fighters WHERE name = ?', (name,))
            conn.commit()
            flash('Боец удален успешно!', 'success')

    cursor.execute('SELECT * FROM FIGHTERS')
    fighters = cursor.fetchall()
    conn.close()

    return render_template('main_sql.html', fighters=fighters, title='Основная')

@app.route('/mark_presence', methods=['GET', 'POST'])
def mark_presence():
    cursor.execute('SELECT * FROM FIGHTERS')
    fighters = cursor.fetchall()
    if request.method == 'POST':
        attended = request.form.getlist('attended')
        today_date = create_training_session(attended)
        return redirect(url_for('training_session', date=today_date))
    return render_template('mark_presence.html', fighters=fighters, title='Присутствющие')

def create_fights_history(fighter_id):
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

def create_training_session(attended_fighters):
    today_date = f'session_{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}'
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS "{today_date}" (
        ROUND INTEGER,
        FIGHTER_1 TEXT,
        SCORE_1 INTEGER,
        SCORE_2 INTEGER,
        FIGHTER_2 TEXT,
        FOREIGN KEY (FIGHTER_1) REFERENCES FIGHTERS (NAME),
        FOREIGN KEY (FIGHTER_2) REFERENCES FIGHTERS (NAME)
    )
    ''')

    fighters = attended_fighters
    if len(fighters) % 2 != 0:
        fighters.append('skip')

    num_fighters = len(fighters)
    x = fighters[0:num_fighters // 2]
    y = fighters[num_fighters // 2:num_fighters]

    matches = []

    for round_num in range(num_fighters - 1):
        if round_num != 0:
            x.insert(1, y.pop(0))
            y.append(x.pop())
        round_matches = [(x[i], y[i]) for i in range(len(x))]
        matches.append(round_matches)

    round_num = 0
    for fight in matches:
        round_num+=1
        for fighter1, fighter2 in fight:
            cursor.execute(f'''
                INSERT INTO "{today_date}" (ROUND, FIGHTER_1, SCORE_1, SCORE_2, FIGHTER_2)
                VALUES (?, ?, ?, ?, ?)
            ''', (round_num, fighter1, 0, 0, fighter2))

    conn.commit()
    return today_date

def update_fighter_kd():
    cursor.execute('''
        UPDATE FIGHTERS SET KD = 
            CASE 
                WHEN LOSES = 0 THEN WINS
                ELSE ROUND(WINS * 1.0 / LOSES, 2)
            END
    ''')

def check_scores(fighter1, score1, score2, fighter2):
    if score1 > score2:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter1,))
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

    return jsonify(success=True)

@app.route('/session/<date>', methods=['GET', 'POST'])
def training_session(date):
    cursor.execute(f'SELECT * FROM "{date}"')
    matches = cursor.fetchall()

    if request.method == 'POST':
        total_matches = int(request.form['total_matches'])  # Получаем количество матчей

        for i in range(total_matches):
            # Получаем данные из формы для каждого матча
            score1 = request.form.get(f'score1_{i}')
            score2 = request.form.get(f'score2_{i}')

            # Пропуск матчей, где данные отсутствуют
            if score1 is None or score2 is None:
                continue

            # Пропуск матчей, где значение 'skip'
            if matches[i][1] == 'skip' or matches[i][4] == 'skip':
                continue

            try:
                score1 = int(score1)
                score2 = int(score2)
            except ValueError:
                continue

            # Данные для обновления
            round_num, fighter_1, _, _, fighter_2 = matches[i]
            cursor.execute(f'''
                UPDATE "{date}" 
                SET SCORE_1 = ?, SCORE_2 = ?
                WHERE ROUND = ? AND FIGHTER_1 = ? AND FIGHTER_2 = ?
            ''', (score1, score2, round_num, fighter_1, fighter_2))

            # Обновление статистики бойцов
            check_scores(fighter1=fighter_1, score1=score1, score2=score2, fighter2=fighter_2)

        update_fighter_kd()

        conn.commit()

    return render_template('training_session.html', matches=matches, today_date=date)

@app.route('/sessions')
def list_sessions():
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%';")
    tables = [row[0] for row in cursor.fetchall()]
    return render_template('story.html', tables=tables)

@app.route('/sessions/<session_id>')
def view_session(session_id):
    cursor.execute(f''' SELECT * FROM "{session_id}"''')
    info = cursor.fetchall()
    results = []
    for fights in info:
        results.append(f'{fights[1]} {fights[2]} - {fights[3]} {fights[4]}')
    return render_template('view_session.html', session=session_id, results=results)

#TODO: переписать эту функцию, как на add_fight
@app.route('/sessions/<session_id>/update', methods=['POST'])
def update_session(session_id):
    data = request.get_json()
    results = data.get('results', [])
    print(data)

    for result in results:
        fighter1 = result['fighter1']
        old_score1 = int(result['oldScore1'])
        new_score1 = int(result['newScore1'])

        fighter2 = result['fighter2']
        old_score2 = int(result['oldScore2'])
        new_score2 = int(result['newScore2'])

        # Update the match scores in the database
        cursor.execute(f'''
            UPDATE "{session_id}"
            SET SCORE_1 = ?, SCORE_2 = ?
            WHERE FIGHTER_1 = ? AND FIGHTER_2 = ?
        ''', (new_score1, new_score2, fighter1, fighter2))

        # Adjust fighter statistics based on score changes
        # First, reverse the old score effects
        if old_score1 > old_score2:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter1,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter2,))
        elif old_score2 > old_score1:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter2,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter1,))

        # Apply the new score effects
        if new_score1 > new_score2:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter1,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter2,))
        elif new_score2 > new_score1:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter2,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter1,))

    # Update KD ratios
    update_fighter_kd()
    conn.commit()

    return jsonify({'status': 'success'})


@app.route('/sessions/<session_id>/add_fight', methods=['GET', 'POST'])
def add_fight(session_id):
    if request.method == 'POST':
        # Получаем данные из формы
        fighter1 = request.form['fighter1']
        score1 = int(request.form['score1'])
        fighter2 = request.form['fighter2']
        score2 = int(request.form['score2'])

        # Проверяем, что выбраны разные бойцы
        if fighter1 == fighter2:
            flash('Выберите двух разных бойцов.')
            return redirect(url_for('add_fight', session_id=session_id))

        # Обновляем данные в базе данных
        cursor.execute(f'''
            INSERT INTO "{session_id}" (ROUND, FIGHTER_1, SCORE_1, SCORE_2, FIGHTER_2)
            VALUES (?, ?, ?, ?, ?)
        ''', ('additional', fighter1, score1, score2, fighter2))

        # Обновление статистики бойцов
        if score1 > score2:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter1,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter2,))
        elif score2 > score1:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter2,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter1,))

        # Обновление KD бойцов
        update_fighter_kd()
        conn.commit()

        # Перенаправляем пользователя на страницу сессии
        return redirect(url_for('training_session', date=session_id))
    else:
        # Получаем список бойцов из текущей сессии
        cursor.execute(f'''
            SELECT FIGHTER_1 FROM "{session_id}" WHERE FIGHTER_1 != 'skip'
            UNION
            SELECT FIGHTER_2 FROM "{session_id}" WHERE FIGHTER_2 != 'skip'
        ''')
        fighters = [row[0] for row in cursor.fetchall()]
        fighters = sorted(set(fighters))  # Убираем дубликаты и сортируем

        return render_template('add_fight.html', session_id=session_id, fighters=fighters)


@app.route('/profiles')
def list_profiles():
    cursor.execute("SELECT name, id FROM FIGHTERS")
    fighter_info = [row for row in cursor.fetchall()]
    return render_template('profiles.html', fighter_info=fighter_info)

@app.route('/profiles/id_<profile_id>')
def view_profile(profile_id):
    cursor.execute('SELECT * FROM FIGHTERS WHERE id = ?', [profile_id])
    fighter_info = [row for row in cursor.fetchall()]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    fights = get_all_entries_for_person(fighter_info[0][1])
    return render_template('view_profile.html', fighter_info=fighter_info, fights=fights)

def get_all_entries_for_person(person_name):
    # Получаем список таблиц, начинающихся с 'session'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    session_tables = cursor.fetchall()

    results = []
    for table in session_tables:
        table_name = table[0]
        cursor.execute(f'''
            SELECT * FROM "{table_name}" WHERE FIGHTER_1 = ? OR FIGHTER_2 = ?
        ''', (person_name, person_name))
        rows = cursor.fetchall()
        results.extend(rows)
    return results


#TODO: сделать таблицу историй боев для каждого бойца

if __name__ == '__main__':
    app.run(debug=True)