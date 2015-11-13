from ASTBuilder import ASTBuilder
import urllib2
import os
import io


def read_source(srcfile):
	return open(srcfile).read()
	
init_attr = dir(io)
def find_caller(graph):
	callers = {}
	for attr in init_attr:
		callees = [attr]
		for node in graph:
			if attr == node.src and node.op == '--becomes--':
				callees.append(node.tgt)
			if node.src in callees and node.op == '--calls--':
				if attr in callers:
					callers[attr].append(node.tgt)
				else:
					callers[attr] = [node.tgt]

	return callers		
				

frequency = {}	
def compute_frequency(callers):
	for attr, callers in callers.items():
		for item in callers:
			key = str(attr)+'->'+str(item)
			if key in frequency:
				frequency[key] += 1
			else:
				frequency[key] = 1
				

		


i = 0
for subdir in os.listdir('repoData'):
#	if i>100:
#		break;
	print('Foldername: ' + subdir)
	filename = 'repoData/' + subdir + '/allPythonContent.py'
	fullfile = read_source(filename)
	file_splits = fullfile.split('########NEW FILE########')
	for piece in file_splits:
		if piece:
			graph = ASTBuilder(piece).build_AST()			
			if graph:
				i += 1
				callers = find_caller(graph)
				compute_frequency(callers)


	
print ('There are ' + str(i) + ' parsable files in total.')
f_freq = open('frequency.txt', 'w')
for key, freq in frequency.items():
#	print key, freq
	f_freq.write(key+' '+str(freq)+'\n')
f_freq.close()
'''
file = read_source('srcfiles/Fetcher.py')
graph =  ASTBuilder(file).build_AST()
callers = find_caller(graph)	
compute_frequency(callers)
for key, freq in frequency.items():
	print key, freq
'''