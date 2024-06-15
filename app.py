import os
from flask import Flask, flash, render_template, redirect, request
from models import Task

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")


@app.route('/')
def main():
    return render_template('main.html')

# @app.route('/submit', methods=['POST'])
# def submit():
#     message = request.form(message)
#     r = Request.create(message=message)
#     analyze.delay(r.id)
#     return redirect('/result/' + str(r.id))

@app.route('/task/<task_id>')
def view_task(task_id):
    t = Task.get(id=task_id)
    return render_template('results.html', task=t)



# @app.route('/add', methods=['POST'])
# def add_inputs():
#     x = int(request.form['x'] or 0)
#     y = int(request.form['y'] or 0)
#     add.delay(x, y)
#     flash("Your addition job has been submitted.")
#     return redirect('/')
