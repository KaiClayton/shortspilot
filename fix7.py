lines = open('app.py').readlines()
for i in range(155, 175):
    if lines[i].startswith('                  '):
        lines[i] = '                ' + lines[i].lstrip()
        print(f'Fixed line {i+1}')
open('app.py','w').writelines(lines)
print('Done!')
