s = open('app.py').read()
old = '''@app.route("/run-poster-now")
def run_poster_now():
    try:
        now = datetime.utcnow()
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now
        ).limit(1).all()
        if not due:
            return f"No due jobs at {now} UTC"
        job = due[0]
        pc = db.session.get(PostingChannel, job.posting_channel_id)
        if not pc or not pc.connected:
            return f"Job {job.id} found but posting channel not connected"
        if not job.filepath:
            return f"Job {job.id} has no filepath"
        return f"Job {job.id} ready: {job.title[:50]} filepath:{job.filepath} time:{job.scheduled_time}"
    except Exception as e:
        import traceback
        return traceback.format_exc()'''
new = '''@app.route("/run-poster-now")
def run_poster_now():
    import threading
    threading.Thread(target=post_due_videos, daemon=True).start()
    return "Poster triggered - check Railway logs and /debug-kai-only in 2-3 minutes"'''
if old in s:
    open('app.py','w').write(s.replace(old,new))
    print('Done!')
else:
    print('NOT FOUND')
