lines = open('app.py').readlines()
for i, line in enumerate(lines):
    if 'os.makedirs(os.path.dirname(job.filepath)' in line:
        lines[i] = '                  os.makedirs(os.path.dirname(job.filepath), exist_ok=True)\n'
        print(f'Fixed line {i+1}')
open('app.py','w').writelines(lines)
print('Done!')
