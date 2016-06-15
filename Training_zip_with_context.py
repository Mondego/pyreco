__author__ = 'andreadsouza'
import sqlite3
import json
import sys
import multiprocessing as mp
from context import extract_types,process_tokens,process_obj_name

FOLDS=10

LIBS=["django",
      "os",
      "re",
      "collections",
      "json",
      "threading",
      "simplejson",
      "encode",
      "decimal",
      "cStringIO",
      "jeevesdb",
      "importlib",
    "discover_runner",
    "coffin",
    "freenasUI",
    "iondb",
    "formtools",
    "nogeos",
    "south"]
DB_CONN="pyty.db"

def run_query_for_prj(fold_no, query_text):
    conn=sqlite3.connect(DB_CONN)
    c=conn.cursor()
    query_info=json.loads(query_text)
    folder, filename=query_info["folder"],query_info["file"]
    print "Folder-name:"+folder, "File:"+filename
    call_list=[]
    for call in query_info["calls"]:
        call_list.append(call["tgt"])
    calls=','.join(call_list)
    arg_types=','.join(extract_types(query_info['context']))
    arg_values=','.join(process_tokens(query_info['context']))
    obj_name=','.join(process_obj_name(query_info['obj']))
    for fold in range(1,FOLDS+1):
        if fold!=fold_no:
            try:
                c.execute(
                    "INSERT INTO TRAINSET_{fold} (obj_type, obj_name, calls, arg_types, arg_values) VALUES (?, ?, ?, ?, ?)".format(fold=str(fold)),
                    (query_info['type'], obj_name, calls, arg_types, arg_values))
            except sqlite3.OperationalError, msg:
                print msg

    conn.commit()
    conn.close()

def run_queries(fold_no, prj_query):
    delim='-'*20+'\n'
    queries=prj_query.split(delim)
    for query in queries:
        #print query
        #print "blah"
        run_query_for_prj(fold_no, query)


def main():
    conn=sqlite3.connect(DB_CONN)
    c=conn.cursor()
    for fold in range(1,FOLDS+1):
        c.execute('''DROP TABLE IF EXISTS TRAINSET_{fold_num}'''.format(fold_num=str(fold)))
        c.execute('''CREATE TABLE TRAINSET_{fold_num} (obj_type text, obj_name text, calls text, arg_types text, arg_values text)'''.format(fold_num=str(fold)))
    conn.commit()
    conn.close()

    pool=mp.Pool(mp.cpu_count())
    jobs=[]
    count=0

    for lib in LIBS:
        query_file='queries/query-'+lib+'.txt'
        with open(query_file,'r') as file:
            query=""
            for line in file:
                if line.strip()=='$' * 20:
                    try:
                        job=pool.apply_async(run_queries,(count%FOLDS+1, query))
                        jobs.append(job)
                        query=""
                        count+=1

                    except:
                        print "Unexpected error in worker:", sys.exc_info()[0]
                else:
                    query+=line


    for job in jobs:
        try:
            job.get()
        except:
            continue

    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
