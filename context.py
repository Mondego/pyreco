import re
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
	if 'arg_val' in context_dict:
		arguments = context_dict['arg_val']
		ret_list.extend(list(flatten(arguments)))
	if 'keyword_val' in context_dict:
		keywords = context_dict['keyword_val']
		ret_list.extend(list(flatten(keywords)))
	if 'keyword_key' in context_dict:
		keywords = context_dict['keyword_key']
		ret_list.extend(list(flatten(keywords)))
	return ret_list

def extract_types(context_dict):
	ret_list = []
	if 'arg_type' in context_dict:
		arguments = context_dict['arg_type']
		ret_list.extend(list(flatten(arguments)))
	if 'keyword_type' in context_dict:
		keywords = context_dict['keyword_type']
		ret_list.extend(list(flatten(keywords)))

	return ret_list

def process_obj_name(name):
	ret_list=[]
	stemmer=PorterStemmer()
	splits=split_tokens(name)
	for split in splits:
		split=split.lower()
		ret_list.append(
			stemmer.stem(split)
		)


	return ret_list

def camel_case_split(identifier):
    matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return [m.group(0) for m in matches]

def split_tokens(identifier):
	#print identifier
	word_list=[]
	words=camel_case_split(identifier)
	for word in words:
		word= word.replace("_", " ")
		word_list.extend(
			re.split(r'[^\w]', word))
	return word_list

def process_tokens(context_dict):
	tokens=extract_tokens(context_dict)
	porter_stemmer = PorterStemmer()
	#wordnet_lemmatizer = WordNetLemmatizer()
	processed = []
	for token in tokens:
		if isinstance(token, basestring): # only procses strings
			token_splits=split_tokens(token)

			for split in token_splits:
				split=split.lower()
				split = porter_stemmer.stem(split)
				#split = wordnet_lemmatizer.lemmatize(split)
				processed.append(split)
	return processed

def process_context(context_dict, process_types=False, process_values=False):
	processed_list=[]
	if process_values:
		processed_list.extend(
			process_tokens(context_dict))
	if process_types:
		processed_list.extend(
			extract_types(context_dict))
	return processed_list
# main function

#print process_obj_name('test_runn')
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

