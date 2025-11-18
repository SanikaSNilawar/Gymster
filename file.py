import datetime
import os
import random

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import mysql.connector as myConn
from flask_session import Session
import redis
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'secret_key'

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379)
Session(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'static/img/'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

plan_fees = {
    'Basic Gym': 750,
    'Gym and Cardio': 1200,
    'Yoga': 700,
    'Zumba': 850,
    'Gym and Zumba': 1500,
    'Gym and Yoga': 1350,
    'Gym and Cardio and Yoga': 1800,
    'Gym and Cardio and Zumba': 2000,
    'Full Access': 2500
}

# Connect to the MySQL database
db = myConn.connect(host="localhost", user="root", password="Sanika@12", database="gym")
db_cursor = db.cursor()
admin_username = 'admin'
admin_password = 'adminpass'



@app.route('/')
def home():
    return render_template('index.html')


@app.route('/plans')
def plans():
    return render_template('membership_plans.html')


@app.route('/new_trainer')
def new_trainer():
    return render_template('add_trainer.html')


@app.route('/posts')
def posts():
    # Assuming you have a function to fetch posts from the database
    # Here's a sample query to fetch posts along with the trainer name
    query = """
    SELECT posts.post_id, posts.title, posts.post_description, member.first_name,member.last_name, posts.post_date 
    FROM posts 
    INNER JOIN member ON posts.member_id = member.member_id
    ORDER BY posts.post_date DESC
    """
    db_cursor.execute(query)
    posts_data = db_cursor.fetchall()

    # Assuming each post_data item is a tuple containing (post_id, title, description, trainer_name, post_date)
    posts = []
    for post_data in posts_data:
        post = {
            'post_id': post_data[0],
            'title': post_data[1],
            'description': post_data[2],
            'trainer_name1': post_data[3],
            'trainer_name2': post_data[4],
            'post_date': post_data[5]
        }
        posts.append(post)

    return render_template('posts.html', posts=posts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the provided credentials are for admin login
        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))

        # Query to check if the provided username and password exist in the 'trainer' table
        trainer_query = "SELECT trainer_id FROM trainer WHERE username = %s AND password = %s"
        db_cursor.execute(trainer_query, (username, password))
        trainer_result = db_cursor.fetchone()

        if trainer_result:
            trainer_id = trainer_result[0]
            session['trainer_id'] = trainer_id
            return redirect(url_for('trainer_dashboard'))

        # Query to check if the provided username and password exist in the 'member' table
        member_query = "SELECT member_id FROM member WHERE username = %s AND password = %s"
        db_cursor.execute(member_query, (username, password))
        member_result = db_cursor.fetchone()

        if member_result:
            member_id = member_result[0]
            session['member_id'] = member_id
            return redirect(url_for('member_dashboard'))

    return render_template('login.html')


@app.route('/upload_meal_plan/<int:member_id>', methods=['POST'])
def upload_meal_plan(member_id):
    if 'admin_logged_in' in session and session['admin_logged_in']:
        if 'meal_plan' in request.files:
            meal_plan = request.files['meal_plan']
            # Save the uploaded file to a folder (e.g., uploads)
            meal_plan.save(os.path.join(app.config['UPLOAD_FOLDER'], meal_plan.filename))
            # Update the member record in the database with the meal plan image filename
            cursor = db.cursor()
            query = "UPDATE member SET meal_plan = %s WHERE member_id = %s"
            cursor.execute(query, (meal_plan.filename, member_id))
            db.commit()
            flash('Meal plan image uploaded successfully!')
        else:
            flash('No meal plan image uploaded.')
        return redirect(url_for('trainer_dashboard'))  # Redirect to trainer dashboard
    else:
        return redirect(url_for('login'))  # Redirect


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        cursor = db.cursor()
        cursor.execute("SELECT trainer_id,name, specialization, contact_number, email,status FROM trainer")
        trainers = cursor.fetchall()
        return render_template('admin_dash.html', trainers=trainers)

    else:
        return redirect(url_for('login'))


@app.route('/add_trainer', methods=['POST'])
def add_trainer():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # Insert the data into the 'trainer' table
        query = "INSERT INTO trainer (name, specialization, contact_number, email,username,password) VALUES (%s, %s, " \
                "%s, %s,%s,%s) "
        values = (name, specialization, phone_number, email, username, password)

        try:
            db_cursor.execute(query, values)
            db.commit()
            flash('Trainer added successfully!')

        except Exception as e:
            flash('Error occurred while adding trainer: ' + str(e))

        return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after adding trainer
    else:
        return redirect(url_for('login'))  # Redirect to login page if not logged in as admin


