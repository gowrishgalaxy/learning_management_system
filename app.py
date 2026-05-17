from flask import Flask, render_template, redirect, url_for, request, flash, session, abort, jsonify
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import mysql.connector
from models import db, Users, Courses, Enrollments, Video, Notes, MCQ, MCQAttempt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = \
    'mysql+mysqlconnector://lms_user:password@localhost/lms_db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'LMS'

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

app.config['UPLOAD_FOLDER'] = 'lms/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  

#bind the db to this app
db.init_app(app)

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return {'status': 'error', 'message': 'Login required'}, 401
        return f(*args, **kwargs)
    return decorated_function

def api_role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return {'status': 'error', 'message': 'Login required'}, 401
            if session.get('role') != role:
                return {'status': 'error', 'message': 'Role required'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '')
    
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        user = Users.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password', 'error')
            return render_template('login.html')
    
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True

        if user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif user.role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid user role', 'error')
            return render_template('login.html')
        
    return render_template('login.html')
    
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')    
    return redirect(url_for('home'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):

    
    def decorator(f):
        @wraps(f)

        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page', 'error')
                return redirect(url_for('login'))
            if session.get('role') != role:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    return render_template('teacher_dashboard.html')

@app.route('/users_list')
@login_required
@role_required('teacher')
def users_list():
    users = Users.query.all()
    return render_template("users_list.html", users=users)

@app.route('/courses_list')
@login_required
def courses_list():
    courses = Courses.query.all()
    return render_template("courses_list.html", courses=courses)

@app.route('/api/register', methods=['POST'])
def api_register():
    data = _get_api_data()

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '')
    role = (data.get('role') or '').strip()

    if isinstance(username, list):
        username = (username[0] or '').strip() if username else ''

    if isinstance(email, list):
        email = (email[0] or '').strip() if email else ''
    
    if isinstance(password, list):
        password = (password[0] or '') if password else ''

    if isinstance(role, list):
        role = (role[0] or '').strip() if role else ''
    

    if not username:
        return {'status': 'error', 'message': 'Username is required'}, 400
    if not email or '@' not in email:
        return {'status': 'error', 'message': 'Valid email is required'}, 400
    if not password or len(password) < 6:
        return {'status': 'error', 'message': 'Password must be at least 6 characters long'}, 400
    if role not in ['student', 'teacher']:
        return {'status': 'error', 'message': 'Invalid role'}, 400
    if Users.query.filter_by(username=username).first():
        return {'status': 'error', 'message': 'Username already exists'}, 400
    if Users.query.filter_by(email=email).first():
        return {'status': 'error', 'message': 'Email already exists'}, 400
    try:
        user = Users(
            username=username,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({
            'status': 'success', 
            'message': 'User registered successfully',
            'data': { 'id': user.id }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error', 
            'message': f'An error occurred while registering the user: {str(e)}'
        }), 500

def _get_api_data():
    #1. json body
    data = request.get_json(force=True, silent=True)
    if data and isinstance(data, dict):
        return data
    
    #2. form data
    if request.form:
        return {
            k: (v[0] if isinstance(v, list) else v)
            for k, v in request.form.items()
        }
    
    #3. try row body as a json
    if request.get_data():
        import json
        try:
            return json.loads(request.get_data().decode('utf-8'))
        except Exception as e:
            pass
        return {}
    
    #4. query string
    if request.args:
        return dict(request.args)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = _get_api_data()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '') 
    if not username or not password:
        return {'status': 'error', 'message': 'Username and password are required'}, 400
    
    user = Users.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password, password):
        return {'status': 'error', 'message': 'Invalid username or password'}, 401
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session.permanent = True
    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'data': {
            'user_id': user.id,
            'username': user.username,
            'role': user.role
        }
    }), 200

