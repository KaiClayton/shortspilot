s = open('app.py').read()
old = '@app.route("/reschedule-now")'
new = '''@app.route("/check-jobs")
def check_jobs():
    jobs = UploadJob.query.filter_by(status="scheduled").order_by(UploadJob.id).limit(5).all()
    out = ""
    for j in jobs:
        out += f"ID:{j.id} filepath:{j.filepath} time:{j.scheduled_time}<br>"
    return out or "No jobs found"

@app.route("/reschedule-now")'''
open('app.py','w').write(s.replace(old,new))
print('Done!' if old in s else 'NOT FOUND')
