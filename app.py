from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
# For SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatroom.db'
# For MySQL
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/chatroom'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Active users tracking (in-memory for Socket.IO)
active_users = {}

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='user', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    pin = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    messages = db.relationship('Message', backref='room_obj', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    file_attachment = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('home.html', username=user.username)
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            user = User(
                username=username,
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/create-room', methods=['GET', 'POST'])
def create_room():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        room_pin = request.form.get('room_pin')
        
        if Room.query.filter_by(name=room_name).first():
            flash('Room already exists')
        else:
            room = Room(
                name=room_name,
                pin=generate_password_hash(room_pin),
                creator_id=session['user_id']
            )
            db.session.add(room)
            db.session.commit()
            return redirect(url_for('chatroom', room=room_name))
    return render_template('create_room.html')

@app.route('/join-room', methods=['GET', 'POST'])
def join_room_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        room_pin = request.form.get('room_pin')
        
        room = Room.query.filter_by(name=room_name).first()
        
        if room and check_password_hash(room.pin, room_pin):
            return redirect(url_for('chatroom', room=room_name))
        flash('Invalid room name or PIN')
    return render_template('join_room.html')

@app.route('/chatroom/<room>')
def chatroom(room):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    room_data = Room.query.filter_by(name=room).first()
    if not room_data:
        return redirect(url_for('home'))
        
    user = User.query.get(session['user_id'])
    messages = Message.query.filter_by(room_id=room_data.id).order_by(Message.created_at.asc()).all()
    
    return render_template('chatroom.html', 
                         room=room, 
                         room_id=room_data.id,
                         username=user.username,
                         messages=messages)

@socketio.on('join')
def handle_join(data):
    room = data['room']
    room_data = Room.query.filter_by(name=room).first()
    
    if room_data:
        join_room(room)
        if room not in active_users:
            active_users[room] = set()
        active_users[room].add(session['user_id'])
        
        emit('user_count', {'count': len(active_users[room])}, room=room)
        
        user = User.query.get(session['user_id'])
        emit('message', {
            'username': 'System',
            'message': f"{user.username} has joined the room",
            'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, room=room)

@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    if room in active_users and session['user_id'] in active_users[room]:
        leave_room(room)
        active_users[room].remove(session['user_id'])
        
        emit('user_count', {'count': len(active_users[room])}, room=room)
        
        user = User.query.get(session['user_id'])
        emit('message', {
            'username': 'System',
            'message': f"{user.username} has left the room",
            'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, room=room)

@socketio.on('message')
def handle_message(data):
    room_name = data['room']
    user = User.query.get(session['user_id'])
    room = Room.query.filter_by(name=room_name).first()
    
    if not user or not room:
        return
        
    message = Message(
        content=data['message'],
        user_id=user.id,
        room_id=room.id
    )
    db.session.add(message)
    db.session.commit()
    
    emit('message', {
        'username': user.username,
        'message': message.content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=room_name)

@socketio.on('file')
def handle_file(data):
    room_name = data['room']
    user = User.query.get(session['user_id'])
    room = Room.query.filter_by(name=room_name).first()
    
    if not user or not room:
        return
        
    filename = secure_filename(data['filename'])
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    with open(file_path, 'wb') as f:
        f.write(data['file'])
    
    message = Message(
        content=f'Shared file: {filename}',
        file_attachment=filename,
        user_id=user.id,
        room_id=room.id
    )
    db.session.add(message)
    db.session.commit()
    
    emit('message', {
        'username': user.username,
        'message': message.content,
        'file': filename,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=room_name)

@app.route('/uploads/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Create database tables
def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables()
    socketio.run(app, debug=True)
