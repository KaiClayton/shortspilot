s = open('app.py').read()
old = '''                        dl_cmd = [
                            "yt-dlp",
                            "--extractor-args", "youtube:player_client=ios",
                            "-f", "best[ext=mp4]/best",
                            "--merge-output-format", "mp4",
                            "--no-check-formats",
                            "-o", job.filepath,
                            "https://www.youtube.com/shorts/" + vid_id
                        ]'''
new = '''                        dl_cmd = [
                            "yt-dlp",
                            "--extractor-args", "youtube:player_client=android",
                            "-f", "best[ext=mp4]/best",
                            "--no-check-formats",
                            "--no-playlist",
                            "-o", job.filepath,
                            "https://www.youtube.com/watch?v=" + vid_id
                        ]'''
if old in s:
    open('app.py','w').write(s.replace(old,new))
    print('Done!')
else:
    print('NOT FOUND')
