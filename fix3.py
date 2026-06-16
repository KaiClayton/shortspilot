s = open('app.py').read()
old = '''def post_due_videos():
    with app.app_context():
        now = datetime.utcnow()
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now,
            UploadJob.filepath != None
        ).all()'''
new = '''def post_due_videos():
    with app.app_context():
        now = datetime.utcnow()
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now
        ).limit(1).all()'''
if old in s:
    open('app.py','w').write(s.replace(old, new))
    print('Done!')
else:
    print('NOT FOUND')
    idx = s.find('def post_due_videos')
    print(repr(s[idx:idx+200]))
