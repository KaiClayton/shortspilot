import os
import json
import subprocess
import threading
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from requests_oauthlib import OAuth2Session
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.oauth2.credentials

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shortspilot-secret-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///shortspilot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
db = SQLAlchemy(app)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CATEGORIES = ["Finance and Money", "Entertainment and Funny", "Motivation and Self Improvement"]
VIDEOS_DIR = "/tmp/shortspilot_videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)

def client_id():
    return os.environ.get("GOOGLE_CLIENT_ID", "")

def client_secret_val():
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")

def redirect_uri():
    return os.environ.get("REDIRECT_URI", "http://localhost:5000/oauth2callback")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SourceChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="pending")

class PostingChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    connected = db.Column(db.Boolean, default=False)
    youtube_token = db.Column(db.Text, nullable=True)
    jobs = db.relationship("UploadJob", backref="posting_channel", lazy=True)

class UploadJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    posting_channel_id = db.Column(db.Integer, db.ForeignKey("posting_channel.id"), nullable=False)
    source_channel_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(500), nullable=False)
    filepath = db.Column(db.String(1000), nullable=True)
    views = db.Column(db.Integer, default=0)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default="scheduled")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def download_channel(source_channel_id):
    with app.app_context():
        source = db.session.get(SourceChannel, source_channel_id)
        if not source:
            return
        source.status = "downloading"
        db.session.commit()
        folder = os.path.join(VIDEOS_DIR, str(source.user_id), str(source_channel_id))
        os.makedirs(folder, exist_ok=True)
        archive = os.path.join(folder, "archive.txt")
        out_tmpl = os.path.join(folder, "%(view_count)s---%(title).100s---%(id)s.%(ext)s")
        cmd = [
            "yt-dlp", "--skip-download",
            "--print", "%(id)s|%(title)s|%(view_count)s",
            source.url + "/shorts"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            lines = [l for l in result.stdout.strip().split("\n") if "|" in l]
            lines_data = []
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        lines_data.append((parts[0], parts[1], int(parts[2].replace(",",""))))
                    except:
                        pass
            lines_data.sort(key=lambda x: x[2], reverse=True)
            posting_channels = PostingChannel.query.filter_by(
                user_id=source.user_id, category=source.category, connected=True
            ).all()
            if posting_channels and lines_data:
                from datetime import timedelta
                next_time = datetime.utcnow()
                for i, (vid_id, title, views) in enumerate(lines_data):
                    pc = posting_channels[i % len(posting_channels)]
                    existing = UploadJob.query.filter_by(
                        posting_channel_id=pc.id,
                        title=title
                    ).first()
                    if not existing:
                        job = UploadJob(
                            posting_channel_id=pc.id,
                            source_channel_id=source_channel_id,
                            title=title,
                            views=views,
                            scheduled_time=next_time,
                            status="scheduled",
                            filepath=os.path.join(folder, vid_id + ".mp4")
                        )
                        db.session.add(job)
                        next_time = next_time + timedelta(hours=2)
            source.status = "scheduled"
            db.session.commit()
        except Exception as e:
            source.status = "error"
            db.session.commit()
            print(f"Download error: {e}")

def post_due_videos():
    with app.app_context():
        now = datetime.utcnow()
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now
        ).limit(1).all()
        for job in due:
            try:
                pc = db.session.get(PostingChannel, job.posting_channel_id)
                if not pc or not pc.connected or not pc.youtube_token:
                    continue
                token_data = json.loads(pc.youtube_token)
                creds = google.oauth2.credentials.Credentials(
                    token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=TOKEN_URI,
                    client_id=client_id(),
                    client_secret=client_secret_val(),
                    scopes=SCOPES
                )
                if job.filepath:
                    os.makedirs(os.path.dirname(job.filepath), exist_ok=True)
                    if not os.path.exists(job.filepath):
                        vid_id = os.path.basename(job.filepath).replace(".mp4","")
                        dl_cmd = [
                            "yt-dlp",
                            "--extractor-args", "youtube:player_client=ios",
                            "-f", "best[ext=mp4]/best",
                            "--merge-output-format", "mp4",
                            "--no-check-formats",
                            "-o", job.filepath,
                            "https://www.youtube.com/shorts/" + vid_id
                        ]
                        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=600)
                        print(f"Download: {result.returncode} {result.stderr[:100]}")
                    if not os.path.exists(job.filepath):
                        job.status = "error"
                        db.session.commit()
                        print(f"File missing: {job.filepath}")
                        continue
                    youtube = build("youtube", "v3", credentials=creds)
                    body = {
                        "snippet": {
                            "title": job.title[:100],
                            "description": "",
                            "categoryId": "22"
                        },
                        "status": {"privacyStatus": "public"}
                    }
                    media = MediaFileUpload(job.filepath, mimetype="video/mp4", resumable=True)
                    youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
                    job.status = "uploaded"
                    db.session.commit()
                    print(f"Uploaded: {job.title}")
            except Exception as e:
                import traceback
                print(f"Error job {job.id}: {e}")
                print(traceback.format_exc())


