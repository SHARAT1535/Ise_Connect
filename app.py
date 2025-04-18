from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import base64
import json
from dotenv import load_dotenv
import requests
import time
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from firebase_admin import auth 



import os
from werkzeug.utils import secure_filename

uploadcare_key = os.getenv("UPLOADCARE_PUBLIC_KEY")



app = Flask(__name__)
app.secret_key = 'your_secret_key'  

load_dotenv()

encoded_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")

# decode the stringand convert to python diction
if encoded_key:
    decoded_bytes = base64.b64decode(encoded_key)
    service_account_info = json.loads(decoded_bytes)

    # Initialize Firebase
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_BASE64 not found in .env file")

@app.route('/')
def hello():
    return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        api_key = os.getenv("FIREBASE_API_KEY")  # Add this to your .env file!
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            user_data = response.json()
            session['user_id'] = user_data['localId']
            session['email'] = user_data['email']
            flash("Login successful!", "success")
            return redirect(url_for('student_home'))
        else:
            error_msg = response.json().get("error", {}).get("message", "Login failed.")
            flash(f"Error: {error_msg}", "danger")
            return render_template('login.html')

    return render_template('login.html')


@app.route('/about_ise', methods=['GET', 'POST'])
def about_ise():
    return render_template('about_ise.html')


@app.route('/student_home')
def student_home():
    if 'user_id' in session:
        user_id = session['user_id']
        user_doc=db.collection('user_data').document(user_id).get()
        if user_doc.exists:
            user_data=user_doc.to_dict()
            return render_template('student_home.html', user=user_data)
        else:
            return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        
        name = request.form['name']
        usn = request.form['usn']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('signup'))

        try:
            user = auth.create_user(
                email=email,
                password=password
            )
            user_data = {
                'uid': user.uid,  
                'name': name,
                'usn': usn,
                'email': email,
                'created_at': firestore.SERVER_TIMESTAMP  
            }

            db.collection('user_data').document(user.uid).set(user_data)

          
            flash("User created successfully!", "success")
            return redirect(url_for('login'))  

        except Exception as e:
            flash(f"Error creating user: {str(e)}", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/profileedit', methods=['GET', 'POST'])
def profileedit():  
    if 'user_id' in session:
        user_id = session['user_id']
        user_doc=db.collection('user_data').document(user_id).get()
        if user_doc.exists:
            user_data=user_doc.to_dict()
            uploadcare_key = os.getenv("UPLOADCARE_PUBLIC_KEY")
            return render_template('profileedit.html', user=user_data, uploadcare_key=uploadcare_key)
        else:
            return redirect(url_for('login'))
    return redirect(url_for('login'))



""" 

@app.route('/update_profile', methods=['POST'])
def update_profile():
    # Logic to handle form data goes here
    # For example:
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    name = request.form.get('name')
    usn = request.form.get('usn')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    internship = request.form.get('internship')
    working_at = request.form.get('working_at')
    experience = request.form.get('experience')
    about_me = request.form.get('about_me')
    skills = request.form.get('skills')
    linkedin = request.form.get('linkedin')
    github = request.form.get('github')
    profile_pic_url = request.form.get('profile_pic_url')

    if profile_pic_url:
        user_data['profile_pic_url'] = profile_pic_url
    user_data = {
        'name': name,
        'usn': usn,
        'email': email,
        'phone': phone,
        'password': password,    
        'internship': internship,
        'working_at': working_at,
        'experience': experience,
        'about_me': about_me,    
        'skills': skills,
        'linkedin': linkedin,    
        'github': github
    }





    db.collection('user_data').document(user_id).update(user_data)





    # Example: handle profile picture upload
    profile_pic = request.files.get('profile_pic')
    if profile_pic:
        filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join('static/uploads', filename))  # Update the path accordingly

    # Update in Firebase or DB here...

    return redirect(url_for('student_home'))  # Redirect back to student home after update




 """


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('user_data').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("User not found.", "error")
        return redirect(url_for('student_home'))

    user_data = user_doc.to_dict()

    # Update basic fields
    updates = {
        'name': request.form.get('name'),
        'usn': request.form.get('usn'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'password': request.form.get('password'),    
        'internship': request.form.get('internship'),
        'working_at': request.form.get('working_at'),
        'experience': request.form.get('experience'),
        'about_me': request.form.get('about_me'),    
        'skills': request.form.get('skills'),
        'linkedin': request.form.get('linkedin'),    
        'github': request.form.get('github')
    }

    # Uploadcare profile picture URL
    profile_pic_url = request.form.get('profile_pic_url')
    if profile_pic_url:
        updates['profile_pic_url'] = profile_pic_url

    user_ref.update(updates)

    flash("Profile updated successfully!", "success")
    return redirect(url_for('student_home'))




@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
