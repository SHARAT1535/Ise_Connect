from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import base64
import json
from dotenv import load_dotenv
import openpyxl
import requests
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from datetime import datetime
import io
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Initialize Firebase
encoded_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
if encoded_key:
    decoded_bytes = base64.b64decode(encoded_key)
    service_account_info = json.loads(decoded_bytes)
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_BASE64 not found in .env file")

# Consolidated homepage route
@app.route('/')
def hello():
    try:
        # Fetch notices from Firestore
        notices_ref = db.collection('notices').order_by('date', direction=firestore.Query.DESCENDING).limit(5)
        notices = [doc.to_dict() for doc in notices_ref.stream()]
        logger.debug(f"Fetched {len(notices)} notices from Firestore")

        # Fetch news from Firestore
        news_ref = db.collection('addnews').order_by('date', direction=firestore.Query.DESCENDING)
        news_docs = news_ref.stream()
        news_items = [
            {
                'title': doc.to_dict().get('title'),
                'date': doc.to_dict().get('date'),
                'description': doc.to_dict().get('description'),
                'link': doc.to_dict().get('link')
            } for doc in news_docs
        ]
        logger.debug(f"Fetched {len(news_items)} news items from Firestore")

        # Get user info from session
        student_info = session.get('student')
        if student_info:
            logger.debug(f"Student info: {student_info}")
        
        return render_template('index.html', notices=notices, news_items=news_items, student_info=student_info)
    except Exception as e:
        logger.error(f"Error in hello route: {str(e)}")
        flash(f'Error loading page: {str(e)}', 'error')
        return render_template('index.html', notices=[], news_items=[], student_info=None)

