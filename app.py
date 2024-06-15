import os
from flask import Flask, flash, render_template, redirect, request
from tasks import add, analyze
from models import Request

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")


@app.route('/')
def main():
    return render_template('main.html')

@app.route('/submit', methods=['POST'])
def submit():
    message = request.form(message)
    request = Request.create(message=message)
    analyze.delay(request.id)
    flash("Your addition job has been submitted.")
    return redirect('/result/' + str(request.id))

@app.route('/result/<request_id>')
def result(request_id):
    request = Request.get(id=request_id)
    return render_template('result.html', request=request)



@app.route('/add', methods=['POST'])
def add_inputs():
    x = int(request.form['x'] or 0)
    y = int(request.form['y'] or 0)
    add.delay(x, y)
    flash("Your addition job has been submitted.")
    return redirect('/')
