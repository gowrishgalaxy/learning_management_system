from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'Teacher'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class Courses(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')  # 'draft' or 'pushed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship('Users', backref='courses')

    def __repr__(self):
        return f"<Course {self.title} by Teacher ID {self.teacher_id}>"

class Enrollments(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending' or 'enrolled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('Users', backref='enrollments')
    course = db.relationship('Courses', backref='enrollments')

    def __repr__(self):
        return f"<Enrollment User ID {self.user_id} in Course ID {self.course_id}>"

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Courses', backref='videos')

    def __repr__(self):
        return f"<Video {self.title}>"

class Notes(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Courses', backref='notes')

    def __repr__(self):
        return f"<Note {self.title}>"

class MCQ(db.Model):
    __tablename__ = 'mcqs'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(10), nullable=False)  # 'A', 'B', 'C', or 'D'
    marks = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Courses', backref='mcqs')

    def __repr__(self):
        return f"<MCQ {self.question[:50]}...>"

class MCQAttempt(db.Model):
    __tablename__ = 'mcq_attempt'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mcq_id = db.Column(db.Integer, db.ForeignKey('mcqs.id'), nullable=False)
    selected_answer = db.Column(db.String(10), nullable=False)  # 'A', 'B', 'C', or 'D'
    score = db.Column(db.Integer, default=0)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('Users', backref='mcq_attempt')
    mcq = db.relationship('MCQ', backref='attempts')

    def __repr__(self):
        return f"<MCQAttempt User = {self.user_id} MCQ = {self.mcq_id} score = {self.score}>"