def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for("signup"))
        user = User(email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        session["email"] = user.email
        return redirect(url_for("dashboard"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["email"] = user.email
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    uid = session["user_id"]
    sources = SourceChannel.query.filter_by(user_id=uid).all()
    posting = PostingChannel.query.filter_by(user_id=uid).all()
    by_category = {}
    for cat in CATEGORIES:
        by_category[cat] = {
            "sources": [s for s in sources if s.category == cat],
            "posting": [p for p in posting if p.category == cat]
        }
    total_scheduled = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "scheduled").count()
    total_uploaded = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "uploaded").count()
    return render_template("dashboard.html", categories=CATEGORIES, by_category=by_category, total_scheduled=total_scheduled, total_uploaded=total_uploaded)

@app.route("/add-source", methods=["GET", "POST"])
def add_source():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        ch = SourceChannel(user_id=session["user_id"], name=request.form["name"], url=request.form["url"], category=request.form["category"])
        db.session.add(ch)
        db.session.commit()
        threading.Thread(target=download_channel, args=(ch.id,), daemon=True).start()
        flash("Source channel added! Fetching video list now...", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_source.html", categories=CATEGORIES)

@app.route("/delete-source/<int:id>")
def delete_source(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    ch = SourceChannel.query.get_or_404(id)
    if ch.user_id == session["user_id"]:
        db.session.delete(ch)
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/add-posting-channel", methods=["GET", "POST"])
def add_posting_channel():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        ch = PostingChannel(user_id=session["user_id"], name=request.form["name"], category=request.form["category"])
        db.session.add(ch)
        db.session.commit()
        session["connecting_channel_id"] = ch.id
        return redirect(url_for("connect_youtube_channel", channel_id=ch.id))
    return render_template("add_posting_channel.html", categories=CATEGORIES)

@app.route("/connect-youtube/<int:channel_id>")
def connect_youtube_channel(channel_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    session["connecting_channel_id"] = channel_id
    oauth = OAuth2Session(client_id(), redirect_uri=redirect_uri(), scope=SCOPES)
    auth_url, state = oauth.authorization_url(AUTH_URI, access_type="offline", prompt="consent")
    session["oauth_state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    if "user_id" not in session:
        return redirect(url_for("login"))
    channel_id = session.get("connecting_channel_id")
    if not channel_id:
        flash("Session expired, please try again", "error")
        return redirect(url_for("dashboard"))
    oauth = OAuth2Session(client_id(), redirect_uri=redirect_uri(), state=session.get("oauth_state"))
    token = oauth.fetch_token(TOKEN_URI, authorization_response=request.url.replace("http://", "https://"), client_secret=client_secret_val())
    ch = db.session.get(PostingChannel, channel_id)
    if ch and ch.user_id == session["user_id"]:
        ch.youtube_token = json.dumps(token)
        ch.connected = True
        db.session.commit()
        flash("YouTube channel connected!", "success")
    return redirect(url_for("dashboard"))

@app.route("/disconnect-channel/<int:id>")
def disconnect_channel(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    ch = db.session.get(PostingChannel, id)
    if ch and ch.user_id == session["user_id"]:
        ch.youtube_token = None
        ch.connected = False
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/delete-posting/<int:id>")
def delete_posting(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    ch = db.session.get(PostingChannel, id)
    if ch and ch.user_id == session["user_id"]:
        db.session.delete(ch)
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/api/status")
def api_status():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    sources = SourceChannel.query.filter_by(user_id=session["user_id"]).all()
    return jsonify([{"id": s.id, "name": s.name, "status": s.status} for s in sources])

@app.route("/trigger-jobs/<int:source_id>")
def trigger_jobs(source_id):
    import threading
    threading.Thread(target=download_channel, args=(source_id,), daemon=True).start()
    return f"Download started for source {source_id} - check /debug-kai-only in 3 minutes"

def trigger_jobs_real(source_id):
    from datetime import timedelta
    source = db.session.get(SourceChannel, source_id)
    if not source:
        return "Source not found"
    posting_channels = PostingChannel.query.filter_by(
        user_id=source.user_id, category=source.category, connected=True
    ).all()
    if not posting_channels:
        return "No connected posting channels in same category"
    url = source.url if "shorts" in source.url else source.url + "/shorts"
    cmd = ["yt-dlp", "--skip-download", "--print", "%(id)s|%(title)s|%(view_count)s", url]
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if not result.stdout.strip():
        return f"yt-dlp returned no output. stderr: {result.stderr[:500]}"
    lines = [l for l in result.stdout.strip().split("\n") if "|" in l]
    lines_data = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 3:
            try:
                lines_data.append((parts[0], parts[1], int(parts[2].replace(",",""))))
            except:
                pass
    lines_data.sort(key=lambda x: x[2], reverse=True)
    next_time = datetime.utcnow()
    count = 0
    for i, (vid_id, title, views) in enumerate(lines_data):
        pc = posting_channels[i % len(posting_channels)]
        existing = UploadJob.query.filter_by(posting_channel_id=pc.id, title=title).first()
        if not existing:
            job = UploadJob(
                posting_channel_id=pc.id,
                source_channel_id=source_id,
                title=title,
                views=views,
                scheduled_time=next_time,
                status="scheduled",
                filepath="/tmp/shortspilot_videos/" + str(source.user_id) + "/" + str(source_id) + "/" + vid_id + ".mp4"
            )
            db.session.add(job)
            next_time = next_time + timedelta(hours=2)
            count += 1
    db.session.commit()
    return f"Created {count} jobs from {len(lines_data)} videos"

@app.route("/run-poster-now")
def run_poster_now():
    import threading
    threading.Thread(target=post_due_videos, daemon=True).start()
    return "Poster triggered - check Railway logs and /debug-kai-only in 2-3 minutes"

@app.route("/check-jobs")
def check_jobs():
    jobs = UploadJob.query.filter_by(status="scheduled").order_by(UploadJob.id).limit(5).all()
    out = ""
    for j in jobs:
        out += f"ID:{j.id} filepath:{j.filepath} time:{j.scheduled_time}<br>"
    return out or "No jobs found"

@app.route("/reschedule-now")
def reschedule_now():
    from datetime import timedelta
    jobs = UploadJob.query.filter_by(status="scheduled").order_by(UploadJob.id).all()
    start = datetime.utcnow()
    for i, job in enumerate(jobs):
        job.scheduled_time = start + timedelta(hours=i*2)
    db.session.commit()
    return f"Rescheduled {len(jobs)} jobs starting from now, every 2 hours"

@app.route("/debug-kai-only")
def debug():
    sources = SourceChannel.query.all()
    posting = PostingChannel.query.all()
    jobs = UploadJob.query.order_by(UploadJob.id.desc()).limit(20).all()
    return render_template("debug.html", sources=sources, posting=posting, jobs=jobs, job_count=UploadJob.query.count())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


