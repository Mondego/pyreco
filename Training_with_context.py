__author__ = 'andreadsouza'

__author__ = 'andreadsouza'
import sqlite3
import json
import sys
import multiprocessing as mp
from context import process_context

FOLDS=10
LIB="os"
DB_CONN="pyty.db"

def run_queries_for_prj(fold_no, query_text):
    conn=sqlite3.connect(DB_CONN)
    c=conn.cursor()
    prj_queries=json.loads(query_text)
    train_set=[]
    for file_queries in prj_queries["q_list"]:
        folder=prj_queries["folder"]
        filename=file_queries["file"]
        print "Folder-name:"+folder, "File:"+filename
        for query in file_queries["queries"]:
            results=','.join(query['results'])
            process_context
            context=','.join(
                process_context(query['context']),process_types=True, process_values=True)
            train_set.append((query['type'],results,context))

    for fold in range(1,FOLDS+1):
        if fold!=fold_no:
            c.executemany("INSERT INTO TRAINSET_{fold}(obj_type, obj_calls, obj_context) VALUES (?, ?, ?)".format(
            fold=str(fold)),train_set)
    conn.commit()
    conn.close()


def main():
    conn=sqlite3.connect(DB_CONN)
    c=conn.cursor()
    for fold in range(1,FOLDS+1):
        c.execute('''DROP TABLE IF EXISTS TRAINSET_{fold_num}'''.format(fold_num=str(fold)))
        c.execute('''CREATE TABLE TRAINSET_{fold_num} (obj_type text, obj_calls text, obj_context text)'''
                     .format(fold_num=str(fold)))
    conn.commit()

    conn.close()

    pool=mp.Pool(mp.cpu_count())
    jobs=[]
    count=0

    query_file='queries/queries-'+LIB+'.txt'
    with open(query_file,'r') as file:
        query=""
        for line in file:
            if line.strip()=='-' * 20:
                try:
                    job=pool.apply_async(run_queries_for_prj,(count%FOLDS+1, query))
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
