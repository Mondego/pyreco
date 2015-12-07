import os

f_empty = open('empty.txt', 'w')
for subdir in os.listdir('repoData'):
    print(subdir)
    if subdir=='.DS_Store':
        continue
    filename = 'repoData/' + subdir + '/allPythonContent.py'
    lines=open(filename).readlines()
    if len(lines) == 0:
        f_empty.write(subdir+'\n')
