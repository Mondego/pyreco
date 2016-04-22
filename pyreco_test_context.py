__author__ = 'andreadsouza'

import multiprocessing as mp
from GetRecoWithContext import get_recos
import sys
import json

LIB="os"
FOLDS=10

def compute_r_precision(pyreco_results, relevant_results):
    relevant_set=set(relevant_results)
    r_length=len(relevant_set)
    p=0
    if pyreco_results:
        for result in relevant_set:
            if result in pyreco_results[:r_length]:
                p+=1
    return p/float(r_length)


def run_queries_for_prj(fold_no, query_text, q):
    prj_queries=json.loads(query_text)
    def run_query(query_info):
        with open('repoData/'+folder+'/allPythonContent.py', 'r') as f:
            file_content=[line.rstrip() for line in f.readlines()]
            index=file_content.index(str('__FILENAME__ = '+filename))
            line_num=query_info["line"]
            query_lines=file_content[index+1:index+line_num]
            col_offset=query_info['col']
            dot_index=query_lines[-1].find(query_info['call'],  col_offset)
            if dot_index!=-1:
                query_lines[-1]=query_lines[-1][:dot_index]
                results = get_recos('\n'.join(query_lines),fold_no)
                p=compute_r_precision(results, query_info["results"])
                q.put((fold_no-1, results, query_info["results"], p))

    for file_queries in prj_queries["q_list"]:
        folder=prj_queries["folder"]
        filename=file_queries["file"]
        print "Folder-name:"+folder, "File:"+filename
        for query in file_queries["queries"]:
            run_query(query)

def listener(q):
    f=list()
    sum_prec=list()
    count=list()

    for i in range(FOLDS):
        f.append(open('results-pyreco-ctxt/results-'+str(i+1)+'.txt','w'))
        sum_prec.append(0)
        count.append(0)

    while(1):
        msg=q.get()
        if isinstance(msg,tuple):
            n, compl_results, relevant_results, p=msg
            f[n].write("Completion results:"+str(compl_results)+"\n")
            f[n].write("Relevant results:"+str(relevant_results)+"\n")
            f[n].write("R-Precision:"+str(p*100)+"\n")
            f[n].write('-' * 20 + '\n')
            f[n].flush()
            sum_prec[n]+=p
            count[n]+=1

        else:
            f_summary=open('results-pyreco-ctxt/results-summary.txt','w')
            for i in range(FOLDS):
                f[i].close()
                f_summary.write("Fold:"+str(i+1)+"\n")
                f_summary.write("Num_queries:"+str(count[i])+"\n")
                f_summary.write("Avg Precision:"+str((sum_prec[i]/count[i])*100)+"\n")
                f_summary.write('-' * 20 + '\n')
            f_summary.close()
            break


def main():
    manager=mp.Manager()
    pool=mp.Pool(mp.cpu_count())

    q=manager.Queue()

    watcher=pool.apply_async(listener,(q,))

    jobs=[]
    count=0
    query_file='queries/queries-'+LIB+'.txt'
    with open(query_file,'r') as file:
        query=""
        for line in file:
            if line.strip()=='-' * 20:
                try:
                    job=pool.apply_async(run_queries_for_prj,(count%FOLDS+1,query, q))
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

    q.put('kill')
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
