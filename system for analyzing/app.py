from flask import Flask, render_template, request, session, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
import pyodbc

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set a secret key for session management

# Строка підключення до бази даних Access
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    r'DBQ=D:\13438\system for analyzing.accdb;'
)

# Папка для зберігання текстових файлів
SAVE_FOLDER = 'results'
os.makedirs(SAVE_FOLDER, exist_ok=True)
RESULTS_FILE = os.path.join(SAVE_FOLDER, 'all_results.txt')

# Ініціалізація аналізатора настроїв
analyzer = SentimentIntensityAnalyzer()

ENGLISH_TEXTS = {
    'Neutral': [
        "Thank you for your excellent service. I appreciate your prompt assistance. 😊",
        "Your kindness and professionalism made my experience truly enjoyable. 👍",
        "I'm grateful for the outstanding support I received. You exceeded my expectations. 🙏"
    ],
    'Negative': [
        "The experience was average, with neither positive nor negative aspects standing out. 😕",
        "The service met the standard expectations, but there was nothing remarkable about it. 😐",
        "I have no strong feelings either way about the outcome of the interaction. 🤷‍♂️"
    ],
}

UKRAINIAN_TEXTS = {
    'Positive': [
        "Сьогодні був настільки епічно крутий день, що йому просто немає перевершення!",
        "Починалось все з невеликих пригод на роботі, але ми, знаєте, які ми незламні бойовики із суперсили, які здатні протистояти будь-яким труднощам!",
        "Автомобіль, здається, просто захотів трошки відпочити, але ми вміємо знайти найкращі варіанти, щоб вирішити ці невеличкі перешкоди.",
        "Щодо погоди... Ось вона, наша можливість вдягти найстильнішу дощову куртку та показати, як ми круті навіть у дощову погоду!",
        "А вечеря в ресторані... Ой, вона просто стала найкращим уявним кінцем цього фантастичного дня!"
    ]
}

def analyze_sentiment(text):
    scores = analyzer.polarity_scores(text)
    neutral_threshold = 0.05
    negative_threshold = -0.1

    if scores['compound'] >= neutral_threshold:
        sentiment = 'Neutral'
    elif scores['compound'] <= negative_threshold:
        sentiment = 'Negative'
    else:
        sentiment = 'Positive'

    return sentiment, scores

@app.route('/', methods=['GET', 'POST'])
def index():
    text = ''
    sentiment = None
    scores = None

    if request.method == 'POST':
        if 'text' in request.form:
            text = request.form['text']
            if text.strip() != '':
                sentiment, scores = analyze_sentiment(text)
            else:
                return render_template('index.html', text=text, sentiment='Error: Text is empty', ukrainian_texts=UKRAINIAN_TEXTS, english_texts=ENGLISH_TEXTS)
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return render_template('index.html', text=text, sentiment='Error: No file selected', ukrainian_texts=UKRAINIAN_TEXTS, english_texts=ENGLISH_TEXTS)
            text = file.read().decode('utf-8')
            sentiment, scores = analyze_sentiment(text)

        if sentiment:
            with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"Text: {text}\n")
                f.write(f"Sentiment: {sentiment}\n")
                f.write(f"Scores: {scores}\n")
                f.write("\n")

    return render_template('index.html', text=text, sentiment=sentiment, scores=scores, ukrainian_texts=UKRAINIAN_TEXTS, english_texts=ENGLISH_TEXTS)

@app.route('/add_db_text', methods=['POST'])
def add_db_text():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        publication_id = request.form.get('publication_id')
        user_id = request.form.get('user_id')
        text = request.form.get('text')
        cursor.execute("INSERT INTO Публікації ([ID публікації], [ID користувача], [Текст публікації], [Дата публікації]) VALUES (?, ?, ?, Now())", (publication_id, user_id, text))
        conn.commit()
        return "Text added to database successfully!"
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/fetch_db_texts')
def fetch_db_texts():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT [ID публікації], [ID користувача], [Текст публікації], [Дата публікації] FROM Публікації")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            text = row[2]
            scores = analyzer.polarity_scores(text)
            neutral_threshold = 0.05
            negative_threshold = -0.1

            if scores['compound'] >= neutral_threshold:
                sentiment = 'Neutral'
            elif scores['compound'] <= negative_threshold:
                sentiment = 'Negative'
            else:
                sentiment = 'Positive'

            result.append({
                'ID публікації': row[0],
                'ID користувача': row[1],
                'Текст публікації': text,
                'Дата публікації': row[3],
                'Настрій': sentiment
            })
        return render_template('db_texts.html', texts=result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/delete_db_text/<int:publication_id>', methods=['POST'])
def delete_db_text(publication_id):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Публікації WHERE [ID публікації] = ?", (publication_id,))
        conn.commit()
        return "Text deleted from database successfully!"
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/toggle-theme')
def toggle_theme():
    # Toggle the theme based on the current theme stored in session or a cookie
    if 'theme' in session:
        if session['theme'] == 'light':
            session['theme'] = 'dark'
        else:
            session['theme'] = 'light'
    else:
        # Set the initial theme to light if not set before
        session['theme'] = 'light'

    return session['theme']

if __name__ == '__main__':
    app.run(debug=True)
