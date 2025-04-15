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

    return render_template('login.html')

@app.route('/about_ise', methods=['GET', 'POST'])
def about_ise():
    return render_template('about_ise.html')




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
                'name':name,
                'usn':usn,
                'email':email,
                'created_at': firestore.SERVER_TIMESTAMP

            }
            db.collection('user_data').document(user.uid).set(user_data)
            flash("User created successfully!", "success")
            return redirect(url_for('login')) 

        except Exception as e:
            flash(f"Error creating user: {str(e)}", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')



if __name__ == '__main__':
    app.run(debug=True)
