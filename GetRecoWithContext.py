__author__ = 'andreadsouza'

from ASTBuilder import ASTBuilder
import re
import sqlite3
from collections import Counter
from context import process_tokens, \
    extract_types, process_obj_name
import math


MAX_RECOS=10


#f=open("srcfiles/test_jedi.py")
#source=f.read()
#f.close()

keywords=['if','elif','else','for','except']


def process(line):
    #Remove semicolons
    return re.split(
        r'''((?:[^;"'#]|"[^"]*"|'[^']*'|#[^#]*)+)''',
        line)[1::2]

def get_recos(query, fold_no, context_features, fname):
    recommendations=[]
    df_graph=None
    source=[l for l in query.split('\n')]

    source=source[:-1]+process(source[-1])

    """Extract the Query Object"""
    query_line=re.split('=|\(|\)|\:|\,|\\s*',source[-1][:-1])
    query_obj=re.findall(r'([self|\w]+.*)',query_line[-1])[-1]
    query_obj=query_obj.replace('\"','\'')
    #print fname, "query_obj", query_obj

    """Get the data flow graph using the least compilable code in the query"""
    source=source[:-1]+[source[-1]+"query_method"]
    l=len(source)
    i=l
    try_stack=[]
    parenthesis_stack=[]
    is_last_loop=True
    count=0
    while not df_graph:
        for c in source[i-1][::-1]:
            if c in [')','}',']']:
                parenthesis_stack.append(c)
            elif c=='(':
                if not parenthesis_stack or parenthesis_stack[-1]!=')':
                    source[l-1]=source[l-1]+')'
                    #parenthesis_stack.append('(')
                    #i=l
                else:
                    parenthesis_stack.pop()
            elif c=='{':
                if not parenthesis_stack or parenthesis_stack[-1]!='}':
                    source[l-1]=source[l-1]+'}'
                    #parenthesis_stack.append('{')
                    #i=l
                else:
                    parenthesis_stack.pop()
            elif c=='[':
                if not parenthesis_stack or parenthesis_stack[-1]!=']':
                    source[l-1]=source[l-1]+']'
                    #parenthesis_stack.append('{')
                    #i=l
                else:
                    parenthesis_stack.pop()
        split_str=source[i-1].split()

        if split_str and is_last_loop:
            #print split_str
            if split_str[-1][-1]==':':
                is_last_loop=False
        #print "in while", fname
        if 'try:' in source[i-1].strip() \
                and i!=l:
            pos=source[i-1].find('try')
            indent_prefix=source[i-1][:pos]
            if indent_prefix not in try_stack:
                source=source[:l]
                source.append(indent_prefix+'except:')
                source.append(indent_prefix+'\t'+ 'pass')
                try_stack.append(indent_prefix)
                l=l+3
                #except_count+=3
            else:
                try_stack.remove(indent_prefix)
                #except_count=l

        if 'except ' in source[i-1] or 'except:' in source[i-1]\
                and i!=l:
            pos=source[i-1].find('except')
            indent_prefix=source[i-1][:pos]
            if indent_prefix not in try_stack:
                try_stack.append(source[i-1][:pos])

        if is_last_loop and len(split_str)>1:
            if 'if' in split_str[1:] and i==l:
                source[i-1]+=" else ''"

            for word in keywords:
                if word == source[i-1].split()[0]:
                    pos=source[i-1].find(word)
                    indent_prefix=source[i-1][:pos]
                    if source[l-1][-1]!=':':
                        source[l-1]=source[l-1]+':'
                    source.append(indent_prefix+'\t'+'pass')
                    if word=='except':
                        try_stack.append(indent_prefix)
                    l=l+1
                    is_last_loop=False
                    break





        df_graph=ASTBuilder('\n'.join(source[:l])).build_AST()
        #df_graph=ASTBuilder('\n'.join(source[:i]+source[l:except_count])).build_AST()
        #print '\n'.join(source[:l][-40:])
        #print '\n'.join(source[:i]+source[l:except_count])

        # print source[i-1], try_stack
        # print '\n'.join(source[:i]+source[l:except_count][-20:])
        #print '-'*40, source[i-1]

        i=i-1
        count+=1

        if i==0:
            break

        if count>500:
            print  fname, "INFINITE LOOP"
            break



    """Get Nearest Neighbours using Manhattan distance"""
    if df_graph:
        query_obj_types=[]
        query_obj_context=[]
        calls=[]
        sql_query=[]
        assign_nodes=[]
        assign_nodes, call_nodes=df_graph.find_definitions_and_calls(query_obj)

        if assign_nodes:
            for node in assign_nodes:
                #print node
                query_obj_types.extend(node.src)
                if node.context:
                    #print node.context, context_features
                    for feature in context_features:
                        if feature=='arg_type':
                            sql_query.append('arg_types')
                            query_obj_context.extend(
                                extract_types(node.context))
                        elif feature=='arg_value':
                            sql_query.append('arg_values')
                            query_obj_context.extend(
                                process_tokens(node.context))
                        elif feature=='object_name':
                            sql_query.append('obj_name')
                            query_obj_context.extend(
                                process_obj_name(node.tgt)
                            )

            for node in call_nodes:
                calls.append(node.tgt)

            sql_query.append('calls')

            query_count=Counter(calls+query_obj_context)

            conn=sqlite3.connect("pyty.db")
            c=conn.cursor()
            objects=[]
            for type in query_obj_types:
                sql_select='''SELECT {attr} FROM TRAINSET_{fold} WHERE obj_type=?'''.format(
                    attr=','.join(sql_query),fold=fold_no)
                results=c.execute(sql_select,(type,))
                if results:
                    for obj in results:
                        obj_count=Counter()
                        for i in range(len(obj)):
                            if obj[i]:
                                obj_count+=Counter(obj[i].split(','))
                        obj_calls=obj[-1].split(',') if obj[-1] else ''
                        score=compute_manhattan_dist(query_count, obj_count)
                        objects.append((obj_calls, score))

            objects=sorted(objects, key=lambda tup: tup[1])
            call_set=Counter()
            min_score =''
            for object in objects:
                if min_score=='':
                    min_score=object[1]
                if object[1]==min_score:
                    call_set.update(Counter(object[0])-query_count)
                elif len(call_set)<MAX_RECOS:
                    min_score=object[1]
                else:
                    break
            total=float(sum(call_set.values()))
            recommendations.extend([call[0] for call in call_set.most_common(MAX_RECOS)])
        return recommendations


def compute_manhattan_dist(query_count, object_count):
    score=0
    for key in query_count:
        score+=abs(query_count[key]-object_count[key])
    return score

def compute_euclidean_dist(query_count, object_count):
    score=math.sqrt(sum((query_count[k] - object_count[k])**2
                        for k in query_count.keys()))
        #score+=abs(query_count[key]-object_count[key])
    return score

#print get_recos(source, 4,'','django')