@app.route('/api/users')
@api_login_required
def api_list_users():
    users = Users.query.all()
    data = [
        {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
        for user in users
    ]
    return jsonify({'status': 'success', 'data': data}), 200

@app.route('/api/courses', methods = ['POST'])
@api_login_required
@api_role_required('teacher')
def api_create_course():

    data = _get_api_data()
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()

    teacher_id = data.get('teacher_id') or session.get('user_id')
    
    if not title:
        return jsonify({'status': 'error', 'message': 'Title is required'}), 400
    
    teacher = Users.query.filter_by(id=teacher_id, role='teacher').first()
    if not teacher:
        return jsonify({'status': 'error', 'message': 'Invalid teacher ID'}), 400
    
    try:
        course = Courses(title=title, description=description, teacher_id=teacher_id)
        db.session.add(course)
        db.session.commit()
        return jsonify({
            'status': 'success', 
            'message': 'Course created successfully',
            'data': { 'id': course.id }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error', 
            'message': f'An error occurred while creating the course: {str(e)}'
        }), 500

@app.route('/api/courses/<int:id>', methods=['PUT'])
@api_login_required
@api_role_required('teacher')
def api_update_course(id):
    course = Courses.query.get_or_404(id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    if course.teacher_id != session.get('user_id'):
        return jsonify({'status': 'error', 'message': 'You are not authorized to update this course'}), 403


    data = _get_api_data()
    title = (data.get('title') or course.title).strip()
    description = (data.get('description') or course.description or '').strip()

    if not title:
        return jsonify({'status': 'error', 'message': 'Title is required'}), 400

    try:
        course.title = title
        course.description = description
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Course updated successfully',
            'data': { 'id': course.id }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'An error occurred while updating the course: {str(e)}'
        }), 500

@app.route('/api/courses/<int:id>', methods=['DELETE'])
@api_login_required
@api_role_required('teacher')
def api_delete_course(id):
    course = Courses.query.get_or_404(id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    if course.teacher_id != session.get('user_id'):
        return jsonify({'status': 'error', 'message': 'You are not authorized to delete this course'}), 403

    try:
        Enrollments.query.filter_by(course_id=id).delete()
        db.session.delete(course)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Course deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'An error occurred while deleting the course: {str(e)}'
        }), 500

@app.route('/api/enrollments', methods=['POST'])
@api_login_required
@api_role_required('student')
def api_enroll():
    data = _get_api_data()
    course_id = data.get('course_id')

    if not course_id:
        return jsonify({'status': 'error', 'message': 'Course ID is required'}), 400

    course = Courses.query.get(course_id)
    if not course:
        return jsonify({'status': 'error', 'message': 'Course not found'}), 404

    user_id = session.get('user_id')
    
    exsiting = Enrollments.query.filter_by(user_id=user_id, course_id=course_id).first()
    if exsiting:
        return jsonify({'status': 'error', 'message': 'You are already enrolled in this course'}), 400
    
    try:
        enrollment = Enrollments(user_id=user_id, course_id=course_id, status='pending')
        db.session.add(enrollment)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Enrollment created successfully',
            'data': { 'id': enrollment.id }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'An error occurred while creating the enrollment: {str(e)}'
        }), 500

@app.route('/api/enrollments')
@api_login_required
def api_list_enrollments():
    user_id = session.get('user_id')
    role = session.get('role')
    course_id = request.args.get('course_id', type=int)
    #/api/enrollments?course_id=1
    if role == 'student':
        enrollments = Enrollments.query.filter_by(user_id=user_id).order_by(Enrollments.created_at.desc()).all()
    elif role == 'teacher' and course_id:
        course = Courses.query.get(course_id)
        if not course or course.teacher_id != user_id:
            return jsonify({'status': 'error', 'message': 'Course not found or you are not the teacher of this course'}), 404
        enrollments = Enrollments.query.filter_by(course_id=course_id).order_by(Enrollments.created_at.desc()).all()
    else:
        return jsonify({'status': 'error', 'message': 'Invalid role or missing course_id for teacher'}), 400

    data = [
        {
            'id': enrollment.id,
            'course_id': enrollment.course_id,
            'course_title': enrollment.course.title,
            'user_id': enrollment.user_id,
            'username': enrollment.user.username,
            'status': enrollment.status,
            'created_at': enrollment.created_at.isoformat()
        }
        for enrollment in enrollments
    ]
    return jsonify({'status': 'success', 'data': data}), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '')
        role = (request.form.get('role') or '').strip()

        if not username:
            flash('Username is required', 'error')
            return render_template('register.html', error='Username is required')
        if not email:
            flash('Email is required', 'error')
            return render_template('register.html', error='Email is required', username=username)
        if '@' not in email:
            flash('Invalid email format', 'error')
            return render_template('register.html', error='Invalid email format', username=username)
        
        if not password:
            flash('Password is required', 'error')
            return render_template('register.html', error='Password is required', username=username, email=email, role=role)

        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html', error='Password must be at least 6 characters long', username=username, email=email, role=role)

        if role not in ['student', 'teacher']:
            flash('Invalid role', 'error')
            return render_template('register.html', error='Invalid role', username=username, email=email, role=role)

        if Users.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html', error='Username already exists', username=username, email=email, role=role)

        if Users.query.filter_by(email=email).first():
            flash('Email already exists', 'error')  
            return render_template('register.html', error='Email already exists', username=username, email=email, role=role)


        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            user = Users(username=username, email=email, password=hashed_password, role=role)
            db.session.add(user)
            db.session.commit()
            flash('User registered successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while registering the user: {str(e)}', 'error')
            return render_template('register.html', error=str(e), username=username, email=email, role=role)

    return render_template('register.html')



