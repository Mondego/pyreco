__author__ = 'andreadsouza'

from ASTBuilder import ASTBuilder
import re
import sqlite3
from collections import Counter

"""
f=open("srcfiles/query-3.txt")
source=f.read()
f.close()
"""

def get_recommendations(query, fold_no):
    df_graph=None
    source=query.split('\n')
    i=len(source)
    while not df_graph:
        src_lines=source[:i]
        if src_lines:
            df_graph=ASTBuilder('\n'.join(source[:i])).build_AST()
            i-=1

    query_obj_types=[]
    calls=[]
    query_line=re.split(r'[^\w]',source[-1])
    query_obj=filter(None, query_line)[-1]
    assign_nodes, call_nodes= df_graph.find_assignments_and_calls(query_obj)
    for node in assign_nodes:
        query_obj_types.extend(node.src)

    for node in call_nodes:
        calls.append(node.tgt)

    query_count=Counter(calls)

    conn=sqlite3.connect("pyty.db")
    c=conn.cursor()
    objects=[]


    for type in query_obj_types:

        results=c.execute('''SELECT obj_calls FROM TRAINSET_{fold} WHERE obj_type=?'''.
                          format(fold=fold_no),(type,))
        for obj in results:
            obj_calls=obj[0].split(',')
            score=compute_manhattan_dist(query_count,
                                   Counter(obj_calls))
            objects.append((obj_calls, score))

    objects=sorted(objects, key=lambda tup: tup[0])

    call_set=Counter()
    for object in objects:
        call_set.update(Counter(object[0])-query_count)

    recommendations=[call[0] for call in call_set.most_common(10)]
    return recommendations


def compute_manhattan_dist(query_count, object_count):
    query_obj=query_count.copy()
    query_obj.subtract(object_count)
    score=sum(abs(i) for i in query_obj.values())
    return score

"""
get_recommendations(source, 4)
"""