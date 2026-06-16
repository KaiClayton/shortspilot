lines = open('app.py').readlines()
for i in range(157, 168):
    lines[i] = '    ' + lines[i]
    print(f'Fixed line {i+1}')
open('app.py','w').writelines(lines)
print('Done!')
