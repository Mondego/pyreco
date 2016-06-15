__author__ = 'andreadsouza'

import multiprocessing as mp
from GetRecoWithContext import get_recos
import sys
import json
from zipfile import ZipFile

LIB="django"
FOLDS=10


def compute_precision_and_recall(pyreco_results, relevant_result):
    r_length=1
    p=0
    r=0
    num=0
    num1=0
    index=0
    rr=0
    if pyreco_results:
        if relevant_result in pyreco_results:
            num1+=1
            index=pyreco_results.index(relevant_result)+1
            rr=1/float(index)

        if relevant_result in pyreco_results[:r_length]:
            num+=1
        p=num/float(r_length)
        r=num1/float(r_length)
        #index=1/float(index)
    return p,r, rr


def run_query(fold_no, query_info, context_features, q):
    print "Folder-name:"+query_info['folder'], "File:"+query_info['file']
    try:
        zf=ZipFile(query_info['folder'],'r')
        file_lines=[line.rstrip() \
                    for line in zf.read(query_info['file']).splitlines()]
        prev_calls=[]
        for call in query_info['calls']:
            line_num=call["lineNum"]
            query=file_lines[:line_num]
            dot_index=query[-1].find(query_info['obj']+'.'+call['tgt'],
                                      call['colOffset'])
            if dot_index!=-1:
                obj_len=len(query_info['obj'])
                query[-1]=query[-1][:dot_index+obj_len+1]
                results=[]
                try:
                    results = get_recos('\n'.join(query), fold_no,
                                        context_features, query_info['file'])
                except:
                    #exc_type, exc_value, exc_traceback = sys.exc_info()

                    print "Error while calling get_recommendations","File:",query_info['file']

                p,r, rr=compute_precision_and_recall(results, call['tgt'])
                #print p, r, query_info['file']
                q.put((fold_no-1, query_info["type"], results, call['tgt'], p, r, rr, len(prev_calls)+1))
            prev_calls.append(call['tgt'])

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()

        print "Error in run_query",exc_type,exc_traceback.tb_lino

    return


