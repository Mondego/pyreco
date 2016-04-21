__author__ = 'andreadsouza'

from ASTBuilder import ASTBuilder
import re
import sqlite3
from collections import Counter
from context import process_tokens

"""
f=open("srcfiles/query-1.txt")
source=f.read()
f.close()
"""

def get_recos(query, fold_no):
    df_graph=None
    source=query.split('\n')
    i=len(source)
    while not df_graph:
        src_lines=source[:i]
        if src_lines:
            df_graph=ASTBuilder('\n'.join(source[:i])).build_AST()
            i-=1

    query_obj_types=[]
    query_obj_context=[]
    calls=[]
    query_line=re.split(r'[^\w]',source[-1])
    query_obj=filter(None, query_line)[-1]

    assign_nodes, call_nodes= df_graph.find_assignments_and_calls(query_obj)
    for node in assign_nodes:
        query_obj_types.extend(node.src)
        if node.context:
            query_obj_context.extend(process_tokens(node.context))

    for node in call_nodes:
        calls.append(node.tgt)

    query_count=Counter(calls+query_obj_context)

    conn=sqlite3.connect("pyty.db")
    c=conn.cursor()
    objects=[]

    for type in query_obj_types:
        results=c.execute('''SELECT obj_calls, obj_context FROM TRAINSET_{fold} WHERE obj_type=?'''.
                          format(fold=fold_no),(type,))
        for obj in results:
            obj_count=Counter()
            obj_calls=obj[0].split(',') if obj[0] else ''
            obj_context=obj[1].split(',') if obj[1] else ''
            if obj_calls:
                obj_count+=Counter(obj_calls)
            if obj_context!='':
                obj_count+=Counter(obj_context)

            score=compute_manhattan_dist(query_count, obj_count)
            objects.append((obj_calls, score))

    objects=sorted(objects, key=lambda tup: tup[0])

    call_set=Counter()
    for object in objects:
        call_set.update(Counter(object[0])-query_count)

    recommendations=[call[0] for call in call_set.most_common(10)]
    #print recommendations
    return recommendations


def compute_manhattan_dist(query_count, object_count):
    query_obj=query_count.copy()
    query_obj.subtract(object_count)
    score=sum(abs(i) for i in query_obj.values())
    return score

"""
get_recos(source, 4)
"""