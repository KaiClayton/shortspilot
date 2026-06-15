import os, sys
sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = "sqlite:///instance/shortspilot.db"
from app import app, db, SourceChannel, PostingChannel, UploadJob
with app.app_context():
    print("Sources:", [(s.id, s.name, s.status, s.category) for s in SourceChannel.query.all()])
    print("Posting:", [(p.id, p.name, p.connected, p.category) for p in PostingChannel.query.all()])
    print("Jobs:", UploadJob.query.count())