def listener(q, context):
    print "in listener"
    prefix='_'.join(context)
    f=list()
    sum_prec=list()
    sum_recall=list()
    sum_rr_1=list()
    sum_rr_2=list()
    sum_rr_3=list()
    sum_rr_4=list()
    sum_rr=list()
    count=list()
    count_1=list()
    count_2=list()
    count_3=list()
    count_4=list()
    avg_prec=0
    avg_prec_1=0
    avg_prec_2=0
    avg_prec_3=0
    avg_prec_4=0
    avg_recall=0
    mean_rr=0


    for i in range(FOLDS):
        f.append(open('results-zip-pyreco-ctxt/results-'+prefix+'-'+str(i+1)+'.txt','w'))
        sum_recall.append(0)
        sum_rr.append(0)
        sum_prec.append(0)
        sum_rr_1.append(0)
        sum_rr_2.append(0)
        sum_rr_3.append(0)
        sum_rr_4.append(0)

        count.append(0)
        count_1.append(0)
        count_2.append(0)
        count_3.append(0)
        count_4.append(0)

    while(1):
        msg=q.get()
        if isinstance(msg, tuple):
            n, type, compl_results, relevant_results, p, r, rr, level=msg
            f[n].write("Object type:"+type+"\n")
            f[n].write("Completion results:"+str(compl_results)+"\n")
            f[n].write("Relevant results:"+str(relevant_results)+"\n")
            f[n].write("Precision:"+str(p*100)+"\n")
            f[n].write("Recall:"+str(r*100)+"\n")
            f[n].write("Reciprocal Rank:"+ str(rr)+'\n')
            f[n].write("Level:"+str(level)+"\n")

            sum_prec[n]+=p
            sum_recall[n]+=r
            sum_rr[n]+=rr
            count[n]+=1
            if level==1:
                sum_rr_1[n]+=rr
                count_1[n]+=1
            elif level==2:
                sum_rr_2[n]+=rr
                count_2[n]+=1
            elif level==3:
                sum_rr_3[n]+=rr
                count_3[n]+=1
            else:
                sum_rr_4[n]+=rr
                count_4[n]+=1
            f[n].write('-' * 20 + '\n')
            f[n].flush()

        elif msg=='kill':
            print "RECEIVED KILL"
            f_summary=open('results-zip-pyreco-ctxt/results-'+prefix+'-''+summary.txt','w')
            for i in range(FOLDS):
                f[i].close()
                if count[i]!=0:
                    f_summary.write("Fold:"+str(i+1)+"\n")
                    f_summary.write("Num_queries:"+str(count[i])+"\n")
                    f_summary.write("Avg Precision:"+str((sum_prec[i]/float(count[i]))*100)+"\n")
                    f_summary.write("Avg Recall:"+str((sum_recall[i]/float(count[i]))*100)+"\n")
                    f_summary.write("Mean RR:"+str(sum_rr[i]/float(count[i]))+"\n")
                    if count_1[i]!=0:
                        f_summary.write("Avg RR for 1st guess:"+str((sum_rr_1[i]/float(count_1[i])))+"\n")
                        avg_prec_1+=sum_rr_1[i]
                    if count_2[i]!=0:
                        f_summary.write("Avg RR for 2nd guess:"+str((sum_rr_2[i]/float(count_2[i])))+"\n")
                        avg_prec_2+=sum_rr_2[i]
                    if count_3[i]!=0:
                        f_summary.write("Avg RR for 3rd guess:"+str((sum_rr_3[i]/float(count_3[i])))+"\n")
                        avg_prec_3+=sum_rr_3[i]
                    if count_4[i]!=0:
                        f_summary.write("Avg RR for 4 or more guess:"+str((sum_rr_4[i]/float(count_4[i])))+"\n")
                        avg_prec_4+=sum_rr_4[i]
                    f_summary.write('-' * 20 + '\n')
                    avg_prec+=sum_prec[i]
                    avg_recall+=sum_recall[i]
                    mean_rr+=sum_rr[i]
            avg_prec/=sum(count)
            avg_recall/=sum(count)
            avg_prec_1/=sum(count_1)
            avg_prec_2/=sum(count_2)
            avg_prec_3/=sum(count_3)
            avg_prec_4/=sum(count_4)
            mean_rr/=sum(count)

            f_summary.write("Avg Precision in all folds:"+str(avg_prec*100)+"\n")
            f_summary.write("Avg Recall in all folds:"+str(avg_recall*100)+"\n")
            f_summary.write("Mean RR in all folds:"+str(mean_rr)+"\n")
            f_summary.write("Avg RR for 1st guess in all folds:"+str(avg_prec_1)+"\n")
            f_summary.write("Count for 1st guess:"+str(sum(count_1))+"\n")
            f_summary.write("Avg RR for 2nd guess in all folds:"+str(avg_prec_2)+"\n")
            f_summary.write("Count for 2nd guess:"+str(sum(count_2))+"\n")
            f_summary.write("Avg RR for 3rd guess in all folds:"+str(avg_prec_3)+"\n")
            f_summary.write("Count for 3rd guess:"+str(sum(count_3))+"\n")
            f_summary.write("Avg RR for 4th or more guess guess in all folds:"+str(avg_prec_4)+"\n")
            f_summary.write("Count for 4th guess:"+str(sum(count_4))+"\n")
            f_summary.close()
            break

def run_queries(fold_no, prj_query, context_features, q):
    delim='-'*20+'\n'
    queries=prj_query.split(delim)
    for query in queries:
        query_json=json.loads(query)
        #print query
        #print "blah"
        run_query(fold_no, query_json, context_features, q)


def main():
    #context_features=raw_input("arg_type, arg_value, object_name:")
    #context_features=[
    #    [],
    #    ['arg_type'],
    #    ['arg_value'],
    #    ['object_name'],
    #    ['arg_value', 'object_name'],
    #    ['arg_type', 'arg_value'],
    #    ['object_name','arg_type'],
    #    ['object_name','arg_type','arg_value']]
    context_features=[['object_name']]
    query_file='queries/query-'+LIB+'.txt'
    for context in context_features:
        manager=mp.Manager()
        pool=mp.Pool(mp.cpu_count())
        q=manager.Queue()
        watcher=pool.apply_async(listener,(q,context))
        jobs=[]
        count=0

        with open(query_file,'r') as file:
            query=""
            for line in file:
                if line.strip()=='$' * 20:
                    try:
                        #query_json=json.loads(query)
                        #if query_json['folder']=='/home/andrea/github-projects-50/django-django.zip':
                        job=pool.apply_async(run_queries,(count%FOLDS+1,query, context, q))
                        jobs.append(job)
                        count+=1
                        query=""

                    except:
                        print "Unexpected error in worker:", sys.exc_info()[0]
                        pass

                else:
                    query+=line

        print "Sent jobs for processing"

        for job in jobs:
            try:
                job.get()
            except:
                pass

        q.put('kill')
        pool.close()
        pool.join()

if __name__ == '__main__':
    main()