@app.route('/trainer_member/<int:trainer_id>')
def trainer_member(trainer_id):
    if 'admin_logged_in' in session and session['admin_logged_in']:
        cursor = db.cursor()
        query = "SELECT photo, first_name, last_name, email, phone_number,status,member_id FROM member WHERE " \
                "member_id IN (SELECT member_id FROM member_trainer WHERE trainer_id = %s) "
        cursor.execute(query, (trainer_id,))
        members1 = cursor.fetchall()

        # Prepare data for rendering the template
        data = []
        for member in members1:
            member_data = {
                'photo_filename': os.path.basename(member[0]),
                'first_name': member[1],
                'last_name': member[2],
                'email': member[3],
                'phone_number': member[4],
                'status': member[5],
                'member_id': member[6]
            }
            data.append(member_data)

        return render_template('trainer_member.html', data=data)

    else:
        return redirect(url_for('login'))


@app.route('/trainer_dashboard')
def trainer_dashboard():
    db_cursor = db.cursor()

    try:
        db_cursor.execute("""
            SELECT 
                m.first_name, 
                m.last_name, 
                m.email, 
                m.photo, 
                m.status, 
                m.member_id, 
                dp.progress_percentage
            FROM 
                member m
            LEFT JOIN 
                daily_progress dp ON m.member_id = dp.member_id
        """)

        members_with_progress = []
        for row in db_cursor.fetchall():
            member_with_progress = {
                'first_name': row[0],
                'last_name': row[1],
                'email': row[2],
                'photo_filename': row[3],
                'status': row[4],
                'member_id': row[5],
                'progress_percentage': row[6]
            }
            members_with_progress.append(member_with_progress)
    except Exception as e:
        print(f"Error fetching data: {e}")
        members_with_progress = []
    finally:
        db_cursor.close()

    return render_template('trainer_dash.html', members_with_progress=members_with_progress)


@app.route('/member_dashboard')
def member_dashboard():
    # Check if the member is logged in
    if 'member_id' not in session:
        # Redirect to the login page or handle the case where the user is not logged in
        return redirect(url_for('login'))

    # Get the logged-in member's ID from the session
    member_id = session['member_id']

    # Create a cursor object to execute SQL queries
    cursor = db.cursor()

    # Fetch activities for the logged-in member where the activity is assigned (value = 1)
    query = f"SELECT * FROM member_activities WHERE member_id = {member_id} AND \
             (daily_warm_ups = 1 OR marching_spot_jogging = 1 OR wall_push_ups = 1 OR \
             squats = 1 OR mic_chest_press_seated_row = 1 OR mic_leg_press = 1 OR \
             cycle = 1 OR stretch_walk = 1 OR bench_up_down_step = 1 OR \
             db_shoulder_press_triceps_biceps = 1 OR walker = 1 OR kicks = 1 OR \
             crunches_hip_raises = 1 OR cycling_reverse_cycling = 1 OR reverse_curl = 1 OR \
             single_leg_up_down = 1 OR suryanamaskar = 1 OR stretches_shavasana = 1)"

    cursor.execute(query)
    activities = cursor.fetchone()  # Assuming only one row per member

    # Check if activities were found
    if activities:
        # Convert the activities to a dictionary
        activities_dict = {
            'daily_warm_ups': activities[1],
            'marching_spot_jogging': activities[2],
            'wall_push_ups': activities[3],
            'squats': activities[4],
            'mic_chest_press_seated_row': activities[5],
            'mic_leg_press': activities[6],
            'cycle': activities[7],
            'stretch_walk': activities[8],
            'bench_up_down_step': activities[9],
            'db_shoulder_press_triceps_biceps': activities[10],
            'walker': activities[11],
            'kicks': activities[12],
            'crunches_hip_raises': activities[13],
            'cycling_reverse_cycling': activities[14],
            'reverse_curl': activities[15],
            'single_leg_up_down': activities[16],
            'suryanamaskar': activities[17],
            'stretches_shavasana': activities[18]
        }
    else:
        activities_dict = {}  # Empty dictionary if no activities were found

    # Render the template with the activities passed to it
    return render_template('member_dash.html', activities=activities_dict)


from flask import jsonify

@app.route('/insert_progress', methods=['POST'])
def insert_progress():
    if request.method == 'POST':
        progress_percentage = request.form['progress_percentage']
        member_id = session.get('member_id')  # Get member ID from session
        if not member_id:
            return jsonify({'error': 'Member ID not found in session.'}), 400

        # Check if progress data for the same member and date already exists
        db_cursor.execute("SELECT COUNT(*) FROM daily_progress WHERE member_id = %s AND progress_date = CURDATE()", (member_id,))
        count = db_cursor.fetchone()[0]

        if count > 0:
            # Update progress_percentage for the same member and date
            update_query = "UPDATE daily_progress SET progress_percentage = %s WHERE member_id = %s AND progress_date = CURDATE()"
            values = (progress_percentage, member_id)
            db_cursor.execute(update_query, values)
            db.commit()
            return jsonify({'message': 'Progress updated successfully.'}), 200
        else:
            # Insert progress into daily_progress table
            insert_query = "INSERT INTO daily_progress (member_id, progress_date, progress_percentage) VALUES (%s, CURDATE(), %s) "
            values = (member_id, progress_percentage)
            db_cursor.execute(insert_query, values)
            db.commit()
            return jsonify({'message': 'Progress inserted successfully.'}), 200
    else:
        return jsonify({'error': 'Invalid request method.'}), 400



