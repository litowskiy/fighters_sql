from flask import Flask, redirect, url_for, render_template, request, flash

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hi'

@app.route('/nigga')
def nigga():
    return redirect(url_for('home'))

@app.route('/nigga_move/<name>')
def nigga_move(name):
    return f'nigga move {name}'

if __name__ == "__main__":
    app.run(debug=True)