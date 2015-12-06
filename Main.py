from ASTBuilder import ASTBuilder
import urllib2
import os
import sys
import re


def read_source(srcfile):
	return open(srcfile).read()
	
module = sys
module_str = 'sys'
init_attr = dir(module)
for i in range(len(init_attr)):
	init_attr[i] = module_str + '.' + init_attr[i]

def find_caller(graph):
	callers = {}
	callees = {}
	for node in graph:
		if node.src in init_attr and node.op == '--becomes--':
			callees[node.tgt]=node.src
		if node.op == '--dies--' and node.src in callees.keys():
			del callees[node.src]
		if node.src in callees.keys() and node.op == '--calls--':
			if callees[node.src] in callers.keys():
				callers[callees[node.src]].append(node.tgt)
			else:
				callers[callees[node.src]] = [node.tgt]
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
f_graph = open('graph-' + module_str + '.txt', 'w')
for subdir in os.listdir('repoData'):
#	if i>100:
#		break;
	print('Foldername: ' + subdir)
	f_graph.write('\n' + 'Foldername:' + subdir)
	filename = 'repoData/' + subdir + '/allPythonContent.py'
	fullfile = read_source(filename)
	file_splits = fullfile.split('########NEW FILE########')
	for piece in file_splits:
		piece = piece.strip()
		piece_name = piece.split('\n')[0]	
		graph = ASTBuilder(piece).build_AST()			
		if graph:
			f_graph.write('\n' + piece_name + '\n')
			for node in graph:
				f_graph.write(str(node) + '\n')
			i += 1
			callers = find_caller(graph)
			compute_frequency(callers)
f_graph.close()


print ('There are ' + str(i) + ' parsable files in total.')
f_freq = open('frequency-' + module_str + '.txt', 'w')
for key, freq in frequency.items():
#	print key, freq
	f_freq.write(key+'\t'+str(freq)+'\n')
f_freq.close()
'''
file = read_source('srcfiles/test_src.py')
graph =  ASTBuilder(file).build_AST()
for item in graph:
	print item
<<<<<<< HEAD
callers = find_caller(graph)	
print('-'*20)
=======
callers = find_caller(graph)

>>>>>>> 08a96bb310aacedf09cd0e7c6124d28ceaf1edd6
compute_frequency(callers)
for key, freq in frequency.items():
	print key, freq
'''
<<<<<<< HEAD
=======

>>>>>>> 08a96bb310aacedf09cd0e7c6124d28ceaf1edd6
