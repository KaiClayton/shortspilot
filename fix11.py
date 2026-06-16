s = open('app.py').read()
old = '@app.route("/debug-kai-only")'
new = '''@app.route("/reschedule-now")
def reschedule_now():
    from datetime import timedelta
    jobs = UploadJob.query.filter_by(status="scheduled").order_by(UploadJob.id).all()
    start = datetime.utcnow()
    for i, job in enumerate(jobs):
        job.scheduled_time = start + timedelta(hours=i*2)
    db.session.commit()
    return f"Rescheduled {len(jobs)} jobs starting from now, every 2 hours"

@app.route("/debug-kai-only")'''
open('app.py','w').write(s.replace(old,new))
print('Done!' if old in s else 'NOT FOUND')