@app.route('/registration')
def registration():
    return render_template('Registration.html')


@app.route('/workout/<int:member_id>', methods=['GET', 'POST'])
def workout(member_id):
    return render_template('Workout_plan.html', member_id=member_id)


@app.route('/toggle_status/<int:trainer_id>', methods=['POST'])
def toggle_status(trainer_id):
    if 'admin_logged_in' in session and session['admin_logged_in']:
        new_status = request.form.get('status')
        # Update the status in your database for the specified trainer_id
        # Example code assuming you have a database connection and trainer table
        cursor = db.cursor()
        query = "UPDATE trainer SET status = %s WHERE trainer_id = %s"
        cursor.execute(query, (new_status, trainer_id))
        db.commit()
        flash('Trainer status updated successfully!')
        return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in as admin


@app.route('/toggle_member_status/<int:member_id>', methods=['POST'])
def toggle_member_status(member_id):
    if 'admin_logged_in' in session and session['admin_logged_in']:
        new_status = request.form.get('status')

        # Update the status in your database for the specified member_id
        cursor = db.cursor()
        query = "UPDATE member SET status = %s WHERE member_id = %s"
        cursor.execute(query, (new_status, member_id))
        db.commit()

        flash('Member status updated successfully!')
        cursor.execute("SELECT trainer_id FROM member_trainer WHERE member_id = %s", (member_id,))
        trainer_id = cursor.fetchone()[0]  # Assuming trainer_id is the first column

        return redirect(url_for('trainer_member', trainer_id=trainer_id))  # Redirect to admin dashboard
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in as admin


@app.route('/membership', methods=['GET', 'POST'])
def membership():
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        blood_group = request.form['blood_group']
        has_heart_problem = request.form.get('has_heart_problem') == 'on'
        has_hypertension = request.form.get('has_hypertension') == 'on'
        has_diabetes = request.form.get('has_diabetes') == 'on'
        has_breathing_problem = request.form.get('has_breathing_problem') == 'on'
        has_hernia = request.form.get('has_hernia') == 'on'
        has_fracture_dislocation = request.form.get('has_fracture_dislocation') == 'on'
        has_back_pain = request.form.get('has_back_pain') == 'on'
        has_knee_problem = request.form.get('has_knee_problem') == 'on'
        has_recent_surgery = request.form.get('has_recent_surgery') == 'on'
        recent_surgery_details = request.form['recent_surgery_details']
        height = request.form['height']
        weight = request.form['weight']

        # Insert data into the member table
        query = """
        INSERT INTO member (username, password, first_name, last_name, date_of_birth, gender, email, phone_number, address, 
        blood_group, has_heart_problem, has_hypertension, has_diabetes, has_breathing_problem, has_hernia, 
        has_fracture_dislocation,has_back_pain, has_knee_problem, has_recent_surgery, recent_surgery_details, height, weight)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )
        """
        values = (
            username, password, first_name, last_name, date_of_birth, gender, email, phone_number, address, blood_group,
            has_heart_problem, has_hypertension, has_diabetes, has_breathing_problem, has_hernia,
            has_fracture_dislocation,
            has_back_pain, has_knee_problem, has_recent_surgery, recent_surgery_details, height, weight
        )
        db_cursor.execute(query, values)
        db.commit()
    return render_template('membership_plans.html')


@app.route('/select_plan', methods=['GET', 'POST'])
def select_plan():
    if request.method == 'GET':
        selected_plan = request.args.get('title')
        fees = plan_fees.get(selected_plan)
        print(fees)

        username = session['username']
        query = "SELECT member_id FROM member WHERE username = %s"
        db_cursor.execute(query, (username,))
        result = db_cursor.fetchone()

        if result:
            member_id = result[0]  # Assuming member_id is the first column in the result
            session['member_id'] = member_id

            session['fees'] = fees  # Set the fees in session
            # Store the plan title and member_id in the member_plan table
            query_insert = "INSERT INTO member_plans (member_id, plan_title, fees) VALUES (%s, %s, %s)"
            values = (member_id, selected_plan, fees)
            db_cursor.execute(query_insert, values)
            db.commit()
    return redirect(url_for('view_profile'))