# Add notice route
@app.route('/add_notice', methods=['GET', 'POST'])
def add_notice():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        logger.warning("Unauthorized access to add_notice: No user_id in session")
        return redirect(url_for('login'))
    
    try:
        # Check if user is admin
        student_info = session.get('student', {})
        if not student_info.get('is_admin', False):
            user_ref = db.collection('user_data').document(session['user_id'])
            user_data = user_ref.get()
            if not user_data.exists or not user_data.to_dict().get('is_admin', False):
                flash('Unauthorized access. Admin privileges required.', 'error')
                logger.warning(f"Unauthorized access to add_notice by user_id: {session['user_id']}")
                return redirect(url_for('hello'))
            # Update session with admin status
            student_info['is_admin'] = True
            session['student'] = student_info
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            link = request.form.get('link')
            logger.debug(f"Form data: title={title}, description={description}, link={link}")
            
            if not title or not description:
                flash('Title and description are required.', 'error')
                logger.warning("Notice submission failed: Missing title or description")
                return redirect(url_for('hello'))
            
            notice_data = {
                'title': title,
                'description': description,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'link': link if link else None
            }
            
            try:
                db.collection('notices').add(notice_data)
                flash('Notice added successfully!', 'success')
                logger.info(f"Notice added by user_id: {session['user_id']}, title: {title}")
            except Exception as e:
                flash(f'Error adding notice: {str(e)}', 'error')
                logger.error(f"Firestore error adding notice: {str(e)}")
            return redirect(url_for('hello'))
        
        # GET request redirects to homepage (form is in index.html)
        return redirect(url_for('hello'))
    except Exception as e:
        logger.error(f"Error in add_notice route: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('hello'))

# Admin dashboard route
@app.route('/admin_home')
def admin_home():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        logger.warning("Unauthorized access to admin_home: No user_id in session")
        return redirect(url_for('login'))
    
    try:
        student_info = session.get('student', {})
        if not student_info.get('is_admin', False):
            user_ref = db.collection('user_data').document(session['user_id'])
            user_data = user_ref.get()
            if not user_data.exists or not user_data.to_dict().get('is_admin', False):
                flash('Unauthorized access. Admin privileges required.', 'error')
                logger.warning(f"Unauthorized access to admin_home by user_id: {session['user_id']}")
                return redirect(url_for('hello'))
            # Update session with admin status
            student_info['is_admin'] = True
            session['student'] = student_info
        
        return render_template('admin_home.html')
    except Exception as e:
        logger.error(f"Error in admin_home route: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('hello'))

# Download users route
@app.route('/admin/users/download')
def download_users():
    query = request.args.get('query', '').lower().strip()
    passout_year = request.args.get('passout_year', '').strip()
    working_at = request.args.get('working_at', '').lower().strip()

    users_ref = db.collection('user_data')
    users = []

    for doc in users_ref.stream():
        data = doc.to_dict()

        # Apply search query filter
        if query:
            name = data.get('name', '').lower()
            usn = data.get('usn', '').lower()
            email = data.get('email', '').lower()
            if query not in name and query not in usn and query not in email:
                continue

        # Apply passout_year filter if set
        if passout_year:
            user_passout = str(data.get('passesout', '')).strip()
            if user_passout != passout_year:
                continue

        # Apply working_at filter if set
        if working_at:
            user_working_at = data.get('working_at', '').lower()
            if working_at not in user_working_at:
                continue

        users.append(data)

    # Generate Excel file
    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Registered Users"

    headers = ['Name', 'Email', 'Role', 'Passed Out', 'USN', 'Phone', 'Working At', 'Experience']
    sheet.append(headers)

    for user in users:
        sheet.append([
            user.get('name', ''),
            user.get('email', ''),
            user.get('role', 'Student'),
            user.get('passesout', ''),
            user.get('usn', ''),
            user.get('phone', ''),
            user.get('working_at', ''),
            user.get('experience', '')
        ])

    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="filtered_users.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/placement')
def placement():
    return render_template('placement.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/community_chat')
def community_chat():
    return render_template('community_chats.html')

@app.route('/library')
def elibrary():
    docs = db.collection('elibrary').stream()
    materials = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        materials.append(data)
    return render_template('elibrary.html', materials=materials)

@app.route('/admin/upload-elibrary', methods=['GET', 'POST'])
def upload_elibrary():
    if 'user_id' not in session or not session.get('student', {}).get('is_admin', False):
        flash('Please log in as admin to access this page.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "title": request.form['title'],
            "type": request.form['type'],
            "subject": request.form['subject'],
            "semester": int(request.form['semester']),
            "year": int(request.form['year']),
            "link": request.form['link']
        }
        db.collection('elibrary').add(data)
        flash('Item uploaded successfully!', 'success')
        return redirect(url_for('upload_elibrary'))
    return render_template('admin_upload_elibrary.html')

@app.route('/send-message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_ref = db.collection('user_data').document(session['user_id'])
    user = user_ref.get()
    if not user.exists:
        return jsonify({'error': 'User not found'}), 404

    name = user.to_dict().get('name', 'Anonymous')
    text = request.json.get('text')

    if text.strip():
        db.collection('community_chat').add({
            'name': name,
            'text': text,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    return jsonify({'status': 'Message sent'})

@app.route('/get-messages')
def get_messages():
    messages_ref = db.collection('community_chat').order_by('timestamp', direction=firestore.Query.ASCENDING).limit(100)
    messages = [
        {'name': msg.to_dict()['name'], 'text': msg.to_dict()['text']}
        for msg in messages_ref.stream()
    ]
    return jsonify(messages)

@app.route('/job_openings', methods=['GET', 'POST'])
def job_openings():
    user = session.get('student')
    if request.method == 'POST':
        if user and user.get('role') == 'Alumni':
            data = {
                'title': request.form['title'],
                'company': request.form['company'],
                'location': request.form['location'],
                'description': request.form['description'],
                'link': request.form['link'],
                'posted_by': user.get('name'),
                'posted_by_uid': session.get('user_id'),
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            db.collection('job_openings').add(data)
            return redirect(url_for('job_openings'))
    
    jobs = db.collection('job_openings').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    job_list = [{
        'title': j.to_dict().get('title'),
        'company': j.to_dict().get('company'),
        'location': j.to_dict().get('location'),
        'description': j.to_dict().get('description'),
        'link': j.to_dict().get('link'),
        'posted_by': j.to_dict().get('posted_by'),
        'timestamp': j.to_dict().get('timestamp')
    } for j in jobs]
    return render_template('job_openings.html', job_list=job_list, user=user)

@app.route('/alumni', methods=['GET'])
def alumni_page():
    users_ref = db.collection('user_data')
    jobs_ref = db.collection('job_openings')
    current_uid = session.get('user_id')
    
    alumni_query = users_ref.where('role', '==', 'Alumni')
    alumni_docs = alumni_query.stream()
    alumni_list = []
    for doc in alumni_docs:
        if doc.id == current_uid:
            continue
        data = doc.to_dict()
        alumni_list.append({
            'name': data.get('name', 'N/A'),
            'working_at': data.get('working_at', 'N/A'),
            'experience': data.get('experience', 'N/A'),
            'about_me': data.get('about_me', ''),
            'profile_pic_url': data.get('profile_pic_url'),
            'linkedin': data.get('linkedin', '')
        })

    search_query = request.args.get('search', '').lower()
    job_docs = jobs_ref.stream()
    job_list = []
    for job in job_docs:
        data = job.to_dict()
        if search_query:
            if not (
                search_query in data.get('title', '').lower() or
                search_query in data.get('company', '').lower() or
                search_query in data.get('posted_by', '').lower()
            ):
                continue
        job_list.append({
            'title': data.get('title'),
            'company': data.get('company'),
            'location': data.get('location'),
            'description': data.get('description'),
            'link': data.get('link'),
            'posted_by': data.get('posted_by')
        })
    return render_template('alumni.html', alumni_list=alumni_list, job_list=job_list, search_query=search_query)

@app.route('/chat/<other_uid>', methods=['GET'])
def chat(other_uid):
    current_uid = session.get('user_id')
    if current_uid:
        return render_template('chat.html', current_uid=current_uid, other_uid=other_uid)
    return redirect(url_for('login'))

def send_message(current_uid, other_uid, message):
    chat_id = "_".join(sorted([current_uid, other_uid]))
    db.collection("chats").document(chat_id).collection("messages").add({
        "sender_id": current_uid,
        "receiver_id": other_uid,
        "message": message,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

@app.route('/gallery_page')
def gallery_page():
    gallery_ref = db.collection('gallery_posts')
    filter_date = request.args.get('filter_date')
    gallery_posts = []
    if filter_date:
        docs = gallery_ref.where('event_date', '==', filter_date).stream()
    else:
        docs = gallery_ref.stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        gallery_posts.append(data)
    return render_template('gallery.html', gallery_posts=gallery_posts)

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if not session.get('student', {}).get('is_admin', False):
        return forbidden(403)
    
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        description = request.form['description']
        link = request.form['link']
        db.collection('addnews').add({
            'title': title,
            'date': date,
            'description': description,
            'link': link
        })
        return redirect(url_for('add_news'))
    
    news_docs = db.collection('addnews').stream()
    news_items = [
        {
            'id': doc.id,
            'title': doc.to_dict().get('title'),
            'date': doc.to_dict().get('date'),
            'description': doc.to_dict().get('description'),
            'link': doc.to_dict().get('link')
        } for doc in news_docs
    ]
    return render_template('add_news.html', news_items=news_items)

@app.route('/delete_news/<news_id>', methods=['POST'])
def delete_news(news_id):
    if not session.get('student', {}).get('is_admin', False):
        return forbidden(403)
    db.collection('addnews').document(news_id).delete()
    return redirect(url_for('add_news'))

@app.route('/news')
def news_page():
    news_ref = db.collection('addnews').order_by('date', direction=firestore.Query.DESCENDING)
    news_posts = [post.to_dict() for post in news_ref.stream()]
    return render_template('index.html', news_posts=news_posts)

@app.route('/request_alumni', methods=['POST'])
def request_alumni():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'pending'
    })
    flash("Your alumni request has been submitted and is pending approval.", "success")
    return redirect(url_for('student_home'))

@app.route('/admin/alumni_requests')
def view_alumni_requests():
    if not session.get('student', {}).get('is_admin', False):
        return redirect(url_for('hello'))
    
    pending_requests = db.collection('user_data').where('alumni_request_status', '==', 'pending').stream()
    requests = [request.to_dict() for request in pending_requests]
    return render_template('admin_alumni_requests.html', requests=requests)

@app.route('/admin/approve_request/<user_id>', methods=['POST'])
def approve_request(user_id):
    if not session.get('student', {}).get('is_admin', False):
        return redirect(url_for('hello'))
    
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'approved',
        'role': 'Alumni'
    })
    flash("Alumni request has been approved.", "success")
    return redirect(url_for('view_alumni_requests'))

@app.route('/admin/reject_request/<user_id>', methods=['POST'])
def reject_request(user_id):
    if not session.get('student', {}).get('is_admin', False):
        return redirect(url_for('hello'))
    
    db.collection('user_data').document(user_id).update({
        'alumni_request_status': 'rejected'
    })
    flash("Alumni request has been rejected.", "danger")
    return redirect(url_for('view_alumni_requests'))

@app.route('/admin/gallery', methods=['GET', 'POST'])
def admin_gallery():
    if 'user_id' not in session:
        flash("You must be logged in to access the gallery.", 'error')
        return redirect(url_for('login'))
    
    gallery_ref = db.collection('gallery_posts')
    if request.method == 'POST':
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            gallery_ref.document(delete_id).delete()
            flash("Post deleted successfully.", 'success')
            return redirect(url_for('admin_gallery'))
        
        description = request.form['description']
        uploaded_files = request.files.getlist('media_files')
        event_date = request.form.get("event_date")
        uploaded_urls = []
        for file in uploaded_files:
            if file:
                upload_result = cloudinary.uploader.upload(file)
                uploaded_urls.append(upload_result['secure_url'])
        
        gallery_ref.add({
            'images': uploaded_urls,
            'description': description,
            'created_by': session['user_id'],
            'event_date': event_date,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return redirect(url_for('admin_gallery'))
    
    gallery_posts = []
    docs = gallery_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        gallery_posts.append(data)
    return render_template('admin_gallery.html', gallery_posts=gallery_posts)

@app.route('/staff')
def staff():
    return render_template('staff.html')

@app.route('/student_portal')
def student_portal():
    return render_template('student_portal.html')

@app.route('/admin/users')
def admin_users():
    query = request.args.get('query', '').lower().strip()
    passout_year = request.args.get('passout_year', '').strip()
    working_at = request.args.get('working_at', '').lower().strip()
    experience = request.args.get('experience', '').strip()
    users_ref = db.collection('user_data')
    users = []
    years_set = set()
    for doc in users_ref.stream():
        data = doc.to_dict()
        data['uid'] = doc.id
        name = data.get('name', '').lower()
        usn = data.get('usn', '').lower()
        year = str(data.get('joining_year', '')).lower()
        passesout = str(data.get('passesout', ''))
        current_company = data.get('working_at', '').lower()
        exp = data.get('experience', '')
        if passesout:
            years_set.add(passesout)
        if query and query not in name and query not in usn and query not in year:
            continue
        if passout_year and passesout != passout_year:
            continue
        if working_at and working_at not in current_company:
            continue
        if experience:
            try:
                exp_val = int(exp)
                if experience == '0-1' and not (0 <= exp_val <= 1):
                    continue
                elif experience == '1-3' and not (1 < exp_val <= 3):
                    continue
                elif experience == '3+' and not (exp_val > 3):
                    continue
            except:
                continue
        users.append(data)
    years = sorted(years_set)
    return render_template('admin_users.html', users=users, years=years)

@app.route('/admin/convert_to_alumni/<user_id>', methods=['POST'])
def convert_to_alumni(user_id):
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
                public_id=book_file.filename.rsplit('.', 1)[0],
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
            session['user_id'] = 'admin'
            session['student'] = {'email': email, 'is_admin': True, 'name': 'Admin'}
            flash("Admin login successful!", "success")
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
            user_id = user_data['localId']
            session['user_id'] = user_id
            session['email'] = user_data['email']
            user_doc = db.collection('user_data').document(user_id).get()
            if user_doc.exists:
                user_dict = user_doc.to_dict()
                user_dict['is_admin'] = user_dict.get('is_admin', False)
                session['student'] = user_dict
            else:
                session['student'] = {'email': email, 'is_admin': False}
            flash("Login successful!", "success")
            return redirect(url_for('hello'))
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
        user_doc = db.collection('user_data').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return render_template('student_home.html', user=user_data)
        return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        if not (name and email and subject and message):
            flash("All fields are required.", "danger")
            return redirect(url_for('feedback'))
        feedback_data = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        db.collection('feedback1').add(feedback_data)
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('feedback'))
    return render_template('feedback.html')

@app.route('/admin/feedback')
def admin_feedback():
    feedback_ref = db.collection('feedback1')
    docs = feedback_ref.stream()
    feedback_list = [doc.to_dict() for doc in docs]
    return render_template('admin_feedback.html', feedbacks=feedback_list)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        usn = request.form['usn']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for('signup'))
        try:
            user = auth.create_user(email=email, password=password)
            user_data = {
                'uid': user.uid,
                'name': name,
                'usn': usn,
                'email': email,
                'role': 'student',
                'is_admin': False,
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
        user_doc = db.collection('user_data').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            uploadcare_key = os.getenv("UPLOADCARE_PUBLIC_KEY")
            return render_template('profileedit.html', user=user_data, uploadcare_key=uploadcare_key)
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
    
    updates = {
        'name': request.form.get('name'),
        'usn': request.form.get('usn'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'internship': request.form.get('internship'),
        'working_at': request.form.get('working_at'),
        'experience': request.form.get('experience'),
        'about_me': request.form.get('about_me'),
        'skills': request.form.get('skills'),
        'linkedin': request.form.get('linkedin'),
        'github': request.form.get('github'),
        'passesout': request.form.get('passesout'),
        'joining_year': request.form.get('joining_year')
    }
    
    file = request.files.get('profile_pic')
    if file:
        upload_result = cloudinary.uploader.upload(file)
        updates['profile_pic_url'] = upload_result['secure_url']
    
    user_ref.update(updates)
    session['student'] = user_ref.get().to_dict()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('student_home'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('student', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/achievement')
def achievement():
    achievement_ref = db.collection('achievements')
    docs = achievement_ref.stream()
    achievements = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        achievements.append(data)
    return render_template('achievement.html', achievements=achievements)

@app.route('/admin/uplode_achievment', methods=['GET', 'POST'])
def uplode_achievment():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        date = request.form.get("date")
        image = request.files.get("image")
        image_url = ""
        if image:
            result = cloudinary.uploader.upload(image)
            image_url = result.get("secure_url")
        db.collection("achievements").add({
            "title": title,
            "description": description,
            "date": date,
            "image_url": image_url
        })
        return redirect(url_for('uplode_achievment'))
    
    achievements_ref = db.collection("achievements").stream()
    achievements = [{**doc.to_dict(), "id": doc.id} for doc in achievements_ref]
    return render_template("uplode_achievment.html", achievements=achievements)

@app.route('/admin/delete_achievement/<id>', methods=['POST'])
def delete_achievement(id):
    db.collection("achievements").document(id).delete()
    return redirect(url_for('uplode_achievment'))



@app.route('/developers')
def developers():
    developers = [
        {
            'name': 'Sharat Kubasad',
            'image': 'https://via.placeholder.com/150',
            'description': 'Sharat led the backend development of ISE Connect, implementing robust APIs and database integration to ensure seamless functionality.',
            'contribution': 'Backend Development, Database Management'
        },
        {
            'name': 'Simran Raikar',
            'image': 'https://via.placeholder.com/150',
            'description': 'Simran focused on the frontend design, creating an intuitive and responsive user interface for ISE Connect.',
            'contribution': 'Frontend Development, UI/UX Design'
        },
        {
            'name': 'Sanjay Kulkarni',
            'image': 'https://via.placeholder.com/150',
            'description': 'Sanjay contributed to the content management system, ensuring dynamic updates for notices and news sections.',
            'contribution': 'Content Management, Feature Implementation'
        },
        {
            'name': 'Apoorva U V',
            'image': 'https://via.placeholder.com/150',
            'description': 'Apoorva handled testing and deployment, ensuring the platform’s stability and performance across devices.',
            'contribution': 'Testing, Deployment, Quality Assurance'
        }
    ]
    return render_template('developers.html', developers=developers)


if __name__ == '__main__':
    app.run(debug=True, port=8000)