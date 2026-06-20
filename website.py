from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import MySQLdb
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL Configuration
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="12345",
    db="attendance_system"
)
cursor = db.cursor()

@app.route('/')
def home():
    return redirect('/login_choice')

@app.route('/login_choice')
def login_choice():
    return render_template('login_choice.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        if cursor.fetchone():
            flash('Email already registered. Please login.')
            return redirect('/login')

        cursor.execute("INSERT INTO students (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        flash('Registration successful. Please login.')
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['email'] = user[2]
            flash('Login successful.')
            return redirect('/dashboard')
        else:
            flash('Invalid email or password.')
            return redirect('/login')
    return render_template('login.html')

@app.route('/teacher_signup', methods=['GET', 'POST'])
def teacher_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor.execute("SELECT * FROM teachers WHERE email=%s", (email,))
        if cursor.fetchone():
            flash('Email already registered. Please login.')
            return redirect('/teacher_login')

        cursor.execute("INSERT INTO teachers (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        flash('Registration successful. Please login.')
        return redirect('/teacher_login')
    return render_template('teacher_signup.html')

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM teachers WHERE email=%s", (email,))
        teacher = cursor.fetchone()

        if teacher and check_password_hash(teacher[3], password):
            session['teacher_id'] = teacher[0]
            session['teacher_name'] = teacher[1]
            flash('Teacher login successful.')
            return redirect('/teacher_dashboard')
        else:
            flash('Invalid teacher credentials.')
            return redirect('/teacher_login')

    return render_template('teacher_login.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        flash('Please log in as a teacher first.')
        return redirect('/teacher_login')

    cursor.execute("""
        SELECT a.id, s.name, s.email, a.photo, a.location, a.timestamp
        FROM attendance a
        JOIN students s ON a.user_id = s.id
        ORDER BY a.timestamp DESC
    """)
    records = cursor.fetchall()

    attendance_data = [
        {
            'id': r[0],
            'name': r[1],
            'email': r[2],
            'photo': r[3],
            'location': r[4],
            'timestamp': r[5]
        }
        for r in records
    ]

    return render_template('teacher_dashboard.html', teacher_name=session['teacher_name'], attendance_data=attendance_data)

@app.route('/delete_attendance/<int:record_id>', methods=['POST'])
def delete_attendance(record_id):
    if 'teacher_id' not in session:
        return redirect('/teacher_login')

    try:
        cursor.execute("DELETE FROM attendance WHERE id = %s", (record_id,))
        db.commit()
        flash("Attendance record deleted successfully.")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting record: {str(e)}")

    return redirect('/teacher_dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.')
        return redirect('/login')

    user_id = session['user_id']
    cursor.execute("SELECT * FROM attendance WHERE user_id=%s ORDER BY timestamp DESC", (user_id,))
    records = cursor.fetchall()
    attendance_records = [
        {
            'timestamp': r[4],
            'location': r[3],
            'photo': r[2]
        } for r in records
    ]

    return render_template('dashboard.html', name=session['name'], email=session['email'], attendance_records=attendance_records)

@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():
    if 'user_id' not in session:
        flash('Please log in first.')
        return redirect('/login')

    user_id = session['user_id']
    photo = request.files.get('photo')
    location = request.form.get('location')

    if not photo or not location:
        flash("Photo and location are required.")
        return redirect('/dashboard')

    filename = secure_filename(f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    cursor.execute("INSERT INTO attendance (user_id, photo, location) VALUES (%s, %s, %s)",
                   (user_id, filename, location))
    db.commit()
    flash("Attendance submitted successfully.")
    return redirect('/dashboard')

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in first.')
        return redirect('/login')

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        flash("New passwords do not match.")
        return redirect('/dashboard')

    cursor.execute("SELECT password FROM students WHERE id=%s", (session['user_id'],))
    current_password_hash = cursor.fetchone()[0]

    if not check_password_hash(current_password_hash, old_password):
        flash("Old password is incorrect.")
        return redirect('/dashboard')

    new_hash = generate_password_hash(new_password)
    cursor.execute("UPDATE students SET password=%s WHERE id=%s", (new_hash, session['user_id']))
    db.commit()
    flash("Password changed successfully.")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)