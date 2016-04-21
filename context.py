# format of the context: "context": {"args": ["basedir", "logs"]}"
import json
from pprint import pprint
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer

def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

def extract_tokens(context_dict):
	ret_list = []
	if 'args' in context_dict:
		arguments = context_dict['args']
		ret_list.extend(list(flatten(arguments)))
	if 'keywords' in context_dict:
		keywords = context_dict['keywords']
		ret_list.extend(list(flatten(keywords)))
	return ret_list


def process_tokens(context_dict):
	tokens=extract_tokens(context_dict)
	porter_stemmer = PorterStemmer()
	wordnet_lemmatizer = WordNetLemmatizer()
	processed = []
	for token in tokens:
		if isinstance(token, basestring): # only procses strings
			token = token.lower() # to lowercase
			token = porter_stemmer.stem(token)
			token = wordnet_lemmatizer.lemmatize(token)
		processed.append(token)
	return processed

# main function
'''
test = [['submitCommands', ['SendCommands']], ['cancelCommands', 
['SendCommands']], ['denyCommands', ['SendCommands']], 
['confirmCommands', ['SendCommands']], ['denyText', 'Keep it'], 
['cancelLabel', 'Keep it'], ['submitLabel', 'Change it'], 
['confirmText', 'Change it'], ['cancelTrigger', 'Confirm']]
print list(flatten(test))
'''
'''
with open('graph-28594.txt', 'r') as file:
	json_chunks = file.read().strip().split('--------------------')
	for chunk in json_chunks:
		if chunk:
			json_data = json.loads(chunk)
			#pprint(json_data)
			for graph_file in json_data['files']:
				for node_num, node_value in graph_file['graph']['graph_dict'].items():
					if 'context' in node_value:
						#print node_num, extract_tokens(node_value['context'])
						token_list = extract_tokens(node_value['context'])
						processed_tokens = process_tokens(token_list)
						print node_num, processed_tokens
'''
			
# two root nodes: files and folders
# under files, two nodes: graph and file
# under graph, three nodes: count, graph_dict, start_vertex
# graph_dict is a dictionary about node_num and node_value
# under node_value, which is a dictionary itself, there's dictionary called 'context':''