@app.route('/user/<int:id>')
@login_required
@role_required('teacher')
def user_detail(id):
    user = Users.query.get(id)
    return render_template('user_detail.html', user=user)


@app.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def user_edit(id):
    user = Users.query.get_or_404(id)
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '')
        role = (request.form.get('role') or '').strip()

        # backend validation
        if not username:
            flash('Username is required', 'error')
            return render_template('user_edit.html', error='Username is required', user=user)
            
            
        if not email:
            flash('Email is required', 'error')
            return render_template('user_edit.html', error='Email is required', user=user)  

        if '@' not in email:
            flash('Invalid email format', 'error')
            return render_template('user_edit.html', error='Invalid email format', user=user)   
        
        if not password:
            flash('Password is required', 'error')
            return render_template('user_edit.html', error='Password is required', user=user)   
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('user_edit.html', error='Password must be at least 6 characters long', user=user)        
        
        if role not in ['student', 'teacher']:
            flash('Invalid role', 'error')
            return render_template('user_edit.html', error='Invalid role', user=user)   
        
        if Users.query.filter(Users.username == username, Users.id != id).first():
            flash('Username already exists', 'error')       
            return render_template('user_edit.html', error='Username already exists', user=user)    

        if Users.query.filter(Users.email == email, Users.id != id).first():
            flash('Email already exists', 'error')  
            return render_template('user_edit.html', error='Email already exists', user=user)
        
        try:
            user.username = username
            user.email = email
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
            user.role = role

            db.session.commit()
            flash('User updated successfully', 'success')
            return render_template('user_edit.html', success='User updated successfully', user=user)
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the user: {str(e)}', 'error')
            return render_template('user_edit.html', error=str(e), user=user)

    return render_template('user_edit.html', user=user)

@app.route('/user/delete/<int:id>', methods=['GET','POST'])
@login_required
@role_required('teacher')
def user_delete(id):
    user = Users.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('users_list'))

@app.route('/my-enrollments')
@login_required
@role_required('student')
def my_enrollments():
    user_id = session.get('user_id')
    enrollments = Enrollments.query.filter_by(user_id=user_id).order_by(Enrollments.created_at.desc()).all()
    return render_template('my_enrollments.html', enrollments=enrollments)

@app.route('/course/<int:id>/enrollments')
@login_required
@role_required('teacher')
def course_enrollments(id):
    course = Courses.query.get_or_404(id)
    if course.teacher_id != session.get('user_id'):
        abort(403)  # Forbidden

    enrollments = Enrollments.query.filter_by(course_id=id).order_by(Enrollments.created_at.desc()).all()
    return render_template('course_enrollments.html', course=course, enrollments=enrollments)

