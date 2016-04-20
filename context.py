# format of the context: "context": {"args": ["basedir", "logs"]}"
import json
from pprint import pprint
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer


def extract_tokens(context_dict):
	args_dict = context_dict['context']
	arguments = args_dict['args']
	# keywords
	# there are different types, need to deal with that
	# turn all elements into token list

def process_tokens(tokens):
	porter_stemmer = PorterStemmer()
	wordnet_lemmatizer = WordNetLemmatizer()
	processed = []
	for token in tokens:
		token = token.lower() # to lowercase
		token = porter_stemmer(token)
		token = wordnet_lemmatizer(token)
		processed.append(token)
	return processed


# main function
with open('check-json.txt') as json_file:
	json_data = json.load(json_file)

#pprint(json_data)

# two root nodes: files and folders
# under files, two nodes: graph and file
# under graph, three nodes: count, graph_dict, start_vertex
# graph_dict is a dictionary about node_num and node_value
# under node_value, which is a dictionary itself, there's dictionary called 'context':''
for graph_file in json_data['files']:
	for node_num, node_value in graph_file['graph']['graph_dict'].items():
		if 'context' in node_value:
			print node_num, node_value['context']
	
