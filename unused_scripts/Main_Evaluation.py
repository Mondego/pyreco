__author__ = 'andreadsouza'
from GraphNode import GraphNode
from operator import itemgetter
import urllib2
import os
import sys
import re


def read_source(srcfile):
	return open(srcfile).read()


module = re
module_str = 're'
init_attr = dir(module)
for i in range(len(init_attr)):
	init_attr[i] = module_str + '.' + init_attr[i]

api_freq = {}

def add_to_api_freq(source, prev,curr):
	key=prev+'->'+curr
	if source in api_freq.keys():
		if key in api_freq[source].keys():
			api_freq[source][key]=api_freq[source][key]+1
		else:
			api_freq[source][key]=1
	else:
			api_freq[source]={}
			api_freq[source][key]=1

def find_caller(graph):
	callers = {}
	callees = {}
	for node in graph:
		if node.src in init_attr and node.op == '--becomes--':
			callees[node.tgt] = node.src
		if node.op == '--dies--' and node.src in callees.keys():
			del callees[node.src]
		if node.src in callees.keys() and node.op == '--calls--':
			if callees[node.src] in callers.keys():
				callers[callees[node.src]].append(node.tgt)
				add_to_api_freq(
					callees[node.src],
					module_str + '.' + callers[callees[node.src]][-2],
					module_str + '.' + node.tgt)
			else:
				callers[callees[node.src]] = [node.tgt]
				add_to_api_freq(
					callees[node.src],
					callees[node.src],
					module_str + '.' + node.tgt)
	return callers

frequency = {}


def compute_frequency(callers):
	for attr, callers in callers.items():
		for item in callers:
			key = str(attr) + '->' + str(item)
			if key in frequency:
				frequency[key] += 1
			else:
				frequency[key] = 1


with open('graph.txt') as f:
	current_graph = []
	for line in f:
		line = line.strip()
		if line.startswith('Foldername') or line == '':
			pass
		elif line.startswith('__FILENAME__') \
				or line.startswith('-' * 20):
			if current_graph != []:
				compute_frequency(find_caller(current_graph))
			current_graph = []
		elif len(line.split()) == 2:
			node = line.split()
			current_graph.append(
				GraphNode(node[0], node[1], ''))
		elif len(line.split()) == 3:
			node = line.split()
			current_graph.append(
				GraphNode(node[0], node[1], node[2]))

f_freq = open('frequency-' + module_str + '.txt', 'w')
for key, freq in frequency.items():
	f_freq.write(key + '\t' + str(freq) + '\n')
f_freq.close()

f_api_freq = open('frequency-api-' + module_str + '.txt', 'w')
sorted_freq = sorted(api_freq.items(), key=itemgetter(0))

for source, freqdict in sorted_freq:
	f_api_freq.write(source+'\n')
	for key, value in sorted(freqdict.items(), key=itemgetter(1), reverse=True):
		f_api_freq.write(key + '\t' + str(freq) + '\n')
	f_api_freq.write('\n')
f_api_freq.close()