@app.route('/upload_post', methods=['POST'])
def upload_post():
    if request.method == 'POST':
        member_id = session['member_id']
        print(member_id)
        title = request.form['title']
        post_date = datetime.date.today()
        post_description = request.form['text_description']

        # Insert the post into the posts table
        query = "INSERT INTO posts (member_id, post_description, post_date,title) VALUES (%s, %s,%s,%s)"
        values = (member_id, post_description, post_date, title)
        db_cursor.execute(query, values)
        db.commit()

        flash('Post uploaded successfully!')
        return redirect(url_for('trainer_dashboard'))  # Redirect to trainer dashboard after uploading


@app.route('/view_profile')
def view_profile():
    if 'member_id' in session:
        member_id = session['member_id']

        # Fetch user information from the member table
        query_member = "SELECT first_name, last_name, phone_number, email FROM member WHERE member_id = %s"
        db_cursor.execute(query_member, (member_id,))
        member_info = db_cursor.fetchone()

        # Fetch membership plan information from the member_plans table
        query_member_plan = "SELECT plan_title, fees FROM member_plans WHERE member_id = %s"
        db_cursor.execute(query_member_plan, (member_id,))
        member_plan_info = db_cursor.fetchone()

        # Check if both member and membership plan information exist
        if member_info and member_plan_info:
            first_name, last_name, phone_number, email = member_info
            plan_title, fees = member_plan_info
            session['plan_title'] = plan_title;

            # Render the profile template with the fetched information
            return render_template('Payment.html', first_name=first_name, last_name=last_name,
                                   phone_number=phone_number, email=email, plan_title=plan_title, fees=fees)

    else:
        # Handle if member_id is not in the session
        return redirect(url_for('/login'))  # Redirect to login route if session is not available


@app.route('/proceed', methods=['POST'])
def proceed():
    if request.method == 'POST':
        member_id = session.get('member_id')
        transaction_id = request.form['transaction_id']
        payment_date = datetime.date.today()
        fees = session['fees']

        # Insert payment information into the payment table
        query = "INSERT INTO payment (member_id, transaction_id, payment_date, fees) VALUES (%s, %s, %s, %s)"
        values = (member_id, transaction_id, payment_date, fees)
        db_cursor.execute(query, values)
        db.commit()

        plan_title = session['plan_title']
        query = "SELECT trainer_id FROM trainer WHERE specialization = %s"
        db_cursor.execute(query, (plan_title,))
        trainers = db_cursor.fetchall()

        if trainers:
            selected_trainer = random.choice(trainers)
            assignment_date = datetime.date.today()
            member_trainer_query = "INSERT INTO member_trainer (member_id, trainer_id, assignment_date) VALUES (%s, " \
                                   "%s, %s) "
            member_trainer_values = (member_id, selected_trainer[0], assignment_date)
            db_cursor.execute(member_trainer_query, member_trainer_values)
            db.commit()

    if 'photo' in request.files:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Create the upload folder if it doesn't exist
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            file.save(file_path)

            cursor = db.cursor()
            member_id = session.get('member_id')
            query = "UPDATE member SET photo = %s WHERE member_id = %s"
            values = (file_path, member_id)
            cursor.execute(query, values)
            db.commit()
            flash('File uploaded successfully')

    registration_success = True
    return render_template('login.html', registration_success=registration_success)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/assign_activities', methods=['POST'])
def assign_activities():
    if request.method == 'POST':
        # Get member_id from session or request
        member_id = request.form.get('member_id')

        # Get selected activities from the form
        activities = request.form.getlist('activities[]')

        # Example code to insert activities into the member_activities table
        insert_query = """
        INSERT INTO member_activities 
        (member_id, daily_warm_ups, marching_spot_jogging, wall_push_ups, squats, mic_chest_press_seated_row, 
        mic_leg_press, cycle, stretch_walk, bench_up_down_step, db_shoulder_press_triceps_biceps, walker, kicks, 
        crunches_hip_raises, cycling_reverse_cycling, reverse_curl, single_leg_up_down, suryanamaskar, stretches_shavasana) 
        VALUES (%s, %s, %s, %s, %s,
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Generate parameter values for the placeholders
        values = [member_id] + [str(int(activity in activities)) for activity in [
            'daily_warm_ups', 'marching_spot_jogging', 'wall_push_ups', 'squats', 'mic_chest_press_seated_row',
            'mic_leg_press', 'cycle', 'stretch_walk', 'bench_up_down_step', 'db_shoulder_press_triceps_biceps',
            'walker', 'kicks', 'crunches_hip_raises', 'cycling_reverse_cycling', 'reverse_curl', 'single_leg_up_down',
            'suryanamaskar', 'stretches_shavasana'
        ]]

        # Execute the insert query
        db_cursor.execute(insert_query, values)
        db.commit()

        return redirect(url_for('trainer_dashboard'))  # Redirect to login route if session is not available

    else:
        return "Invalid request method"


if __name__ == '__main__':
    app.run(debug=True)