@app.route('/enrollment/<int:id>/approve', methods=['POST'])
@login_required
@role_required('teacher')
def enrollment_approve(id):
    enrollment = Enrollments.query.get_or_404(id)

    course = Courses.query.get(enrollment.course_id)
    if course.teacher_id != session.get('user_id'):
        abort(403)  # Forbidden

    if enrollment.status != 'pending':
        flash('Only pending enrollments can be approved', 'error')
        return redirect(url_for('course_enrollments', id=enrollment.course_id))

    
    enrollment.status = 'enrolled'
    db.session.commit()
    return redirect(url_for('course_enrollments', id=enrollment.course_id))


@app.route('/enrollment/<int:id>/reject', methods=['POST'])
@login_required 
@role_required('teacher')
def enrollment_reject(id):
    enrollment = Enrollments.query.get_or_404(id)   
    course = Courses.query.get(enrollment.course_id)
    if course.teacher_id != session.get('user_id'):
        abort(403)  # Forbidden
    if enrollment.status != 'pending':
        flash('Only pending enrollments can be rejected', 'error')
        return redirect(url_for('course_enrollments', id=enrollment.course_id))

    enrollment.status = 'rejected'
    db.session.commit()
    return redirect(url_for('course_enrollments', id=enrollment.course_id))


