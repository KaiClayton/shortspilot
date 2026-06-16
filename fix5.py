s = open('app.py').read()
old = '@app.route("/debug-kai-only")'
new = '''@app.route("/run-poster-now")
def run_poster_now():
    import threading
    threading.Thread(target=post_due_videos, daemon=True).start()
    return "Poster triggered - check Railway logs and /debug-kai-only in 2-3 minutes"

@app.route("/debug-kai-only")'''
open('app.py','w').write(s.replace(old, new))
print('Done!' if old in s else 'NOT FOUND')
