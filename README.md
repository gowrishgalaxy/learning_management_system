# Learning Management System

A simple Flask-based Learning Management System for managing users, courses, videos, and enrollments.

## Features

- User registration and authentication
- Role-based dashboards for students and teachers
- Course creation and course management
- Video uploads and course content management
- Enrollment tracking and student submissions

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv my-env
   .\my-env\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Run the application:

   ```powershell
   python app.py
   ```

4. Open the application in your browser at:

   ```text
   http://127.0.0.1:5000
   ```

## Project Structure

- `app.py` - main Flask application entry point
- `models/` - database models and data layer
- `templates/` - HTML templates for views
- `static/` - CSS, images, and uploaded media files

## Notes

Make sure the `uploads/` directory exists inside `static/` for video upload functionality.

