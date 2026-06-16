s = open('app.py').read()
old = '''def post_due_videos():
    with app.app_context():
        now = datetime.utcnow()
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now
        ).limit(1).all()
        for job in due:'''
new = '''def post_due_videos():
    with app.app_context():
        now = datetime.utcnow()
        print(f"post_due_videos running at {now}")
        due = UploadJob.query.filter(
            UploadJob.status == "scheduled",
            UploadJob.scheduled_time <= now
        ).limit(1).all()
        print(f"Found {len(due)} due jobs")
        for job in due:'''
if old in s:
    open('app.py','w').write(s.replace(old,new))
    print('Done!')
else:
    print('NOT FOUND')
