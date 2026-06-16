lines = open('app.py').readlines()
new_lines = []
skip = 0
for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    if 'if not os.path.exists(job.filepath):' in line and 'dl_cmd' in lines[i+1]:
        new_lines.append('                  os.makedirs(os.path.dirname(job.filepath), exist_ok=True)\n')
        new_lines.append('                  if not os.path.exists(job.filepath):\n')
        new_lines.append('                      vid_id = os.path.basename(job.filepath).replace(".mp4","")\n')
        new_lines.append('                      dl_cmd = [\n')
        new_lines.append('                          "yt-dlp",\n')
        new_lines.append('                          "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",\n')
        new_lines.append('                          "--merge-output-format", "mp4",\n')
        new_lines.append('                          "-o", job.filepath,\n')
        new_lines.append('                          "https://www.youtube.com/shorts/" + vid_id\n')
        new_lines.append('                      ]\n')
        new_lines.append('                      result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=600)\n')
        new_lines.append('                      print(f"Download: {result.returncode} {result.stderr[:100]}")\n')
        skip = 7
    elif 'if not os.path.exists(job.filepath):' in line and 'job.status = "error"' in lines[i+1]:
        new_lines.append('                  if not os.path.exists(job.filepath):\n')
        new_lines.append('                      job.status = "error"\n')
        new_lines.append('                      db.session.commit()\n')
        new_lines.append('                      print(f"File missing after download: {job.filepath}")\n')
        new_lines.append('                      continue\n')
        skip = 4
    else:
        new_lines.append(line)
open('app.py','w').writelines(new_lines)
print('Done!')
