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
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url



import os
from werkzeug.utils import secure_filename
load_dotenv()
uploadcare_key = os.getenv("UPLOADCARE_PUBLIC_KEY")
API_KEY = "AIzaSyC1Y1TFKP0b-L7aFiNanvvjLdy6ufmR998"



import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Cloudinary configuration
cloudinary.config( 
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.getenv("CLOUDINARY_API_KEY"), 
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)







app = Flask(__name__)
app.secret_key = 'your_secret_key'  



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
""" 
@app.route('/')
def hello():
    if 'user_id' in session:
        student_info = session.get('student')
        return render_template('index.html', student_info=student_info)
    return render_template('index.html')

"""

@app.route('/')
def hello():
    student_info = session.get('student')
    return render_template('index.html', student_info=student_info)


from flask import session

@app.route('/alumni')
def alumni_page():
    db = firestore.client()
    users_ref = db.collection('user_data')

    current_uid = session.get('user_id')  # Correct key here

    alumni_query = users_ref.where('role', '==', 'Alumni')
    alumni_docs = alumni_query.stream()

    alumni_list = []
    for doc in alumni_docs:
        if doc.id == current_uid:
            continue  # Exclude the currently signed-in user
        data = doc.to_dict()
        alumni_list.append({
            'name': data.get('name', 'N/A'),
            'working_at': data.get('working_at', 'N/A'),
            'experience': data.get('experience', 'N/A'),
            'about_me': data.get('about_me', ''),
            'profile_pic_url': data.get('profile_pic_url')
        })

    return render_template('alumni.html', alumni_list=alumni_list)





@app.route('/alumni')
def alumni_list():
    alumni_docs = db.collection('users').where('role', '==', 'alumni').stream()
    alumni_list = []
    for doc in alumni_docs:
        data = doc.to_dict()
        data['uid'] = doc.id 
        alumni_list.append(data)
    
    return render_template('alumni.html', alumni_list=alumni_list)



@app.route('/chat/<other_uid>', methods=['GET'])
def chat(other_uid):
    current_uid = session.get('user_id')
    if current_uid:
        return render_template('chat.html', current_uid=current_uid, other_uid=other_uid)
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in


def send_message(current_uid, other_uid, message):
    chat_id = "_".join(sorted([current_uid, other_uid]))
    db.collection("chats").doc(chat_id).collection("messages").add({
        "sender_id": current_uid,
        "receiver_id": other_uid,
        "message": message,
        "timestamp": firestore.SERVER_TIMESTAMP
    })





@app.route('/request_alumni', methods=['POST'])
def request_alumni():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    user_id = current_user.id  # Assuming current_user holds the authenticated user's info
    
    # Update the alumni_request_status to 'pending'
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'pending'
    })
    
    flash("Your alumni request has been submitted and is pending approval.", "success")
    return redirect(url_for('student_home'))  # Or wherever you want to redirect after the request

@app.route('/admin/alumni_requests')
def view_alumni_requests():
    if current_user.role != 'admin':
        return redirect(url_for('index'))  # Ensure only admin can access this page
    
    # Fetch all students with pending alumni requests
    pending_requests = db.collection('user_data').where('alumni_request_status', '==', 'pending').stream()
    
    # Convert query to a list of alumni request details
    requests = [request.to_dict() for request in pending_requests]
    
    return render_template('admin_alumni_requests.html', requests=requests)


@app.route('/admin/approve_request/<user_id>', methods=['POST'])
def approve_request(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))  # Ensure only admin can access this route
    
    # Update the alumni_request_status to 'approved'
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'approved'
    })
    
    flash("Alumni request has been approved.", "success")
    return redirect(url_for('view_alumni_requests'))

@app.route('/admin/reject_request/<user_id>', methods=['POST'])
def reject_request(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))  # Ensure only admin can access this route
    
    # Update the alumni_request_status to 'rejected'
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'rejected'
    })
    
    flash("Alumni request has been rejected.", "danger")
    return redirect(url_for('view_alumni_requests'))







@app.route('/admin/home')
def admin_home():
    return render_template('admin_home.html') 

@app.route('/admin/gallery')
def admin_gallery():
    return render_template('admin_gallary.html')

@app.route('/staff')
def staff():
    return render_template('staff.html')

@app.route('/student_portal')
def student_portal():
    return render_template('student_portal.html')


@app.route('/admin/users')
def admin_users():
    users_ref = db.collection('user_data')
    users = [doc.to_dict() for doc in users_ref.stream()]
    return render_template('admin_users.html', users=users)



@app.route('/admin/convert_to_alumni/<user_id>', methods=['POST'])
def convert_to_alumni(user_id):
    # Firestore example
    user_ref = db.collection('user_data').document(user_id)
    user_ref.update({'role': 'Alumni'})
    flash('User converted to Alumni successfully!', 'success')
    return redirect(url_for('admin_users'))





@app.route('/admin/library', methods=['GET', 'POST'])
def admin_library():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        book_file = request.files['book_file']

        if book_file:
            cloudinary_response = cloudinary.uploader.upload(
                book_file,
               # resource_type="raw",
                public_id=book_file.filename.rsplit('.', 1)[0],  # filename without extension
                filename=book_file.filename,
                use_filename=True,
                unique_filename=False,
                overwrite=True
            )
            book_url = cloudinary_response['secure_url']

            db.collection('library').add({
                'title': title,
                'author': author,
                'link': book_url
            })

            flash('Book uploaded successfully!', 'success')
            return redirect(url_for('admin_library'))





    # Retrieve all books from Firebase
    books_ref = db.collection('library')
    books = books_ref.stream()
    return render_template('admin_library.html', books=books)


@app.route('/admin/add_book', methods=['POST'])
def add_book():
    title = request.form['title']
    author = request.form['author']
    link = request.form['link']
    
    db.collection('library').add({
        'title': title,
        'author': author,
        'link': link
    })
    flash("Book added successfully!", "success")
    return redirect(url_for('admin_library'))

@app.route('/admin/delete_book/<book_id>', methods=['POST'])
def delete_book(book_id):
    db.collection('library').document(book_id).delete()
    flash("Book deleted successfully!", "success")
    return redirect(url_for('admin_library'))
 



 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == 'admin@gmail.com' and password == '123':
            return redirect(url_for('admin_home'))

        api_key = os.getenv("FIREBASE_API_KEY")  
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

            # Get extra user info from Firestore
            user_doc = db.collection('user_data').document(user_data['localId']).get()
            if user_doc.exists:
                session['student'] = user_doc.to_dict()

            flash("Login successful!", "success")
            return redirect('/')  # Redirect to home page
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
                'role': 'student',
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

    file = request.files['profile_pic']
    if file:
     upload_result = cloudinary.uploader.upload(file)
     profile_pic_url = upload_result['secure_url']
     updates['profile_pic_url'] = profile_pic_url

    user_ref.update(updates)

    flash("Profile updated successfully!", "success")
    return redirect(url_for('student_home'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)