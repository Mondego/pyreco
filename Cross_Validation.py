__author__ = 'andreadsouza'
import json
import random
from sklearn.cross_validation import ShuffleSplit

LIB='os'

query_info={}

def create_queries(folder, query_info):
    queries=[]
    for file in query_info:
        f=open('repoData/'+folder+'/allPythonContent.py','r')
        file_content=[line.strip() for line in f.readlines()]
        print file,folder
        index=file_content.index('__FILENAME__ = '+file)
        for query in query_info[file]:
            if query['op']=='--becomes--':
                result=query['src'].split('.')[-1]
                col_offset=int(query['colOff'])
                query_line=file_content[index+int(query['lNo'])-1]
                result_index=query_line.find(result, col_offset)
                query_line=query_line[:result_index]+'<caret>'
                query='\n'.join(
                    file_content[index+1:index+int(query['lNo'])-2]
                    +[query_line])
                print query
                #add_to_queries(query, result)
    print queries

with open('queries/Queries_'+LIB+'.txt') as data_file:
    query_info = json.load(data_file)
data_file.close()
folders=query_info.keys()
folds=ShuffleSplit(len(folders), n_iter=10,test_size=0.1)
count=1

"""Shuffle the list of projects"""
projects=query_info.keys()
random.shuffle(projects)
print projects

""" Projects in Test/Train """
#10
for fold in range(1):
    test_set=[project for index, project in enumerate(projects) if index%10 == fold]
    train_set=[project for index, project in enumerate(projects) if index%10 != fold]
    for test in test_set:
        query_list = create_queries(project, query_info[project])
        break
