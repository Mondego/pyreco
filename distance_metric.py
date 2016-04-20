
# Jaccard similarity
# intersection/union

def jaccard_similarity(x, y):
	
	set_x = set(x)
	set_y = set(y)

	# empty sets are always different
	if len(set_x)==0 or len(set_y)==0:
		return 0.0
	return len(set_x & set_y) / len(set_x | set_y)
	
