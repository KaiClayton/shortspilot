s = open("app.py").read()
old = """        cmd = [
            "yt-dlp", "--skip-download",
            "--print", "%(id)s|%(title)s|%(view_count)s",
            source.url + "/shorts"
        ]"""
new = """        cmd = [
            "yt-dlp", "--skip-download",
            "--print", "%(id)s|%(title)s|%(view_count)s",
            url + "/shorts"
        ]"""
open("app.py","w").write(s.replace(old,new))
print("Done!" if old in s else "NOT FOUND")

