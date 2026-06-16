s = open('app.py').read()
# Find and replace the entire post_due_videos function
start = s.find('def post_due_videos():')
end = s.find('\ndef ', start + 1)
old_func = s[start:end]
new_func = '''def post_due_videos():
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
                            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                            "--merge-output-format", "mp4",
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
                print(f"Error job {job.id}: {e}")

'''
result = s.replace(old_func, new_func)
open('app.py','w').write(result)
print('Done!' if old_func in s else 'NOT FOUND')
