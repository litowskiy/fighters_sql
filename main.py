from flask import Flask, redirect, url_for, render_template, request, flash, jsonify
import sqlite3
from datetime import datetime

#TODO: Переписать всю логику по бойцам в id
#TODO: В БД ОСТАЕТСЯ СКИП ФАЙТЕР ДЛЯ КОРРЕКТНОГО ОТОБРАЖЕНИЯ ВО VIEW PROFILE!!

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
        # Обработка добавления бойца
        if 'name' in request.form and 'save_changes' not in request.form:
            name = request.form['name']
            cursor.execute('SELECT * FROM Fighters WHERE name = ?', (name,))
            fighter_exists = cursor.fetchone()
            if fighter_exists:
                flash('Имя уже существует!', 'error')
            else:
                cursor.execute('INSERT INTO Fighters (name, wins, loses) VALUES (?, ?, ?)', (name, 0, 0))
                conn.commit()
                flash('Боец добавлен успешно!', 'success')

        # Обработка удаления бойца
        elif 'delete' in request.form:
            fighter_id = request.form['delete']
            cursor.execute('DELETE FROM Fighters WHERE id = ?', (fighter_id,))
            conn.commit()
            flash('Боец удален успешно!', 'success')

        # Обработка сохранения изменений бойцов
        elif 'save_changes' in request.form:
            cursor.execute('SELECT * FROM Fighters')
            fighters = cursor.fetchall()
            for fighter in fighters:
                fighter_id = fighter[0]
                original_name = request.form.get(f'original_name_{fighter_id}')
                new_name = request.form.get(f'name_{fighter_id}')
                wins = request.form.get(f'wins_{fighter_id}')
                loses = request.form.get(f'loses_{fighter_id}')

                # Проверяем, что все данные получены
                if new_name is not None and wins is not None and loses is not None:
                    try:
                        wins = int(wins)
                        loses = int(loses)
                    except ValueError:
                        flash(f'Некорректные данные для бойца {original_name}', 'error')
                        continue

                    # Проверяем, изменилось ли имя, и нет ли конфликта
                    if new_name != original_name:
                        cursor.execute('SELECT * FROM Fighters WHERE name = ? AND id != ?', (new_name, fighter_id))
                        name_exists = cursor.fetchone()
                        if name_exists:
                            flash(f'Имя {new_name} уже существует!', 'error')
                            continue

                    # Обновляем данные бойца
                    cursor.execute('''
                        UPDATE Fighters
                        SET name = ?, wins = ?, loses = ?
                        WHERE id = ?
                    ''', (new_name, wins, loses, fighter_id))
            conn.commit()
            flash('Изменения сохранены успешно!', 'success')

    cursor.execute('SELECT * FROM Fighters')
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

@app.route('/session/<date>', methods=['GET', 'POST'])
def training_session(date):
    if request.method == 'POST':
        total_matches = int(request.form['total_matches'])  # Получаем количество матчей

        # Получаем текущие матчи перед обновлением
        cursor.execute(f'SELECT * FROM "{date}"')
        matches = cursor.fetchall()

        scores_updated = False  # Флаг для отслеживания изменений

        for i in range(total_matches):
            # Получаем данные из формы для каждого матча
            score1 = request.form.get(f'score1_{i}')
            score2 = request.form.get(f'score2_{i}')

            # Пропуск матчей, где значение 'skip'
            if matches[i][1] == 'skip' or matches[i][4] == 'skip':
                continue

            try:
                score1 = int(score1)
                score2 = int(score2)
            except ValueError:
                continue

            # Получаем существующие счета из базы данных
            existing_score1 = matches[i][2] or 0  # matches[i][2] - SCORE_1
            existing_score2 = matches[i][3] or 0  # matches[i][3] - SCORE_2

            # Если счёты не изменились, пропускаем обновление
            if score1 == existing_score1 and score2 == existing_score2:
                continue

            # Данные для обновления
            round_num, fighter_1, _, _, fighter_2 = matches[i]

            # Обновляем счёты бойцов в базе данных
            cursor.execute(f'''
                    UPDATE "{date}" 
                    SET SCORE_1 = ?, SCORE_2 = ?
                    WHERE ROUND = ? AND FIGHTER_1 = ? AND FIGHTER_2 = ?
                ''', (score1, score2, round_num, fighter_1, fighter_2))

            # Обновляем статистику бойцов в зависимости от того, изменились ли счёты
            update_fighter_stats(fighter_1, existing_score1, score1, fighter_2, existing_score2, score2)

            scores_updated = True  # Отмечаем, что было произведено обновление

        if scores_updated:
            update_fighter_kd()  # Обновляем КД всех бойцов

        conn.commit()

        # Перенаправление на ту же страницу после сохранения данных
        return redirect(url_for('training_session', date=date))

    # Для GET-запроса или после перенаправления получаем обновленные данные
    cursor.execute(f'SELECT * FROM "{date}"')
    matches = cursor.fetchall()

    return render_template('training_session.html', matches=matches, today_date=date)


def update_fighter_stats(fighter1, old_score1, new_score1, fighter2, old_score2, new_score2):
    """Обновляет статистику бойцов (победы и поражения) на основе изменений в счётах."""
    # Убираем старые результаты
    if old_score1 > old_score2:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter1,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter2,))
    elif old_score2 > old_score1:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter2,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter1,))

    # Добавляем новые результаты
    if new_score1 > new_score2:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter1,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter2,))
    elif new_score2 > new_score1:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter2,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter1,))

@app.route('/sessions')
def list_sessions():
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%';")
    tables = [row[0] for row in cursor.fetchall()]
    return render_template('story.html', tables=tables)

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

if __name__ == '__main__':
    app.run(debug=True)