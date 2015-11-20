import json
import os

frequency = {}
for subdir in os.listdir('repoData'):
	filename = 'repoData/' + subdir + '/libs-new.json'
	print('Foldername: ' + subdir)
	json_data = open(filename).read()
	data = json.loads(json_data)
	for module in data['libs']:
#		print module
		if module in frequency:
			frequency[module] += 1
		else:
			frequency[module] = 1

	
f = open('Top10.txt', 'w')	
for item in frequency.items():
	f.write(str(item[0]) + '\t' + str(item[1]) +'\n')
	
f.close()
		