from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os, subprocess, json, threading
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'shortspilot-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shortspilot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---- MODELS ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    channels = db.relationship('Channel', backref='user', lazy=True)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='pending')
    video_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    jobs = db.relationship('UploadJob', backref='channel', lazy=True)

class UploadJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    scheduled_date = db.Column(db.String(20))
    slot = db.Column(db.Integer)
    views = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ---- ROUTES ----
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        user = User(email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['email'] = user.email
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    channels = Channel.query.filter_by(user_id=session['user_id']).all()
    total_scheduled = UploadJob.query.join(Channel).filter(
        Channel.user_id == session['user_id'],
        UploadJob.status == 'scheduled'
    ).count()
    total_uploaded = UploadJob.query.join(Channel).filter(
        Channel.user_id == session['user_id'],
        UploadJob.status == 'uploaded'
    ).count()
    return render_template('dashboard.html', channels=channels, total_scheduled=total_scheduled, total_uploaded=total_uploaded)

@app.route('/add-channel', methods=['GET', 'POST'])
def add_channel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        url = request.form['url']
        channel = Channel(user_id=session['user_id'], name=name, url=url, status='downloading')
        db.session.add(channel)
        db.session.commit()
        flash(f'Channel "{name}" added! Downloading Shorts now...', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_channel.html')

@app.route('/channel/<int:channel_id>')
def channel_detail(channel_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    channel = Channel.query.get_or_404(channel_id)
    if channel.user_id != session['user_id']:
        return redirect(url_for('dashboard'))
    jobs = UploadJob.query.filter_by(channel_id=channel_id).order_by(UploadJob.views.desc()).all()
    return render_template('channel.html', channel=channel, jobs=jobs)

@app.route('/api/status')
def api_status():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401
    channels = Channel.query.filter_by(user_id=session['user_id']).all()
    return jsonify([{
        'id': c.id, 'name': c.name, 'status': c.status, 'video_count': c.video_count
    } for c in channels])

if __name__ == '__main__':
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)
