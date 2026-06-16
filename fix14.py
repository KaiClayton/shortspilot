s = open('app.py').read()
old = '            except Exception as e:\n                print(f"Error job {job.id}: {e}")'
new = '            except Exception as e:\n                import traceback\n                print(f"Error job {job.id}: {e}")\n                print(traceback.format_exc())'
if old in s:
    open('app.py','w').write(s.replace(old,new))
    print('Done!')
else:
    print('NOT FOUND')
    idx = s.find('except Exception as e')
    print(repr(s[idx:idx+100]))
