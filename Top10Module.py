from GraphNode import GraphNode
from operator import itemgetter
import json
import os

"""
Script to get the most frequently used modules
"""

frequency = {}
queries = {}
libs_used = []

def convert_to_dict(node):
    node_dict={}
    node_dict['src']=node.src
    node_dict['op']=node.op
    node_dict['tgt']=node.tgt
    node_dict['lNo']=node.lineNum
    node_dict['colOff']=node.colOffset
    return node_dict

def add_to_queries(lib, node, folder, file):
    if lib in queries.keys():
        if folder in queries[lib].keys():
            if file in queries[lib][folder].keys():
                node_obj=convert_to_dict(node)
                if node_obj not in queries[lib][folder][file]:
                    queries[lib][folder][file].append(
                        convert_to_dict(node))
            else:
                queries[lib][folder][file]=[
                    convert_to_dict(node)]
        else:
            queries[lib][folder]={file:[
                convert_to_dict(node)]}
    else:
        queries[lib]={folder:
            {file:[
            convert_to_dict(node)]}}

def find_libs(graph, folder, file):
    lib_callees={}
    for node in graph:
        if '.' in node.src and node.op == '--becomes--':
            pos = node.src.find('.')
            lib = node.src[:pos] if pos!=-1 else ''
            if len(lib)!=0 and ':' not in lib:
                try:
                   # __import__(lib)
                    if lib not in libs_used:
                        libs_used.append(lib)
                    lib_callees[node.tgt]=lib
                    add_to_queries(lib, node, folder, file)
                except ImportError:
                    pass
                except:
                    pass
        elif node.op == '--calls--':
            if node.src in lib_callees.keys():
                lib=lib_callees[node.src]
                add_to_queries(lib, node, folder, file)
        else:
            if node.src in lib_callees.keys():
                del lib_callees[node.src]

with open('graph_new.txt') as f:
    current_graph = []
    folderName = ''
    fileName = ''
    for line in f:
        if line == '':
            pass
        if line.startswith('Foldername'):
            folderName = line.split(':')[1]
            print folderName
            pass
        elif line.startswith('-' * 20):
            if current_graph != []:
                find_libs(current_graph,
                          folderName,
                          fileName)
        elif line.startswith('__FILENAME__'):
            if current_graph != []:
                find_libs(current_graph,
                          folderName,
                          fileName)
                current_graph = []
            fileName = line.split()[2]
            print '\tfile:'+fileName
        elif len(line.split()) == 2:
            node = line.split()
            current_graph.append(
                GraphNode(node[0], node[1], ''))
        elif len(line.split()) == 3:
            node = line.split()
            current_graph.append(
                GraphNode(node[0], node[1], node[2]))
        elif len(line.split()) == 5:
            node = line.split()
            current_graph.append(
                GraphNode(node[0], node[1], node[2],
                          node[3], node[4]))

for lib in libs_used:
    frequency[lib]=0
    for file in queries[lib].keys():
        frequency[lib] += len(file)

f1 = open('Top10.txt', 'w')
count = 0
for lib, freq in sorted(frequency.items(), key=itemgetter(1), reverse=True):
    count += 1
    f1.write(lib + '\t' + str(freq) + '\n')
    f2=open('queries1/Queries_'+lib+'.txt', 'w')
    data=queries[lib]
    json.dump(data, f2, sort_keys=True, indent = 4, ensure_ascii=False)
    if count==10:
        break
f.close()
