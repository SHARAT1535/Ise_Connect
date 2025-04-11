from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import time
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for sessions & flash messages

# Initialize Firebase Admin SDK
#cred = credentials.Certificate('iseconnect-ad8b0-firebase-adminsdk-fbsvc-e092490c1a.json')
#firebase_admin.initialize_app(cred)
#db = firestore.client()

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
