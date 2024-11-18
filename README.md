# Flask Chatroom Application

This is a real-time chatroom application built with Flask, Flask-SocketIO, and Flask-SQLAlchemy. Users can sign up, log in, create or join chat rooms, and exchange messages. The app also supports file sharing and real-time user count updates.

---
## **Setup Instructions**

### Prerequisites:
- Python 3.7+

---

**Install Dependencies:**
pip install -r requirements.txt

---

## **Technologies Used**
- **Backend**: Flask, Flask-SQLAlchemy, Flask-SocketIO.
- **Frontend**: HTML, CSS, JavaScript.
- **Database**: SQLite (default, supports MySQL with minor changes).
- **SocketIO**: Real-time bi-directional communication.

---

## **Set up the Database: Run the following command to initialize the SQLite database:** ##
python -c "from app import create_tables; create_tables()"

---

**Access the Application: Open a browser and navigate to http://localhost:5000.**

###**Folder Structure**

flask-chatroom/

├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
├── static/             # Static files (CSS, JS, Images)
├── uploads/            # Directory for file uploads
├── chatroom.db         # SQLite database (auto-created)
└── README.md           # Documentation
