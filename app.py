from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -------------------------------
# Database Configuration
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Neeraja@04",
        database="smartscheduler"
    )

# -------------------------------
# MinHeap Implementation
# -------------------------------
class MinHeap:
    def __init__(self):
        self.heap = []

    def push(self, event):
        self.heap.append(event)
        self._heapify_up(len(self.heap) - 1)

    def pop(self):
        if len(self.heap) == 0:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        root = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._heapify_down(0)
        return root

    def _heapify_up(self, index):
        parent_index = (index - 1) // 2
        if index > 0 and self.heap[index][1] < self.heap[parent_index][1]:
            self.heap[index], self.heap[parent_index] = self.heap[parent_index], self.heap[index]
            self._heapify_up(parent_index)

    def _heapify_down(self, index):
        smallest = index
        left_child = 2 * index + 1
        right_child = 2 * index + 2

        if left_child < len(self.heap) and self.heap[left_child][1] < self.heap[smallest][1]:
            smallest = left_child
        if right_child < len(self.heap) and self.heap[right_child][1] < self.heap[smallest][1]:
            smallest = right_child

        if smallest != index:
            self.heap[index], self.heap[smallest] = self.heap[smallest], self.heap[index]
            self._heapify_down(smallest)

# -------------------------------
# Greedy Algorithm for Scheduling
# -------------------------------
def schedule_tasks(tasks):
    formatted_tasks = []
    for task in tasks:
        try:
            start_time = datetime.strptime(str(task[1]), "%H:%M:%S").time()
            end_time = datetime.strptime(str(task[2]), "%H:%M:%S").time()
            formatted_tasks.append((task[0], start_time, end_time))
        except (ValueError, TypeError) as e:
            print(f"Error processing task {task}: {e}")

    formatted_tasks.sort(key=lambda x: x[2])
    selected_tasks = []
    last_end_time = datetime.min.time()

    for task in formatted_tasks:
        if task[1] >= last_end_time:
            selected_tasks.append((task[0], task[1].strftime("%H:%M"), task[2].strftime("%H:%M")))
            last_end_time = task[2]

    return selected_tasks

# -------------------------------
# Login Page (Default Page)
# -------------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))  # Redirect to the home page if already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT user_id, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['username'] = username
                flash('Login successful! Welcome to Smart Scheduler.', 'success')
                return redirect(url_for('home'))  # Redirect to home after successful login
            else:
                flash('Invalid username or password', 'error')
        except mysql.connector.Error as e:
            flash(f"Database Error: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('login.html')

# -------------------------------
# Register Page
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password before saving it in the database
        hashed_password = generate_password_hash(password)

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if the username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html')

            # Insert the new user into the database
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                           (username, hashed_password))
            connection.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            flash(f"Database Error: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('register.html')

# -------------------------------
# Home Page
# -------------------------------
@app.route('/home')
def home():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('index.html')

# -------------------------------
# View Events
# -------------------------------
@app.route('/events')
def view_events():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT event_name, event_date, start_time, end_time FROM events ORDER BY event_date;")
        all_events = cursor.fetchall()

        if not all_events:
            flash("No events found.", "info")
            return render_template('events.html', upcoming_events=[], all_events=[])

        # Filter events based on current date and time
        current_date = datetime.now().date()
        upcoming_events = [event for event in all_events if datetime.strptime(str(event[1]), "%Y-%m-%d").date() >= current_date]
        scheduled_events = schedule_tasks(upcoming_events)

        return render_template('events.html', upcoming_events=scheduled_events, all_events=all_events)
    except mysql.connector.Error as e:
        flash(f"Database Error: {e}", "error")
        return redirect(url_for('home'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# -------------------------------
# Add Event Page
# -------------------------------
@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_description = request.form['event_description']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO events (event_name, event_date, event_description, start_time, end_time) VALUES (%s, %s, %s, %s, %s)", 
                           (event_name, event_date, event_description, start_time, end_time))
            connection.commit()

            flash('Event added successfully!', 'success')
            
            # After adding event, fetch updated events and redirect
            cursor.execute("SELECT event_name, start_time, end_time FROM events;")
            events = cursor.fetchall()

            # Sort and schedule events after adding new one
            scheduled_events = schedule_tasks(events)
            return render_template('events.html', events=scheduled_events)

        except mysql.connector.Error as e:
            flash(f"Database Error: {e}", "error")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('add_event.html')

# -------------------------------
# Logout
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# -------------------------------
# Error Handlers
# -------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# -------------------------------
# Run the App
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
