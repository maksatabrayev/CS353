import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)


app.secret_key = 'abcdefgh'


app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'

mysql = MySQL(app)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            return redirect(url_for('tasks'))
        else:
            message = 'Invalid username or password!'
    

    response = make_response(render_template('login.html', message=message))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            message = 'Username already exists. Please choose another!'
        elif not username or not password or not email:
            message = 'Please fill out all fields!'
        else:
            
            cursor.execute('INSERT INTO User (id, username, email, password) VALUES (NULL, %s, %s, %s)', (username, email, password))
            mysql.connection.commit()

            
            cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
            user = cursor.fetchone()
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            return redirect(url_for('tasks'))
    elif request.method == 'POST':
        message = 'Please fill out all fields!'
    

    response = make_response(render_template('register.html', message=message))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

   
    if request.form.get('_method') == 'DELETE':
        task_id = request.form['task_id']
        if task_id:
            cursor.execute('DELETE FROM Task WHERE id = %s AND user_id = %s', (task_id, session['userid']))
            mysql.connection.commit()
            return redirect(url_for('tasks'))
        else:
            return redirect(url_for('tasks'))

   
    elif request.form.get('_method') == 'PATCH':
        task_id = request.form.get('task_id')
        if not task_id:
            return redirect(url_for('tasks'))

        update_fields = []
        update_values = []

        if request.form.get('title'):
            update_fields.append('title = %s')
            update_values.append(request.form['title'])
        if request.form.get('description'):
            update_fields.append('description = %s')
            update_values.append(request.form['description'])
        if request.form.get('status'):
            update_fields.append('status = %s')
            update_values.append(request.form['status'])
        if request.form.get('deadline'):
            update_fields.append('deadline = %s')
            update_values.append(request.form['deadline'])
        if request.form.get('type'):
            update_fields.append('type = %s')
            update_values.append(request.form['type'])

        
        if not update_fields:
            return redirect(url_for('tasks'))

        
        update_query = 'UPDATE Task SET ' + ', '.join(update_fields) + ' WHERE id = %s AND user_id = %s'
        update_values.extend([task_id, session['userid']])

       
        cursor.execute(update_query, update_values)
        mysql.connection.commit()
        return redirect(url_for('tasks'))
   
    elif request.form.get('_method') == 'MARK_DONE':
        task_id = request.form['task_id']
        if task_id:
            cursor.execute('UPDATE Task SET status = %s, completion_time = NOW() ' + ' WHERE id = %s AND user_id = %s', ('Done',task_id, session['userid']))
            mysql.connection.commit()
        else:
            return redirect(url_for('tasks'))


   
    elif request.method == 'POST' and request.form.get('_method') is None:
        title = request.form['title']
        description = request.form['description']
        status = request.form['status']
        deadline = request.form['deadline']
        task_type = request.form['type']
        user_id = session['userid']

        cursor.execute('''
            INSERT INTO Task (title, description, status, deadline, creation_time, type, user_id) 
            VALUES (%s, %s, %s, %s, NOW(), %s, %s)
        ''', (title, description, status, deadline, task_type, user_id))
        mysql.connection.commit()
        return redirect(url_for('tasks'))

   
    user_id = session['userid']
    cursor.execute('SELECT * FROM Task WHERE user_id = %s AND status = %s ORDER BY deadline ASC', (user_id, 'Done'))
    tasks_completed = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Task WHERE user_id = %s AND status = %s ORDER BY deadline ASC', (user_id, 'Todo'))
    tasks_uncompleted = cursor.fetchall()

    response = make_response(render_template('tasks.html', username=session['username'], 
                                             tasks_completed=tasks_completed, tasks_uncompleted = tasks_uncompleted))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)


    cursor.execute('''
        SELECT title, type, deadline, status
        FROM Task
        WHERE user_id = %s
        ORDER BY deadline ASC
    ''', (user_id,))
    all_tasks = cursor.fetchall()


    cursor.execute('''
        SELECT title, completion_time, TIMESTAMPDIFF(SECOND, creation_time, completion_time) AS time_spent
        FROM Task
        WHERE user_id = %s AND status = 'Done'
        ORDER BY completion_time ASC
    ''', (user_id,))
    completed_tasks = cursor.fetchall()

    cursor.execute('''
        SELECT title, type, deadline
        FROM Task
        WHERE user_id = %s AND status = 'Todo'
        ORDER BY deadline ASC
    ''', (user_id,))
    uncompleted_tasks = cursor.fetchall()

   
    cursor.execute('''
        SELECT title, TIMESTAMPDIFF(SECOND, deadline, completion_time) AS latency
        FROM Task
        WHERE user_id = %s AND status = 'Done' AND completion_time > deadline
    ''', (user_id,))
    late_completed_tasks = cursor.fetchall()

  
    cursor.execute('''
        SELECT type, COUNT(*) AS completed_count
        FROM Task
        WHERE user_id = %s AND status = 'Done'
        GROUP BY type
        ORDER BY completed_count DESC
    ''', (user_id,))
    completed_tasks_by_type = cursor.fetchall()

    response = make_response(render_template('analysis.html', 
                                             all_tasks=all_tasks, 
                                             completed_tasks=completed_tasks, 
                                             uncompleted_tasks=uncompleted_tasks, 
                                             late_completed_tasks=late_completed_tasks, 
                                             completed_tasks_by_type=completed_tasks_by_type))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/logout', methods=['POST'])
def logout():
    
    session.clear()
    

    response = make_response(redirect(url_for('login')))

    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
