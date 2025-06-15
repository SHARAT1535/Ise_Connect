# ISE_Connect

ISE_Connect is a comprehensive web and mobile application built for the **Information Science and Engineering Department** to enhance communication, academics, placements, and alumni interaction.

## 🚀 Features

- 📢 Communication & Notifications
- 📚 Academic Resources (PYQs, Notes)
- 🎓 Placement & Internship Support
- 🧾 Attendance & Results
- 📖 E-Library (PDF books hosted on Cloudinary)
- 🖼️ ISE Gallery (Event photos)
- 📅 Timetable & Reminders
- 🧑‍🏫 Faculty Directory (with IRINS links)
- 🧑‍🎓 Alumni Connect (Community chat & Job openings)
- 🆘 Emergency Alerts & Help Desk
- 📰 News Section

## 🛠️ Tech Stack

- **Frontend:** HTML, CSS, JavaScript, Kotlin (for Android app)
- **Backend:** Flask (Python)
- **Database:** Firebase Firestore
- **Authentication:** Firebase Auth
- **Storage:** Cloudinary (for images, PDFs)

## 📂 Project Structure (Web)

```
/ISE_Connect
│
├── app.py               # Flask backend
├── templates/           # HTML templates
├── static/              # CSS, JS, images
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not uploaded)
└── README.md
```

## 🔐 Environment Variables

Make sure to create a `.env` file with the following (do not upload it):

```
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_key
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
```

## ⚙️ Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/your-username/ISE_Connect.git
cd ISE_Connect
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Flask app
```bash
python app.py
```

## 📱 Mobile App (Kotlin)

- Android app includes:
  - E-Library viewer with filters (semester, type, search)
  - Alumni job listings and chat
  - Faculty profiles
  - News section
- Uses Firebase and Cloudinary just like the web app

## 👥 Contributors

- [Your Name] - Backend & Firebase Integration
- [Friend's Name] - UI/UX & Frontend Styling
- [Team Member] - Android App (Kotlin)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Feel free to ⭐ the repo or contribute!