@app.route('/course/create', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def course_create():
    
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = (request.form.get('description') or '').strip()
        teacher_id = (request.form.get('teacher_id') or '')

        if not title:
            flash('Title is required', 'error')
            teachers = Users.query.filter_by(role = 'teacher').all()
            return render_template('course_create.html', error='Title is required', teachers=teachers, title=title, description=description, teacher_id=teacher_id )
        
        if not teacher_id:
            flash('Teacher is required', 'error')
            teachers = Users.query.filter_by(role = 'teacher').all()
            return render_template('course_create.html', error='Teacher is required', teachers=teachers, title=title, description=description, teacher_id=teacher_id )

        try:
            teacher_id = int(teacher_id)
        except ValueError:
            flash('Invalid teacher ID', 'error')
            teachers = Users.query.filter_by(role = 'teacher').all()
            return render_template('course_create.html', error='Invalid teacher ID', teachers=teachers, title=title, description=description, teacher_id=teacher_id )

        teacher = Users.query.filter_by(id=teacher_id, role='teacher').first()

        if not teacher:
            flash('Invalid teacher ID', 'error')
            teachers = Users.query.filter_by(role = 'teacher').all()
            return render_template('course_create.html', error='Invalid teacher ID', teachers=teachers, title=title, description=description, teacher_id=teacher_id )

        try:
            course = Courses(title=title, description=description, teacher_id=teacher_id)
            db.session.add(course)
            db.session.commit()
            flash('Course created successfully', 'success')
            return redirect(url_for('courses_list'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the course', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_create.html', teachers=teachers, title=title, description=description, teacher_id=teacher_id )

    teachers = Users.query.filter_by(role='teacher').all()
    return render_template('course_create.html', teachers=teachers)

@app.route('/api/courses', methods=['GET'])
@api_login_required
def api_courses_list():
    courses = Courses.query.all()
    
    data = [
        {
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'teacher_id': course.teacher_id,
            'status': course.status
        }
        for course in courses
    ]
    return {'status': 'success', 'data': data}, 200


@app.route('/course/<int:id>')
@login_required
def course_detail(id):
    course = Courses.query.get_or_404(id)
    user_enrollment = None

    if session.get('role') == 'student' and session.get('user_id'):
        user_enrollment = Enrollments.query.filter_by(user_id=session['user_id'], course_id=id).first()

    return render_template('course_detail.html', course=course, user_enrollment=user_enrollment)

@app.route('/api/course/<int:id>')
@api_login_required
def api_course_detail(id):
    course = Courses.query.get_or_404(id)

    if not course:
        return {'status': 'error', 'message': 'Course not found'}, 404

    data = {
        'id': course.id,
        'title': course.title,
        'description': course.description,
        'teacher_id': course.teacher_id,
        'teacher': course.teacher.username
    }
    return jsonify({'status': 'success', 'data': data}), 200



@app.route('/course/<int:id>/enroll', methods=['POST'])
@login_required
@role_required('student')
def course_enroll(id):
    course = Courses.query.get_or_404(id)
    user_id = session.get('user_id')
    
    # Check 
    existing_enrollment = Enrollments.query.filter_by(user_id=user_id, course_id=id).first()
    
    if not existing_enrollment:
        try:
            enrollment = Enrollments(user_id=user_id, course_id=id, status='pending')
            db.session.add(enrollment)
            db.session.commit()
            flash('Successfully enrolled in the course', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while enrolling in the course', 'error')
    else:
        flash('You are already enrolled in this course', 'error')

    return redirect(url_for('course_detail', id=id))

@app.route('/course/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def course_edit(id):
    course = Courses.query.get_or_404(id)
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = (request.form.get('description') or '').strip()
        teacher_id = (request.form.get('teacher_id') or '').strip()
        
        if not title:
            flash('Title is required', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_edit.html', error='Title is required', course=course, teachers=teachers)
    
        if not teacher_id:
            flash('Teacher is required', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_edit.html', error='Teacher is required', course=course, teachers=teachers)
        try:            
            teacher_id = int(teacher_id)
        except ValueError:
            flash('Invalid teacher ID', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_edit.html', error='Invalid teacher ID', course=course, teachers=teachers)
        
        teacher = Users.query.filter_by(id=teacher_id, role='teacher').first()

        if not teacher:
            flash('Invalid teacher ID', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_edit.html', error='Invalid teacher ID', course=course, teachers=teachers)
        
        try:
            course.title = title
            course.description = description
            course.teacher_id = teacher_id
            
            db.session.commit()
            flash('Course updated successfully', 'success')
            return redirect(url_for('courses_list'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the course', 'error')
            teachers = Users.query.filter_by(role='teacher').all()
            return render_template('course_edit.html', course=course, teachers=teachers)

    teachers = Users.query.filter_by(role='teacher').all()
    return render_template('course_edit.html', course=course, teachers=teachers)

@app.route('/course/delete/<int:id>', methods=['GET','POST'])
@login_required
@role_required('teacher')
def course_delete(id):
    course = Courses.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    return redirect(url_for('courses_list'))


@app.route('/course/<int:id>/video/create', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def video_create(id):
    course = Courses.query.get_or_404(id)

    if course.teacher_id != session.get('user_id'):
            abort(403)  # Forbidden

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        file = request.files.get('file')

        if not title:
            flash('Title is required', 'error')
            return render_template('video_form.html', course=course)

        if not file or file.filename == '':
            flash('Video file is required', 'error')
            return render_template('video_form.html', course=course, title=title)

        filename = secure_filename(file.filename)

        if not filename:
            flash('Invalid filename', 'error')
            return render_template('video_form.html', course=course, title=title)

        upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'videos')
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(filename)[1] or '.mp4'

        video_order = Video.query.filter_by(course_id=course.id).count() + 1
        unique_name = f"{course.id}_{video_order}{ext}"
        
        
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)

        rel_path = f"uploads/videos/{unique_name}"

        
        video = Video(course_id=course.id, title=title, file_path=rel_path, order=video_order)
        

        db.session.add(video)
        db.session.commit()

        flash('Video uploaded successfully', 'success')
        return redirect(url_for('videos_list', id=course.id))
        

    return render_template('video_form.html', course=course)

@app.route('/course/<int:id>/videos')
@login_required
def videos_list(id):
    course = Courses.query.get_or_404(id)
    videos = Video.query.filter_by(course_id=course.id).order_by(Video.order, Video.id).all()
    return render_template('videos_list.html', course=course, videos=videos)


@app.route('/video/delete/<int:id>', methods=['POST'])
@login_required
@role_required('teacher')
def video_delete(id):
    video = Video.query.get_or_404(id)
    course = Courses.query.get_or_404(video.course_id)

    if course.teacher_id != session.get('user_id'):
        abort(403)  # Forbidden

    db.session.delete(video)
    db.session.commit()
    flash('Video deleted successfully', 'success')
    return redirect(url_for('videos_list', id=course.id))

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'),403


with app.app_context():
        db.create_all()
        print("Tables created successfully")

if __name__=="__main__":
    app.run(debug=True)