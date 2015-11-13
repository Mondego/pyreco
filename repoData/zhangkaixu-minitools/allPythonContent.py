__FILENAME__ = cws
#!/usr/bin/python3
# Zhang, Kaixu: kareyzhang@gmail.com
import argparse
import sys
import json
import time
import math

class Weights(dict): # 管理平均感知器的权重
    def __init__(self,penalty='no'):
        self._values=dict()
        self._last_step=dict()
        self._step=0
        self._ld=0.0001
        self._p=0.999
        self._log_p=math.log(self._p)


        self._acc=dict()
        #self._new_value=self._l1_regu
        pena={'no':self._no_regu,'l1':self._l1_regu,'l2':self._l2_regu}
        self._new_value=pena[penalty]

    def _no_regu(self,key):
        dstep=self._step-self._last_step[key]
        value=self._values[key]

        # no regularization
        new_value=value
        self._acc[key]+=dstep*value

        self._values[key]=new_value
        self._last_step[key]=self._step
        return new_value

    def _l1_regu(self,key):
        dstep=self._step-self._last_step[key]
        value=self._values[key]

        # l1-norm regularization
        dvalue=dstep*self._ld
        new_value=max(0,abs(value)-dvalue)*(1 if value >0 else -1)
        if new_value==0 :
            self._acc[key]+=(value)*(value/self._ld)/2
        else :
            self._acc[key]+=(value+new_value)*dstep/2

        self._values[key]=new_value
        self._last_step[key]=self._step
        return new_value

    def _l2_regu(self,key):
        dstep=self._step-self._last_step[key]
        value=self._values[key]

        # l2-norm regularization
        new_value=value*math.exp(dstep*self._log_p)
        self._acc[key]+=value*(1-math.exp(dstep*self._log_p))/(1-self._p)

        self._values[key]=new_value
        self._last_step[key]=self._step
        return new_value

    def update_all(self):
        for key in self._values:
            self._new_value(key)
    def update_weights(self,key,delta): # 更新权重
        if key not in self._values : 
            self._values[key]=0
            self._acc[key]=0
            self._last_step[key]=self._step
        else :
            self._new_value(key)

        self._values[key]+=delta

    def average(self): # 平均
        self._backup=dict(self._values)
        for k,v in self._acc.items():
            self._values[k]=self._acc[k]/self._step
    def unaverage(self): 
        self._values=dict(self._backup)
        self._backup.clear()
    def save(self,filename):
        json.dump({k:v for k,v in self._values.items() if v!=0.0},
                open(filename,'w'),
                ensure_ascii=False,indent=1)
    def load(self,filename):
        self._values.update(json.load(open(filename)))
        self._last_step=None
    
    def get_value(self,key,default):
        if key not in self._values : return default
        if self._last_step==None : return self._values[key]
        return self._new_value(key)

class CWS :
    def __init__(self,penalty='no'):
        self.weights=Weights(penalty=penalty)
    def gen_features(self,x): # 枚举得到每个字的特征向量
        for i in range(len(x)):
            left2=x[i-2] if i-2 >=0 else '#'
            left1=x[i-1] if i-1 >=0 else '#'
            mid=x[i]
            right1=x[i+1] if i+1<len(x) else '#'
            right2=x[i+2] if i+2<len(x) else '#'
            features=['1'+mid,'2'+left1,'3'+right1,
                    '4'+left2+left1,'5'+left1+mid,'6'+mid+right1,'7'+right1+right2]
            yield features
    def update(self,x,y,delta): # 更新权重
        for i,features in zip(range(len(x)),self.gen_features(x)):
            for feature in features :
                self.weights.update_weights(str(y[i])+feature,delta)
        for i in range(len(x)-1):
            self.weights.update_weights(str(y[i])+':'+str(y[i+1]),delta)
    def decode(self,x): # 类似隐马模型的动态规划解码算法
        # 类似隐马模型中的转移概率
        transitions=[ [self.weights.get_value(str(i)+':'+str(j),0) for j in range(4)]
                for i in range(4) ]
        # 类似隐马模型中的发射概率
        emissions=[ [sum(self.weights.get_value(str(tag)+feature,0) for feature in features) 
            for tag in range(4) ] for features in self.gen_features(x)]
        # 类似隐马模型中的前向概率
        alphas=[[[e,None] for e in emissions[0]]]
        for i in range(len(x)-1) :
            alphas.append([max([alphas[i][j][0]+transitions[j][k]+emissions[i+1][k],j]
                                        for j in range(4))
                                        for k in range(4)])
        # 根据alphas中的“指针”得到最优序列
        alpha=max([alphas[-1][j],j] for j in range(4))
        i=len(x)
        tags=[]
        while i :
            tags.append(alpha[1])
            i-=1
            alpha=alphas[i][alpha[1]]
        return list(reversed(tags))

def load_example(words): # 词数组，得到x，y
    y=[]
    for word in words :
        if len(word)==1 : y.append(3)
        else : y.extend([0]+[1]*(len(word)-2)+[2])
    return ''.join(words),y

def dump_example(x,y) : # 根据x，y得到词数组
    cache=''
    words=[]
    for i in range(len(x)) :
        cache+=x[i]
        if y[i]==2 or y[i]==3 :
            words.append(cache)
            cache=''
    if cache : words.append(cache)
    return words

class Evaluator : # 评价
    def __init__(self):
        self.std,self.rst,self.cor=0,0,0
        self.start_time=time.time()
    def _gen_set(self,words):
        offset=0
        word_set=set()
        for word in words:
            word_set.add((offset,word))
            offset+=len(word)
        return word_set
    def __call__(self,std,rst): # 根据答案std和结果rst进行统计
        std,rst=self._gen_set(std),self._gen_set(rst)
        self.std+=len(std)
        self.rst+=len(rst)
        self.cor+=len(std&rst)
    def report(self):
        precision=self.cor/self.rst if self.rst else 0
        recall=self.cor/self.std if self.std else 0
        f1=2*precision*recall/(precision+recall) if precision+recall!=0 else 0
        print("历时: %.2f秒 答案词数: %i 结果词数: %i 正确词数: %i F值: %.4f"
                %(time.time()-self.start_time,self.std,self.rst,self.cor,f1))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--iteration',type=int,default=5, help='')
    parser.add_argument('--train',type=str, help='')
    parser.add_argument('--test',type=str, help='')
    parser.add_argument('--dev',type=str, help='')
    parser.add_argument('--predict',type=str, help='')
    parser.add_argument('--penalty',type=str, default='no')
    parser.add_argument('--result',type=str, help='')
    parser.add_argument('--model',type=str, help='')
    args = parser.parse_args()
    # 训练
    if args.train: 
        cws=CWS(penalty=args.penalty)
        for i in range(args.iteration):
            print('第 %i 次迭代'%(i+1),end=' '),sys.stdout.flush()
            evaluator=Evaluator()
            for l in open(args.train):
                x,y=load_example(l.split())
                z=cws.decode(x)
                evaluator(dump_example(x,y),dump_example(x,z))
                cws.weights._step+=1
                if z!=y :
                    cws.update(x,y,1)
                    cws.update(x,z,-1)
            evaluator.report()
            cws.weights.update_all()
            cws.weights.average()
            if args.dev :
                evaluator=Evaluator()
                for l in open(args.dev) :
                    x,y=load_example(l.split())
                    z=cws.decode(x)
                    evaluator(dump_example(x,y),dump_example(x,z))
                evaluator.report()
            cws.weights.unaverage()

        #cws.weights.average()
        cws.weights.save(args.model)
    # 使用有正确答案的语料测试
    if args.test : 
        cws=CWS()
        cws.weights.load(args.model)
        evaluator=Evaluator()
        for l in open(args.test) :
            x,y=load_example(l.split())
            z=cws.decode(x)
            evaluator(dump_example(x,y),dump_example(x,z))
        evaluator.report()
    # 对未分词的句子输出分词结果
    if args.model and (not args.train and not args.test) : 
        cws=CWS()
        cws.weights.load(args.model)
        instream=open(args.predict) if args.predict else sys.stdin
        outstream=open(args.result,'w') if args.result else sys.stdout
        for l in instream:
            x,y=load_example(l.split())
            z=cws.decode(x)
            print(' '.join(dump_example(x,z)),file=outstream)

########NEW FILE########
__FILENAME__ = autoencoder
#!/usr/bin/python2
"""
modefied from :
    https://github.com/lisa-lab/DeepLearningTutorials


./autoencoder.py model1 --train 1.pca --vector floats --hidden 20 --lost_func L2 --beta 0 --linear True --learning_rate 0.02 --itera    tion 30
./autoencoder.py model --train vector --vector inds --hidden 50 --beta 0 --learning_rate 0.02 --iteration 30
./autoencoder.py model --vector inds 
"""
import argparse
import cPickle
import gzip
import os
import sys
import time

import numpy

import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams

class dA(object):
    """Denoising Auto-Encoder class (dA)
    """

    def __init__(self, numpy_rng, theano_rng=None, input=None,
                 n_visible=784, n_hidden=500,
                 W=None, bhid=None, bvis=None):
        self.n_visible = n_visible
        self.n_hidden = n_hidden

        # create a Theano random generator that gives symbolic random values
        if not theano_rng:
            theano_rng = RandomStreams(numpy_rng.randint(2 ** 30))

        # note : W' was written as `W_prime` and b' as `b_prime`
        if not W:
            initial_W = numpy.asarray(numpy_rng.uniform(
                      low=-4 * numpy.sqrt(6. / (n_hidden + n_visible)),
                      high=4 * numpy.sqrt(6. / (n_hidden + n_visible)),
                      size=(n_visible, n_hidden)), dtype=theano.config.floatX)
            W = theano.shared(value=initial_W, name='W', borrow=True)

        if not bvis:
            bvis = theano.shared(value=numpy.zeros(n_visible,
                                         dtype=theano.config.floatX),
                                 borrow=True)

        if not bhid:
            bhid = theano.shared(value=numpy.zeros(n_hidden,
                                                   dtype=theano.config.floatX),
                                 name='b',
                                 borrow=True)

        self.W = W
        # b corresponds to the bias of the hidden
        self.b = bhid
        # b_prime corresponds to the bias of the visible
        self.b_prime = bvis
        # tied weights, therefore W_prime is W transpose
        self.W_prime = self.W.T
        self.theano_rng = theano_rng
        # if no input is given, generate a variable representing the input
        if input == None:
            # we use a matrix because we expect a minibatch of several
            # examples, each example being a row
            self.x = T.dmatrix(name='input')
        else:
            self.x = input

        self.params = [self.W, self.b, self.b_prime]

    def get_corrupted_input(self, input, corruption_level):
        return  self.theano_rng.binomial(size=input.shape, n=1,
                                         p=1 - corruption_level,
                                         dtype=theano.config.floatX) * input

    def get_hidden_values(self, input):
        return T.nnet.sigmoid(T.dot(input, self.W) + self.b)

    def get_reconstructed_input(self, hidden,linear=False):
        if linear :
            return T.dot(hidden, self.W_prime) + self.b_prime
        return  T.nnet.sigmoid(T.dot(hidden, self.W_prime) + self.b_prime)

    def get_cost_updates(self, corruption_level, learning_rate, rho=0.1, beta=10,
            linear=False,lost_func='KL'):
        """ This function computes the cost and the updates for one trainng
        step of the dA """

        tilde_x = self.get_corrupted_input(self.x, corruption_level)
        y = self.get_hidden_values(tilde_x)
        z = self.get_reconstructed_input(y,linear=linear)

        #L = - T.sum(self.x * T.log(z) + (1 - self.x) * T.log(1 - z), axis=1)
        
        #
        # sparse
        # rho is the expected (small) fired rate
        #
        a=T.mean(y,axis=0)
        #rho=0.1
        sL=  ( rho*T.log(rho/a)+(1-rho)*T.log((1-rho)/(1-a)) ) 
        
        #lost for the output
        if lost_func=='KL':
            L = - T.sum(self.x * T.log(z) + (1 - self.x) * T.log(1 - z), axis=1)
        elif lost_func=='L2':
            L = T.sum((self.x-z)**2)/2


        #cost = T.mean(L) + T.sum(sL) * beta + T.sum(self.W*self.W)/100
        #cost = T.mean(L) + T.sum(sL) * beta + 1.0/2 * T.sum((self.W)**2) /100.0
        if beta == 0 :
            cost = T.mean(L)
        else :
            cost = T.mean(L) + T.sum(sL) * beta 

        gparams = T.grad(cost, self.params)
        # generate the list of updates
        updates = []
        for param, gparam in zip(self.params, gparams):
            updates.append((param, param - learning_rate * gparam))

        return (cost, updates)


class Inds_Loader():
    @staticmethod
    def load_training_data(lines):
        train_set_x=[]
        n_visible=0
        for line in lines:
            train_set_x.append(line)
            line=line.split()
            vec=[int(x)for x in line]
            if vec:
                n_visible=max(n_visible,max(vec)+1)
        train_set_x=[Inds_Loader.load_line(x,n_visible) for x in train_set_x]
        return train_set_x, n_visible

    @staticmethod
    def load_line(line,n_visible=None):
        line=line.split()
        vec=[int(x)for x in line]
        v=[0 for i in range(n_visible)]
        for ind in vec:
            v[(ind)]=1
        return numpy.array(v)

class Floats_Loader():
    @staticmethod
    def load_training_data(lines):
        train_set_x=[]
        n_visible=0
        for line in lines:
            line=line.split()
            line=list(map(float,line))
            #line=list(map(lambda x: float(x)*10,line))
            train_set_x.append(numpy.array(line))
        return train_set_x, len(train_set_x[0])

    @staticmethod
    def load_line(line,n_visible=None):
        line=line.split()
        v=list(map(float,line))
        #v=list(map(lambda x : float(x)*10,line))
        return numpy.array(v)

    

def test_dA(learning_rate=0.01, training_epochs=15,
            dataset="",modelfile="",
            batch_size=20, output_folder='dA_plots',
            n_visible=1346,n_hidden=100,
            beta=0,rho=0.5,noise=0.3,
            linear=False,lost_func='KL',
            loader=None):

    data=map(lambda x : x.partition(' ')[2],open(dataset))
    train_set_x,n_visible=loader.load_training_data(data)

    print >>sys.stderr, "number of training example", len(train_set_x)
    print >>sys.stderr, "batch size", batch_size

    print >>sys.stderr, "number of visible nodes", n_visible
    print >>sys.stderr, "number of hidden nodes", n_hidden

    print >>sys.stderr, "corruption_level",noise
    print >>sys.stderr, "sparse rate",rho,"weight",beta

    print >>sys.stderr, "learning rate", learning_rate
    # compute number of minibatches for training, validation and testing
    n_train_batches = len(train_set_x) / batch_size
    #print(n_train_batches)


    # allocate symbolic variables for the data
    index = T.lscalar()    # index to a [mini]batch
    x = T.matrix('x')  # the data is presented as rasterized images
    data_x=numpy.array([[0 for i in range(n_visible)]for j in range(batch_size)])
    shared_x = theano.shared(numpy.asarray(data_x,
                                           dtype=theano.config.floatX),
                             borrow=True)

    #####################################

    rng = numpy.random.RandomState(123)
    theano_rng = RandomStreams(rng.randint(2 ** 30))

    da = dA(numpy_rng=rng, theano_rng=theano_rng, input=x,
            n_visible=n_visible, n_hidden=n_hidden)

    cost, updates = da.get_cost_updates(corruption_level=noise,
                                        learning_rate=learning_rate,
                                        beta=beta,rho=rho,
                                        linear=linear,lost_func=lost_func)

    train_da = theano.function([], cost, updates=updates,
         givens={x: shared_x})

    start_time = time.clock()

    # TRAINING #
    for epoch in xrange(training_epochs):
        # go through trainng set
        c = []
        for batch_index in xrange(n_train_batches):
            sub=train_set_x[batch_index * batch_size : (1+batch_index)*batch_size]
            sub=numpy.array(sub)
            shared_x.set_value(sub)
            c.append(train_da())
        print 'Training epoch %d, cost ' % epoch, numpy.mean(c)

    end_time = time.clock()

    training_time = (end_time - start_time)

    print >> sys.stderr, (' ran for %.2fm' % (training_time / 60.))

    modelfile=gzip.open(modelfile,"wb")
    cPickle.dump([n_visible, n_hidden],modelfile)
    cPickle.dump([da.W,da.b,da.b_prime],modelfile)
    modelfile.close()


def predict(modelfile,threshold=0.5,loader=None,form='values'):
    modelfile=gzip.open(modelfile)
    n_visible,n_hidden=cPickle.load(modelfile)
    paras=cPickle.load(modelfile)
    modelfile.close()
    # allocate symbolic variables for the data
    x = T.matrix()  # the data is presented as rasterized images
    data_x=numpy.array([[0 for i in range(n_visible)]])
    shared_x = theano.shared(numpy.asarray(data_x,
                                           dtype=theano.config.floatX),
                             borrow=True)

    rng = numpy.random.RandomState(123)
    theano_rng = RandomStreams(rng.randint(2 ** 30))

    da = dA(numpy_rng=rng, theano_rng=theano_rng, input=x,
            n_visible=n_visible, n_hidden=n_hidden,
            W=paras[0], bhid=paras[1], bvis=paras[2])

    y=da.get_hidden_values(da.x)

    predict_da = theano.function([], y,
            givens={x: shared_x})

    for line in sys.stdin :
        word,_,line=line.partition(' ')
        v=loader.load_line(line,n_visible)
        shared_x.set_value(numpy.array([v]))
        res=predict_da()[0]
        #print word,' '.join([str(ind) for ind, v in enumerate(res) if float(v)>threshold])
        if form =='values':
            print word,' '.join([str(v) for ind, v in enumerate(res)])
        #print word,' '.join([str(ind)+":"+str(v) for ind, v in enumerate(res) if float(v)>threshold])
        sys.stdout.flush()

def output_weights(modelfile,indexfile):
    conts={}
    for line in open(indexfile):
        cont,ind=line.split()
        conts[int(ind)]=cont

    modelfile=gzip.open(modelfile)
    n_visible,n_hidden=cPickle.load(modelfile)
    paras=cPickle.load(modelfile)

    W=paras[0].get_value().T
    for j,V in enumerate(W) :
        V=sorted(enumerate(V),key=lambda x:x[1],reverse=True)[:10]
        V=[conts[i] for i,_ in V]
        print(str(j)+" :  "+' | '.join(V))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model',  type=str)
    
    parser.add_argument('--train',  type=str)
    parser.add_argument('--hidden',  type=int,default=50)
    parser.add_argument('--batch_size',  type=int,default=20)
    parser.add_argument('--iteration',  type=int,default=15)
    parser.add_argument('--noise',  type=float,default=0.1)
    parser.add_argument('--beta',  type=float,default=0.0)
    parser.add_argument('--rho',  type=float,default=0.1)
    parser.add_argument('--learning_rate',  type=float,default=0.01)
    parser.add_argument('--predict',  action="store_true")
    parser.add_argument('--threshold',  type=float,default=0.5)
    parser.add_argument('--linear',  type=bool,default=False)
    parser.add_argument('--lost_func',  type=str,default='KL')
    parser.add_argument('--vector',  type=str,default='inds')
    parser.add_argument('--output',  type=str,default='values')
    
    parser.add_argument('--index',  type=str)
    args = parser.parse_args()


    loader_map={'inds': Inds_Loader,
            'floats': Floats_Loader}
    loader=loader_map.get(args.vector,None)
    if loader==None : exit()

    

    if args.train :
        test_dA(dataset=args.train,n_hidden=args.hidden,
                batch_size=args.batch_size,modelfile=args.model,
                beta=args.beta,rho=args.rho,noise=args.noise,
                training_epochs=args.iteration,
                learning_rate=args.learning_rate,
                linear=args.linear,lost_func=args.lost_func,
                loader=loader,
                )
    if args.predict :
        predict(modelfile=args.model,threshold=args.threshold,loader=loader,form=args.output)
    if args.index :
        output_weights(args.model,args.index)


########NEW FILE########
__FILENAME__ = autoencoders
#!/usr/bin/python2
import argparse
import cPickle
import gzip
import os
import sys
import time

import numpy

import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams

class sdA(object):
    def __init__(self, layers, numpy_rng, theano_rng, input):
        self.layers=layers

        self.theano_rng = theano_rng

        self.x = input

        self.params=[]
        for p in self.layers :
            self.params.extend(p)

    def get_corrupted_input(self, input, corruption_level):
        return  self.theano_rng.binomial(size=input.shape, n=1,
                                         p=1 - corruption_level,
                                         dtype=theano.config.floatX) * input

    def get_hidden_values(self, input):
        ys=[]
        for i,paras in enumerate(self.layers) :
            W,b,b_prime=paras
            vector=input if i==0 else ys[i-1]
            ys.append(T.nnet.sigmoid(T.dot(vector, W) + b))
        return ys
    def get_reconstructed_input(self, hidden):
        return  T.nnet.sigmoid(T.dot(hidden, self.W_prime) + self.b_prime)

    def get_cost_updates(self, corruption_level, learning_rate, rho=0.1, beta=10):
        """ This function computes the cost and the updates for one trainng
        step of the dA """

        tilde_x = self.get_corrupted_input(self.x, corruption_level)
        ys=self.get_hidden_values(tilde_x)
        #ys=[]
        #for i,paras in enumerate(self.layers) :
        #    W,b,b_prime=paras
        #    vector=self.x if i==0 else ys[i-1]
        #    ys.append(T.nnet.sigmoid(T.dot(vector, W) + b))

        zs=[None for i in range(len(ys))]
        for i in range(len(self.layers)-1,-1,-1):
            W,b,b_prime=self.layers[i]
            #print(i,len(self.layers))
            vector=ys[-1] if i+1==len(self.layers) else zs[i+1]
            zs[i]=T.nnet.sigmoid(T.dot(vector, W.T) + b_prime)

        #
        # sparse
        # rho is the expected (small) fired rate
        #
        a=T.mean(ys[-1],axis=0)
        #rho=0.1
        sL=  ( rho*T.log(rho/a)+(1-rho)*T.log((1-rho)/(1-a)) ) 
        L = - T.sum(self.x * T.log(zs[0]) + (1 - self.x) * T.log(1 - zs[0]), axis=1)

        #cost = T.mean(L) + T.sum(sL) * beta + T.sum(self.W*self.W)/100
        cost = T.mean(L) + T.sum(sL) * beta

        gparams = T.grad(cost, self.params)
        # generate the list of updates
        updates = []
        for param, gparam in zip(self.params, gparams):
            updates.append((param, param - learning_rate * gparam))

        return (cost, updates)

def make_array(n,vec):
    #print(n,len(vec))
    v=[0 for i in range(n)]
    for ind in vec:
        #print(ind)
        v[(ind)]=1
    return numpy.array(v)

def finetune(dataset,modelfiles,newmodelfile,
        batch_size=20, training_epochs=15,
        noise=0.1,learning_rate=0.1,
        beta=1,rho=0.1,
        ):
    train_set_x=[]
    n_visible=0
    for line in open(dataset):
        line=line.split()
        vec=[int(x)for x in line[1:]]
        if vec:
            n_visible=max(n_visible,max(vec)+1)
        train_set_x.append(vec)


    layers=[]
    nns=[]
    for modelfile in modelfiles :
        modelfile=gzip.open(modelfile)
        nns.append(cPickle.load(modelfile))
        paras=cPickle.load(modelfile)
        layers.append(paras)
        modelfile.close()

    n_visible=nns[0][0]
    print(n_visible)

    rng = numpy.random.RandomState(123)
    theano_rng = RandomStreams(rng.randint(2 ** 30))

    # compute number of minibatches for training, validation and testing
    n_train_batches = len(train_set_x) / batch_size
    #print(n_train_batches)


    # allocate symbolic variables for the data
    index = T.lscalar()    # index to a [mini]batch
    x = T.matrix('x')  # the data is presented as rasterized images
    data_x=numpy.array([[0 for i in range(n_visible)]for j in range(batch_size)])
    shared_x = theano.shared(numpy.asarray(data_x,
                                           dtype=theano.config.floatX),
                             borrow=True)

    sda=sdA(layers, numpy_rng=rng, theano_rng=theano_rng, input=x)

    cost, updates = sda.get_cost_updates(corruption_level=noise,
                                        learning_rate=learning_rate,
                                        beta=beta,rho=rho)

    train_da = theano.function([], cost, updates=updates,
         givens={x: shared_x})

    start_time = time.clock()

    # TRAINING #
    for epoch in xrange(training_epochs):
        # go through trainng set
        c = []
        for batch_index in xrange(n_train_batches):
            sub=train_set_x[batch_index * batch_size : (1+batch_index)*batch_size]
            sub=numpy.array([make_array(n_visible,v)for v in sub])
            shared_x.set_value(sub)
            c.append(train_da())
        print 'Training epoch %d, cost ' % epoch, numpy.mean(c)

    end_time = time.clock()

    training_time = (end_time - start_time)

    print >> sys.stderr, (' ran for %.2fm' % (training_time / 60.))

    newmodelfile=gzip.open(newmodelfile,"wb")
    cPickle.dump([len(modelfiles),n_visible],newmodelfile)
    cPickle.dump(layers,newmodelfile)
    #for nn,para in zip(nns,layers):
    #    cPickle.dump(nn,newmodelfile)
    #    cPickle.dump(para,newmodelfile)
    modelfile.close()


def predict(modelfile,threshold=0.5):
    modelfile=gzip.open(modelfile)
    n_layers,n_visible=cPickle.load(modelfile)
    #print(n_layers,n_visible)
    layers=cPickle.load(modelfile)
    modelfile.close()

    # allocate symbolic variables for the data
    x = T.matrix()  # the data is presented as rasterized images
    data_x=numpy.array([[0 for i in range(n_visible)]])
    shared_x = theano.shared(numpy.asarray(data_x,
                                           dtype=theano.config.floatX),
                             borrow=True)

    rng = numpy.random.RandomState(123)
    theano_rng = RandomStreams(rng.randint(2 ** 30))

    da = sdA(layers,numpy_rng=rng, theano_rng=theano_rng, input=x,
            )

    y=da.get_hidden_values(da.x)[-1]

    predict_da = theano.function([], y,
            givens={x: shared_x})

    for line in sys.stdin :
        line=line.split()
        word=line[0]
        v=make_array(n_visible,map(int,line[1:]))
        shared_x.set_value(numpy.array([v]))
        res=predict_da()[0]
        #print word,' '.join([str(v) for ind, v in enumerate(res) if float(v)>0.5])
        print word,' '.join([str(ind) for ind, v in enumerate(res) if float(v)>threshold])
        sys.stdout.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model',  type=str)
    
    parser.add_argument('--layers', nargs='+', type=str)
    parser.add_argument('--train',  type=str)
    parser.add_argument('--batch_size',  type=int,default=20)
    parser.add_argument('--iteration',  type=int,default=15)
    parser.add_argument('--noise',  type=float,default=0.1)
    parser.add_argument('--beta',  type=float,default=0.0)
    parser.add_argument('--rho',  type=float,default=0.1)

    parser.add_argument('--predict',  action="store_true")
    parser.add_argument('--threshold',  type=float,default=0.5)
    
    parser.add_argument('--index',  type=str)
    args = parser.parse_args()

    if args.train :
        finetune(dataset=args.train,modelfiles=args.layers,
                batch_size=args.batch_size,newmodelfile=args.model,
                beta=args.beta,rho=args.rho,noise=args.noise,
                training_epochs=args.iteration
                )
    if args.predict :
        predict(modelfile=args.model,threshold=args.threshold)
    exit()

    predict('model.gz')

########NEW FILE########
__FILENAME__ = char_lm
#!/usr/bin/python2
"""
modefied from :
    https://github.com/lisa-lab/DeepLearningTutorials
"""
import argparse
import os
import sys
import time

import numpy

import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams


rng = numpy.random.RandomState(123)
numpy.random.seed(123)

def random_matrix(x,y,name):
    initial_W = numpy.asarray(rng.uniform(
              low=-4 * numpy.sqrt(6. / (x+y)),
              high=4 * numpy.sqrt(6. / (x+y)),
              size=(x,y)), dtype=theano.config.floatX)
    return theano.shared(value=initial_W, name=name, borrow=True)

def zero_matrix(x,y):
    a=numpy.array([[0 for i in range(y)]for j in range(x)])
    return theano.shared(numpy.asarray(a, dtype=theano.config.floatX), borrow=True)

class LM(object):
    """Denoising Auto-Encoder class (dA)
    """
    def __init__(self, context,tgt,  K=40,H=100):

        self.W = [ random_matrix(H,K,'W'+str(i)) for i in range(len(context)) ]
        self.Wt = random_matrix(H,K,'Wt') # weight for tgt

        initial_b = numpy.asarray(rng.uniform(
                  low=-4 * numpy.sqrt(6. / (H+1)),
                  high=4 * numpy.sqrt(6. / (H+1)),
                  size=(H)), dtype=theano.config.floatX)
        self.b = theano.shared(value=initial_b, name='b', borrow=True)
        #self.b = random_matrix(H,1,'b') # b for hiddens
        #self.b = theano.shared(value=numpy.zeros(H, dtype=theano.config.floatX), name='b', borrow=True) 

        self.x=context
        self.W2 = random_matrix(1,H,'W2') # weight from hiddens to output
        self.tgt=tgt

        self.internal_params=self.W+[self.b,self.W2,self.Wt]
        self.external_params=self.x+self.tgt
        
        self.params = self.x+self.tgt+self.W+[self.b,self.W2,self.Wt]


    def get_cost_updates(self,learning_rate):
        h=sum([T.dot(W,x) for x,W in zip(self.x,self.W)])
        h=(h.T+self.b).T
        g=T.nnet.sigmoid(h+T.dot(self.Wt,self.tgt[0]))
        g_prime=T.nnet.sigmoid(h+T.dot(self.Wt,self.tgt[1]))
        
        score=T.dot(self.W2,g)
        score_prime=T.dot(self.W2,g_prime)
        #loss=T.sum(T.maximum(0,1+score_prime-score))
        loss=T.sum(T.clip(1 + score_prime - score, 0, 1e999))

        cost=loss

        ginparams = T.grad(cost, self.internal_params)
        gexparams = T.grad(cost, self.external_params)

        inup=[(p,p-learning_rate*gp) for p,gp in zip(self.internal_params,ginparams)]
        exup=[(p,-learning_rate*gp) for p,gp in zip(self.external_params,gexparams)]
        return (score,score_prime,cost, inup+exup)

def read_batch(filename,table,freq,tf,batch_size=1):
    data=[]
    cache=[]
    ln=0
    total_line=int(os.popen('wc -l '+filename).read().partition(' ')[0])
    print total_line


    start_time = time.clock()
    for line in open(filename):
        ln+=1
        x0,x1,y,x2,x3=list(map(int,line.split()))
    #    data.append([x0,x1,y,x2,x3])
    #numpy.random.shuffle(data)


    #for ln,line in enumerate(data) :
    #   x0,x1,y,x2,x3=line
        if y==len(table)-1 : continue
        while True :
            n=numpy.random.randint(tf)
            y_prime=0
            while n>freq[y_prime]:
                n-=freq[y_prime]
                y_prime+=1
            if y_prime and y_prime !=y: break

        inds=[x0,x1,x2,x3,y,y_prime]
        inds=[x if x<len(table)-2 else len(table)-1 for x in inds]

        cache.append(inds)
        if len(cache)==batch_size :
            yield cache
            cache=[]
        if ln % 10000 == 0 :
            end_time = time.clock()
            training_time = (end_time - start_time)
            print >> sys.stderr , str(ln) , (' ran for %.2f sec' % (training_time)) ,training_time/ln*(total_line-ln)/60,'\r',

def test_dA(src,dst,learning_rate=0.05, training_epochs=3,
            dataset="",
            batch_size=20,K=50,H=100 ):

    corpus_file=os.path.join(src,'corpus.txt')
    table_file=os.path.join(src,'table.txt')
    freq_file=os.path.join(src,'freq.txt')

    words=[]
    for line in open(table_file) :
        words.append(line.strip())
    words.append('?')
    print len(words)
    V=len(words) #V=10000# size of words

    #K=50 # dims of a word embedding
    #H=100
    # allocate symbolic variables for the data
    index = T.lscalar()    # index to a [mini]batch

    table=numpy.array([numpy.array([0.0 for i in range(K)]) 
        for j in range(V)])

    #batch_size=1
    x0=zero_matrix(K,batch_size)
    x1=zero_matrix(K,batch_size)
    x2=zero_matrix(K,batch_size)
    x3=zero_matrix(K,batch_size)
    y=zero_matrix(K,batch_size)
    y_prime=zero_matrix(K,batch_size)

    score_p=T.lscalar()
    score=T.lscalar()

    lm=LM([x0,x1,x2,x3],[y,y_prime],K=K,H=H)

    score,score_p,cost, updates = lm.get_cost_updates(learning_rate=learning_rate)

    train_lm = theano.function([], [score,score_p,cost], updates=updates,
            givens={
                x0 : x0, 
                x1:x1,
                x2:x2,
                x3:x3,
                y:y,
                y_prime:y_prime,
                })

    start_time = time.clock()


    freq=[]
    for line in open(freq_file):
        w,f=line.split()
        if w=='#' : continue
        freq.append(int(f))
    tf=sum(freq)

    # TRAINING #
    for epoch in xrange(training_epochs):
        # go through trainng set
        c = []
        for i,ind_mat in enumerate(read_batch(corpus_file,table,freq,tf,batch_size=batch_size)):
            x0.set_value(numpy.array([table[inds[0]]for inds in ind_mat]).T)
            x1.set_value(numpy.array([table[inds[1]]for inds in ind_mat]).T)
            x2.set_value(numpy.array([table[inds[2]]for inds in ind_mat]).T)
            x3.set_value(numpy.array([table[inds[3]]for inds in ind_mat]).T)
            y.set_value(numpy.array([table[inds[4]]for inds in ind_mat]).T)
            y_prime.set_value(numpy.array([table[inds[5]]for inds in ind_mat]).T)

            score,score_p,co=(train_lm())
            c.append(co)
            #print 1+score_p-score
            #print numpy.clip(1+score_p-score,0.0,10000)
            #print co
            #input()

            for inds in ind_mat:
                table[inds[0]]+=x0.get_value().T[0]
                table[inds[1]]+=x1.get_value().T[0]
                table[inds[2]]+=x2.get_value().T[0]
                table[inds[3]]+=x3.get_value().T[0]
                table[inds[4]]+=y.get_value().T[0]
                table[inds[5]]+=y_prime.get_value().T[0]

        print 'Training epoch %d, cost ' % epoch, numpy.mean(c)/batch_size

        modelfile=os.path.join(dst,'model_%d.txt'%(epoch))
        modelfile2=open(modelfile,"w")
        for i in range(table.shape[0]):
            print >>modelfile2,' '.join("%.4f"%x for x in table[i]) 
        modelfile2.close()

    end_time = time.clock()

    training_time = (end_time - start_time)


    print >> sys.stderr, (' ran for %.2fm' % (training_time / 60.))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('src',type=str, help='')
    parser.add_argument('dst',type=str, help='')
    parser.add_argument('-i','--iteration',type=int,default=3, help='')
    parser.add_argument('--learning_rate',type=float,default=0.01, help='')
    parser.add_argument('--batch_size',type=int,default=1, help='')
    parser.add_argument('-K',type=int,default=50, help='')
    parser.add_argument('-H',type=int,default=100, help='')
    #parser.add_argument('-P',type=int,default=1, help='')
    args=parser.parse_args()


    
    src=args.src
    dst=args.dst

    os.system('mkdir %s -p'%(dst))
    test_dA(src,dst=args.dst,training_epochs=args.iteration,
            learning_rate=args.learning_rate,batch_size=args.batch_size)

########NEW FILE########
__FILENAME__ = pca2
#!/usr/bin/python3
"""
功能：
PCA降维

Author: ZHANG Kaixu
"""
import argparse
import sys
import numpy
import pickle
from scipy.linalg import svd


def conv_list(raw):
    data=[]
    for v in raw :
        data.append(numpy.array(v))
    data=numpy.array(data).T
    return data

def conv_int(raw,maxind=None):
    m=0
    for i,inds in enumerate(raw):
        inds=list(map(int,inds))
        if inds:
            m=max(m,max(inds))
        raw[i]=inds
    m+=1
    #print('向量长度为 %i'%(m),file=sys.stderr)

    if maxind!=None : m=maxind
    data=[]
    for inds in raw :
        v=[0 for i in range(m)]
        for ind in inds : v[ind]=1
        data.append(numpy.array(v))
    data=numpy.array(data).T
    return data



def load_raw(file,with_id=False,oneline=False):
    m=0
    print('读入数据',file=sys.stderr)
    words=[] if with_id else None
    raw=[]
    for line in file :
        if with_id :
            word,*inds=line.split()
            words.append(word)
        else :
            inds=line.split()
        raw.append(inds)
        if oneline : return words,raw
    return words,raw

def dump(words,mat,of,with_id=False):
    print('保存数据',file=sys.stderr)
    if with_id :
        for word,vector in zip(words,mat.T):
            print(word,' '.join(map(str,vector)),file=of)
    else :
        for vector in mat.T:
            print(' '.join(map(str,vector)),file=of)

    pass

def pca(data,whitten=None,epsilon=0.00001,model_file=None):
    s=numpy.mean(data,axis=1) # 求均值
    data=(data.T-s).T # 保证数据均值为0
    print('计算协方差矩阵',file=sys.stderr)
    sigma=numpy.dot(data,data.T)/data.shape[1] # 计算协方差矩阵
    print('SVD分解',file=sys.stderr)
    u,s,v=svd(sigma)
    sl=numpy.sum(s)
    y=0
    for i,x in enumerate(s):
        y+=x
        if y>=sl*0.99 : 
            tr=i+1
            break
    if whitten=='PCA' :
        print('在 %i 个特征值中截取前 %i 个较大的特征用以降维'%(s.shape[0],tr),file=sys.stderr)
        print('计算降维后的向量',file=sys.stderr)
        xdot=numpy.dot(u.T[:tr],data)
        print('对数据进行PCA白化',file=sys.stderr)
        pcawhite=numpy.dot(numpy.diag(1/numpy.sqrt(s[:tr]+epsilon)),xdot)
        return pcawhite
    elif whitten=='ZCA' :
        print('计算PCA但不降维的向量',file=sys.stderr)
        xdot=numpy.dot(u.T,data)
        print('对数据进行PCA白化',file=sys.stderr)
        pcawhite=numpy.dot(numpy.diag(1/numpy.sqrt(s+epsilon)),xdot)
        print('对数据进行ZCA白化',file=sys.stderr)
        zcawhite=numpy.dot(u,pcawhite)
        return zcawhite
    else :
        print('在 %i 个特征值中截取前 %i 个较大的特征用以降维'%(s.shape[0],tr),file=sys.stderr)
        print('计算降维后的向量',file=sys.stderr)
        #xdot=numpy.dot(u.T[:tr],data)
        return [s,u.T]
        #pickle.dumps(u.T)
        #return xdot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--train',type=str, help='')
    parser.add_argument('--result',type=str, help='')
    parser.add_argument('--model',type=str,default='/dev/null', help='')
    parser.add_argument('--vector',type=str,default='list', help='')
    parser.add_argument('--white',type=str,default='', help='')
    parser.add_argument('--with_id',action='store_true', help='')
    parser.add_argument('--epsilon',type=float,default=0.00001, help='')
    parser.add_argument('--dim',type=int,default=0, help='')
    #parser.add_argument('--model',type=str, help='')
    args = parser.parse_args()

    vectors={'int': conv_int, 'list' : conv_list}
    if args.vector not in vectors :
        exit()

    result_file=open(args.result,'w') if args.result else sys.stdout

    if args.train :
        train_file=open(args.train) if args.train else sys.stdin

        ids,raw=load_raw(train_file,with_id=args.with_id)

        data=vectors[args.vector](raw)
        mat=pca(data,whitten=args.white,epsilon=args.epsilon)
        pickle.dump(mat,open(args.model,'wb'))

    else :
        train_file=sys.stdin
        s,ut=pickle.load(open(args.model,'rb'))
        if args.dim : ut=ut[:args.dim]
        #ut=ut[:6000] # 降维！

        for line in sys.stdin :
            if args.with_id :
                word,*inds=line.split()
            else :
                inds=line.split()

            data=vectors[args.vector]([inds],maxind=s.shape[0])
            rst=numpy.dot(ut,(data.T-s).T).T
            print(word,*rst[0])


    #dump(ids,mat,of=result_file,with_id=args.with_id)

    # debug : to check that sigma == I 
    #sigma=numpy.dot(mat,mat.T)/mat.shape[1]
    #print(sigma)

########NEW FILE########
__FILENAME__ = softmax
#!/usr/bin/python2
"""
logistic regression with one hidden layer
"""
import argparse
import cPickle
import gzip
import os
import sys
import time
import json

import numpy

import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams

def shared_array(shape,dtype=float,rng=None):
    if rng :
        value=numpy.asarray(rng.uniform(
                  low=-4 * numpy.sqrt(6. / sum(shape)),
                  high=4 * numpy.sqrt(6. / sum(shape)),
                  size=shape), dtype=dtype)
    else :
        value=numpy.zeros(shape,dtype=dtype)
    return theano.shared(value=value, name=None, borrow=True)

class dA(object):
    """Denoising Auto-Encoder class (dA)
    """

    def __init__(self, numpy_rng, theano_rng=None, xs=[],y=None,
                 n_visibles=[], n_hidden=500, n_y=3,
                 params=None
                 ):
        self.n_visibles = n_visibles
        self.n_hidden = n_hidden
        self.xs = xs
        self.y=y

        if not theano_rng:
            theano_rng = RandomStreams(numpy_rng.randint(2 ** 30))
        self.theano_rng = theano_rng

        self.Ws = [ shared_array((n_visible,n_hidden),rng=numpy_rng)
                for n_visible in self.n_visibles ]

        self.V=shared_array((n_hidden,n_y),rng=numpy_rng)

        self.b_prime = shared_array(n_y)
        self.b =shared_array(n_hidden)

        if params == None : # train
            self.params = self.Ws+[self.V,self.b,self.b_prime]#+[self.V,self.b,self.b_prime]
        else : # predict
            self.b_prime=params[-1]
            self.b=params[-2]
            self.V=params[-3]
            self.Ws=params[:-3]


    def get_corrupted_input(self, input, corruption_level):
        return  self.theano_rng.binomial(size=input.shape, n=1,
                                         p=1 - corruption_level,
                                         dtype=theano.config.floatX) * input

    def get_hidden_values(self, input):
        x=sum(T.dot(a,b) for a,b in zip(input,self.Ws))+self.b
        return T.nnet.sigmoid(x)
        #return T.tanh(x)

    def get_reconstructed_input(self, hidden):
        #return T.nnet.sigmoid(T.dot(hidden,self.V)+self.b_prime)
        return T.nnet.softmax(T.dot(hidden,self.V)+self.b_prime)

    def get_cost_updates(self, corruption_level, learning_rate,  
            ):
        """ This function computes the cost and the updates for one trainng
        step of the dA """


        tilde_xs = [self.get_corrupted_input(x, corruption_level) for x in self.xs]
        y = self.get_hidden_values(tilde_xs)
        zs = self.get_reconstructed_input(y)
        #L=((zs-self.y)**2)/2 

        sw=sum(T.mean(w**2) for w in self.Ws)/2/len(self.Ws)

        #cost = T.mean(L)# + sw
        cost=-T.mean(T.log(zs)[T.arange(self.y.shape[0]), self.y])
        cost+=sw

        gparams = T.grad(cost, self.params)

        updates = []
        for param, gparam in zip(self.params, gparams):
            updates.append((param, param - learning_rate * gparam))

        return (cost, updates)
        
        #lost for the output
        #L = sum(T.sum((x-z)**2 )/2 for x,z in zip(self.xs,zs))


        #cost = T.mean(L) + T.sum(sL) * beta + T.sum(self.W*self.W)/100
        #cost = T.mean(L) + T.sum(sL) * beta + 1.0/2 * T.sum((self.W)**2) /100.0


        # generate the list of updates


class Inds_Loader():
    @staticmethod
    def load_training_data(filename,n_visibles):
        labels=[]
        v=[[] for i in range(len(n_visibles))]

        for line in open(filename):
            data=json.loads(line)
            label=data[0]
            vectors=data[1:]

            vectors=list(map(lambda x:numpy.array(x,dtype=float),vectors))
            labels.append([label])
            for i in range(len(n_visibles)) :
                v[i].append(vectors[i])
        labels=numpy.array(labels,dtype=int)
        train_set_x=[labels,v]
        print('ok')
        return train_set_x

    @staticmethod
    def load_line(line,n_visibles):
        labels=[]
        v=[[] for i in range(len(n_visibles))]
        data=json.loads(line)
        label=data[0]
        vectors=data[1:]
        vectors=list(map(lambda x:numpy.array(x,dtype=float),vectors))
        labels.append([label])
        for i in range(len(n_visibles)) :
            v[i].append(vectors[i])
        train_set_x=[labels,v]
        return train_set_x


def get_vars(batch_size,n_visibles):
    shared_xs = [ shared_array((n_visibles[k],batch_size))
            for k in range(len(n_visibles)) ]
    shared_y=shared_array(batch_size,dtype=int)
    return shared_xs,shared_y


def test_dA(learning_rate=0.01, training_epochs=15,
            dataset="",modelfile="",
            batch_size=20, output_folder='dA_plots',
            n_visible=1346,n_hidden=100,
            noise=0.3,
            n_visibles=None,
            loader=None):

    train_set_x=loader.load_training_data(dataset,n_visibles)

    print >>sys.stderr, "number of training example", len(train_set_x[0])
    print >>sys.stderr, "batch size", batch_size

    print >>sys.stderr, "number of visible nodes", n_visible
    print >>sys.stderr, "number of hidden nodes", n_hidden

    print >>sys.stderr, "corruption_level",noise

    print >>sys.stderr, "learning rate", learning_rate
    # compute number of minibatches for training, validation and testing

    
    n_train_batches = len(train_set_x[0]) / batch_size
    #print(n_train_batches)

    shared_xs,shared_y=get_vars(batch_size,n_visibles)

    #####################################

    rng = numpy.random.RandomState(123)

    da = dA(numpy_rng=rng, xs=shared_xs,y=shared_y,
            n_visibles=n_visibles, n_hidden=n_hidden)

    cost, updates = da.get_cost_updates(corruption_level=noise,
                                        learning_rate=learning_rate,)


    train_da = theano.function([], cost, updates=updates,
         on_unused_input='ignore')

    start_time = time.clock()

    # TRAINING #
    for epoch in xrange(training_epochs):
        # go through trainng set
        c = []
        for batch_index in xrange(n_train_batches):
            v=numpy.array(train_set_x[0][batch_index * batch_size : (1+batch_index)*batch_size],dtype=int)
            v=v.T[0]
            shared_y.set_value(v)
            for i in range(len(n_visibles)):
                v=numpy.array(train_set_x[1][i][batch_index * batch_size : (1+batch_index)*batch_size])
                shared_xs[i].set_value(v)

            ret=(train_da())
            c.append(ret)
        print 'Training epoch %d, cost ' % epoch, numpy.mean(c)

    end_time = time.clock()

    training_time = (end_time - start_time)

    print >> sys.stderr, (' ran for %.2fm' % (training_time / 60.))

    modelfile=gzip.open(modelfile,"wb")
    cPickle.dump([n_hidden],modelfile)
    cPickle.dump(da.Ws+[da.V,da.b,da.b_prime],modelfile)
    modelfile.close()

    tmp=gzip.open('2to3.gz','wb')
    for x in da.Ws: # Ws
        cPickle.dump(x.get_value().tolist(),tmp)
    cPickle.dump(da.V.get_value().tolist(),tmp)
    cPickle.dump(da.b.get_value().tolist(),tmp)
    cPickle.dump(da.b_prime.get_value().tolist(),tmp)

def predict(modelfile,threshold=0.5,loader=None,n_visibles=[]):
    modelfile=gzip.open(modelfile)
    n_hidden,=cPickle.load(modelfile)
    paras=cPickle.load(modelfile)
    modelfile.close()


    # allocate symbolic variables for the data
    shared_xs,shared_y=get_vars(1,n_visibles)

    #####################################

    rng = numpy.random.RandomState(123)

    da = dA(numpy_rng=rng, xs=shared_xs,y=shared_y,
            n_visibles=n_visibles, n_hidden=n_hidden,params=paras)



    py = da.get_reconstructed_input(da.get_hidden_values(da.xs))
    #py = da.get_hidden_values(da.xs)
    #py=da.xs[0]

    predict_da = theano.function([], py,
            on_unused_input='ignore')

    t,cor=0,0
    for line in sys.stdin :
        label,v=loader.load_line(line,n_visibles)
        label=label[0][0]
        
        for i in range(len(n_visibles)):
            shared_xs[i].set_value(v[i])
            #print(shared_xs[i].get_value())
        res=predict_da()[0]
        res=max((v,i) for i,v in enumerate(res))[1]
        c=1 if (label==res) else 0
        t+=1
        cor+=c
    print(t,cor,1.0*cor/t)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model',  type=str)
    
    parser.add_argument('--train',  type=str)
    parser.add_argument('--hidden',  type=int,default=100)
    parser.add_argument('--batch_size',  type=int,default=20)
    parser.add_argument('--iteration',  type=int,default=15)
    parser.add_argument('--noise',  type=float,default=0)
    parser.add_argument('--learning_rate',  type=float,default=0.2)
    parser.add_argument('--predict',  action="store_true")
    parser.add_argument('--threshold',  type=float,default=0.5)
    parser.add_argument('--vector',  type=str,default='inds')
    

    args = parser.parse_args()

    #n_visibles=[20,20,20,50,50,50,50]
    n_visibles=[50,10,50,10,50,10,50,10,50,10]

    loader_map={'inds': Inds_Loader,
            }
    loader=loader_map.get(args.vector,None)
    if loader==None : exit()
    

    if args.train :
        test_dA(dataset=args.train,n_hidden=args.hidden,
                batch_size=args.batch_size,modelfile=args.model,
                noise=args.noise,
                training_epochs=args.iteration,
                learning_rate=args.learning_rate,
                n_visibles=n_visibles,
                loader=loader,
                )
    if args.predict :
        predict(modelfile=args.model,threshold=args.threshold,loader=loader,
                n_visibles=n_visibles,
                )


########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# minitools documentation build configuration file, created by
# sphinx-quickstart on Sat May  4 13:31:44 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.mathjax']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'minitools'
copyright = '2013, ZHANG Kaixu'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1'
# The full version, including alpha/beta/rc tags.
release = '1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'
html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'minitoolsdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'minitools.tex', 'minitools Documentation',
   'ZHANG Kaixu', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'minitools', 'minitools Documentation',
     ['ZHANG Kaixu'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'minitools', 'minitools Documentation',
   'ZHANG Kaixu', 'minitools', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = k-means
#!/usr/bin/python3
"""
k-means

* k-means聚类
* 使用了numpy的向量，还比较快
* 目前还不能保存模型，只能给什么数据聚什么

author : ZHANG Kaixu
"""
import argparse
import sys
import random
import numpy as np

def cal_means(clus,M):
    means=[]
    for clu in clus:
        if not clu :
            means.append([random.random()*2-1 for i in range(M)])
            continue
        s=np.mean(clu,axis=0)
        means.append(s)
    return means

def assign(means,data):
    clus=[[] for i in range(len(means))]
    a=[]
    for ex in data:
        d=[np.sum((m-ex)**2) for m in means]
        ass=min(enumerate(d),key=lambda x:x[1])[0]
        a.append(ass)
        clus[ass].append(ex)
    return clus,a

def kmeans(datafile,resultfile,K,nbest,
        T):
    data=[]
    words=[]
    clu=[[]for i in range(K)]
    M=None
    print('load data',file=sys.stderr)
    for line in datafile :
        word,*x=line.split()
        x=list(map(float,x))
        M=len(x)
        data.append(np.array(x))
        words.append(word)
        clu[random.randrange(0,K-1)].append(x)

    for i in range(T):
        print('iteration',i+1,file=sys.stderr)
        means=cal_means(clu,M)
        clu,a=assign(means,data)


    for word,ex in zip(words,data):
        d=[np.sqrt(np.sum((m-ex)**2)) for m in means]
        dists=sorted(enumerate(d),key=lambda x:x[1])
        if type(nbest)==int :
            print(word,*[ind for ind,_ in dists[:min(len(dists),nbest)]],file=resultfile)
        elif nbest=='triangle' :
            mu=sum(d for _,d in dists)/len(dists)
            print(word,' '.join(str(ind)+':'+str(mu-d) for ind,d in dists if mu>d),file=resultfile)
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--iteration',type=int,default=10, help='')
    parser.add_argument('--train',type=str, default='-', help='')
    parser.add_argument('--test',type=str, help='')
    parser.add_argument('--predict',type=str, help='')
    parser.add_argument('--k',type=int,default=50, help='')
    parser.add_argument('--result',type=str, default='-', help='')
    parser.add_argument('--nbest',type=str, default='1', help='')
    parser.add_argument('--model',type=str, help='')
    args = parser.parse_args()

    datafile=open(args.train) if args.train!='-' else sys.stdin
    resultfile=open(args.result) if args.result!='-' else sys.stdout

    nbest=int(args.nbest) if all(x in set('1234567890') for x in args.nbest) else args.nbest

    kmeans(K=args.K,datafile=datafile,T=args.iteration,resultfile=resultfile,
            nbest=nbest
            )

########NEW FILE########
__FILENAME__ = lda
#!/usr/bin/python3
import random
import sys
import argparse
import collections 
"""
"""

class GibbsLDA :
    def __init__(self,K,alpha,beta):
        self.alpha=alpha
        self.beta=beta
        self.K=K
        self._init_list=lambda x,y : [y for i in range(x)]
        self._init_array=lambda x,y,z : [[z for j in range(y)] for i in range(x)]

    def set_vocabulary(self,vocabulary):
        self.vocabulary=vocabulary
        self.V=len(self.vocabulary)
        self.word_list=self._init_list(self.V,None)
        for word,word_id in self.vocabulary.items() : self.word_list[word_id]=word

        self.topic_word=self._init_array(self.K,self.V,0)
        self.words_of_topic=self._init_list(self.K,0)


    def one_iteration(self):
        for doc_id in range(len(self.docs)):
            doc=self.docs[doc_id]
            for word_id in range(len(doc)):
                word=doc[word_id]
                #remove one
                topic=self.assignments[doc_id][word_id]
                self.doc_topic[doc_id][topic]-=1
                self.topic_word[topic][word]-=1
                self.words_of_topic[topic]-=1

                #sample
                ps=[(self.doc_topic[doc_id][topic]+self.alpha)*
                            (self.topic_word[topic][word]+self.beta)/
                            (self.words_of_topic[topic]+len(self.vocabulary)*self.beta)
                            for topic in range(self.K)]
                x=sum(ps)*random.random()
                topic=0
                acc=0
                for p in ps :
                    acc+=p
                    if acc > x : break
                    topic+=1

                #add one
                self.assignments[doc_id][word_id]=topic
                self.doc_topic[doc_id][topic]+=1
                self.topic_word[topic][word]+=1
                self.words_of_topic[topic]+=1
        
    def loop(self,docs,burnin,iteration):
        #init docs
        self.docs=docs
        self.M=len(self.docs)
        self.assignments=[ [0 for i in range(len(doc))] for doc in self.docs]
        self.doc_topic=self._init_array(self.M,self.K,0)
        for doc_id in range(len(self.docs)):
            doc=self.docs[doc_id]
            for word_id in range(len(doc)):
                word=doc[word_id]
                topic=random.randrange(0,self.K)
                self.doc_topic[doc_id][topic]+=1
                self.topic_word[topic][word]+=1
                self.words_of_topic[topic]+=1
                self.assignments[doc_id][word_id]=topic

        #init phi and theta
        self.phi=self._init_array(self.K,self.V,0)
        self.theta=self._init_array(self.M,self.K,0)

        #sampling loop
        for it in range(burnin+iteration):
            print('第 %s 轮迭代开始...'%(it+1),file=sys.stderr)
            self.one_iteration()
            
            #print top-10 words for each topic
            cats=[]
            for k in range(self.K):
                words=(sorted([(self.topic_word[k][w],w) 
                    for w in range(len(self.vocabulary))],reverse=True)[:10])
                cats.append((self.words_of_topic[k],
                        ' '.join([self.word_list[w] for f,w in words])))
            cats=sorted(cats,reverse=True)
            for n,s in cats:
                print(n,s,file=sys.stderr)

            if it>=burnin :
                #theta
                for doc_id in range(len(self.docs)):
                    for k in range(self.K) :
                        self.theta[doc_id][k]+=self.doc_topic[doc_id][k]
                #phi
                for k in range(self.K) :
                    for i in range(len(self.vocabulary)):
                        self.phi[k][i]+=self.topic_word[k][i]

    def save(self,modelfile):
        ofile=open(modelfile,'w')
        print(self.alpha,self.beta,file=ofile)#alpha and beta
        for k in range(self.K) :
            words=(sorted([(self.topic_word[k][w],w) 
                for w in range(len(self.vocabulary))],reverse=True))
            for v,w in words:
                if not v : continue
                print(k,self.word_list[w],v,file=ofile)

    def load(self,modelfile):
        ofile=open(modelfile)
        self.alpha,self.beta=ofile.readline().split()
        self.alpha=float(self.alpha)
        self.beta=float(self.beta)
        self.K=-1
        self.vocabulary={}
        self.topic_word=[]
        for line in ofile :
            topic,word,freq=line.split()
            topic=int(topic)
            if topic > self.K : 
                self.topic_word.append({})
                self.K=topic
            if word not in self.vocabulary : 
                self.vocabulary[word]=len(self.vocabulary)
            self.topic_word[topic][self.vocabulary[word]]=float(freq)
        self.V=len(self.vocabulary)
        self.word_list=self._init_list(self.V,None)
        for word,word_id in self.vocabulary.items() : self.word_list[word_id]=word

        for k in range(self.K):
            l=self._init_list(self.V,0)
            for w,f in self.topic_word[k].items() : l[w]=f
            self.topic_word[k]=l
        self.words_of_topic=[sum(self.topic_word[k]) for k in range(self.K)]

    def save_assignment(self,filename):
        ofile=open(filename,'w')
        for doc_id in range(len(self.docs)):
            doc=self.docs[doc_id]
            assignment=[]
            for word_id in range(len(doc)):
                word=doc[word_id]
                #MLE
                ps=[(self.doc_topic[doc_id][topic]+self.alpha)*
                            (self.topic_word[topic][word]+self.beta)/
                            (self.words_of_topic[topic]+len(self.vocabulary)*self.beta)
                            for topic in range(self.K)]
                ps=[(p,i)for i,p in enumerate(ps)]
                topic=max(ps)[1]
                assignment.append(self.word_list[word]+'/'+str(topic))
            theta=' '.join([str(k)+':'+str(self.theta[doc_id][k]) for k in range(self.K)])
            print(theta,' '.join(assignment),file=ofile)
        for doc_id in range(len(self.docs)):
            doc=self.docs[doc_id]
            assignment=[]
            for word_id in range(len(doc)):
                word=doc[word_id]
                topic=self.assignments[doc_id][word_id]
                self.topic_word[topic][word]-=1
                self.words_of_topic[topic]-=1

def load(docfile,n_stopword,n_words):
    #load file
    docs=[line.split() for line in open(docfile)]

    #filter stopwords and tail words
    counter=collections.Counter()
    for doc in docs : counter.update(doc)
    words=[w for w,_ in counter.most_common(n_stopword+n_words)]
    words=set(words[n_stopword:])

    #index words
    vocabulary={}
    for i,doc in enumerate(docs):
        for word in doc:
            if word not in words : continue
            if word not in vocabulary : vocabulary[word]=len(vocabulary)
        docs[i]=[vocabulary[word] for word in doc if word in vocabulary]
    return docs,vocabulary

def load_with_v(docfile,vocabulary):
    docs=[line.split() for line in open(docfile)]
    for i,doc in enumerate(docs):
        docs[i]=[vocabulary[word] for word in doc if word in vocabulary]
    return docs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--train',type=str, help='用于训练的文本集，每行代表一个文档，文档中的词用空格隔开')
    parser.add_argument('--predict',type=str, help='')
    parser.add_argument('--model',type=str, help='')
    parser.add_argument('--result',type=str, help='')
    parser.add_argument('--burnin',type=int,default=30, help='')
    parser.add_argument('--iteration',type=int,default=5, help='')
    parser.add_argument('--n_stops',type=int,default=100, help='设定停用词个数')
    parser.add_argument('--n_words',type=int,default=1000, help='设定使用的词的个数')
    parser.add_argument('-K',type=int,default=20, help='主题个数')
    parser.add_argument('--alpha',type=int,default=1, help='')
    parser.add_argument('--beta',type=int,default=1, help='')

    args = parser.parse_args()

    if args.train :
        docs,vocabulary=load(args.train,args.n_stops,args.n_words)
        model=GibbsLDA(args.K,args.alpha,args.beta)
        model.set_vocabulary(vocabulary)
        model.loop(docs,args.burnin,args.iteration)
        if args.model : model.save(args.model)
        if args.result : model.save_assignment(args.result)

    if args.predict :
        model=GibbsLDA(args.K,0,0)
        model.load(args.model)
        docs=load_with_v(args.predict,model.vocabulary)
        model.loop(docs,args.burnin,args.iteration)
        if args.result : model.save_assignment(args.result)

########NEW FILE########
__FILENAME__ = bhc
#!/usr/bin/python3
import math

def bhc_ber(data,lalpha=-1):
    """
    Bayesian hierarchical clustering
        for features with Ber distributions

    an example is a list of 0, 1 values
    """
    D={}
    DD={}

    def lBeta(a,b):
        return math.lgamma(a)+math.lgamma(b)-math.lgamma(a+b)

    def cal_lpH(ex):
        lp=0
        n=ex['n']
        for ni in ex['heads'] :
            #print(ni+a,n-ni+b,lBeta(ni+a,n-ni+b))
            lp+=lBeta(ni+a,n-ni+b)
        #print(n,sum(ex['heads']))
        return lp
    def laddl(a,b):
        if a < b : a,b=b,a
        return a+math.log(1+math.exp(b-a))

    def lminusl(a,b):
        if a==b : return 0
        if a < b : a,b=b,a
        return a+math.log(1-math.exp(b-a))


    def cal_merge(ex1,ex2):
        ex={}
        ex['n']=ex1['n']+ex2['n']
        ex['heads']=[x+y for x,y in zip(ex1['heads'],ex2['heads'])]
        lalphagamma=(lalpha)+math.lgamma(ex['n'])
        ex['ld']=laddl(lalphagamma,left['ld']+right['ld'])
        ex['lpi']=lalphagamma-ex['ld']
        ex['lpH']=cal_lpH(ex)
        ex['lp']=laddl(ex['lpi']+ex['lpH'],lminusl(0,ex['lpi'])+ex1['lp']+ex2['lp'])
        #print('t1',ex['lpi']+ex['lpH'])
        #print('t2',lminusl(0,ex['lpi'])+ex1['lp']+ex2['lp'])
        #print(lminusl(0,ex['lpi']),ex1['lp'],ex2['lp'])

        #print(math.exp(ex['lpi']),ex['lpH'],ex['lp'])
        return ex

    index=0


    a=0.75
    b=0.75
    for example in data :
        r={'n':1,'heads':example,'ld':(lalpha),'lpi':0,'tree':index}
        n=r['n']
        lp=cal_lpH(r)
        r['lpH']=lp
        r['lp']=lp
        D[index]=r
        index+=1

    for i in range(len(D)):
        print(i)
        for j in range(i+1,len(D)):
            left=D[i]
            right=D[j]
            ex=cal_merge(left,right)
            DD[(i,j)]=ex

    while len(D)>1 :
        print(len(D))
        k,v=max(([k,v] for k,v in DD.items()),key=lambda x:x[1]['lpH']-x[1]['lp'])
        #print('lr',v['lpH']-v['lp'])
        inda,indb=k
        v['tree']=[D[inda]['tree'],D[indb]['tree']]
        D={k:v for k,v in D.items() if k!=inda and k!=indb}
        k=index
        D[k]=v
        index+=1
        DD={k:v for k,v in DD.items() if inda not in k and indb not in k}
        for dk,dv in D.items():
            if dk==k : continue
            DD[(dk,k)]=cal_merge(dv,v)
    return (list(D.values())[0]['tree'])
            

########NEW FILE########
__FILENAME__ = gmm
#!/usr/bin/python3
"""
Gaussian mixture model
* require numpy
"""
import numpy

class GMM :
    def __init__(self,K=10):
        self.K=K

    def learn(self,X,T=10):
        


if __name__ == '__main__':
    print('haha')



########NEW FILE########
__FILENAME__ = pca
#!/usr/bin/python3
"""
功能：
PCA降维
PCA白化
ZCA白化

多种数据格式的读入读出

TODO：保存、读取模型

Author: ZHANG Kaixu
"""
import argparse
import sys
import numpy
from scipy.linalg import svd


def conv_list(raw):
    data=[]
    for v in raw :
        data.append(numpy.array(v))
    data=numpy.array(data).T
    return data

def conv_int(raw):
    m=0
    for i,inds in enumerate(raw):
        inds=list(map(int,inds))
        if inds:
            m=max(m,max(inds))
        raw[i]=inds
    m+=1
    print('向量长度为 %i'%(m),file=sys.stderr)

    data=[]
    for inds in raw :
        v=[0 for i in range(m)]
        for ind in inds : v[ind]=1
        data.append(numpy.array(v))
    data=numpy.array(data).T
    return data



def load_raw(file,with_id=False):
    m=0
    print('读入数据',file=sys.stderr)
    words=[] if with_id else None
    raw=[]
    for line in file :
        if with_id :
            word,*inds=line.split()
            words.append(word)
        else :
            inds=line.split()
        raw.append(inds)
    return words,raw

def dump(words,mat,of,with_id=False):
    print('保存数据',file=sys.stderr)
    if with_id :
        for word,vector in zip(words,mat.T):
            print(word,' '.join(map(str,vector)),file=of)
    else :
        for vector in mat.T:
            print(' '.join(map(str,vector)),file=of)

    pass

def pca(data,whitten=None,epsilon=0.00001):
    s=numpy.mean(data,axis=1) # 求均值
    data=(data.T-s).T # 保证数据均值为0
    print('计算协方差矩阵',file=sys.stderr)
    sigma=numpy.dot(data,data.T)/data.shape[1] # 计算协方差矩阵
    print('SVD分解',file=sys.stderr)
    u,s,v=svd(sigma)
    sl=numpy.sum(s)
    y=0
    for i,x in enumerate(s):
        y+=x
        if y>=sl*0.99 : 
            tr=i+1
            break
    if whitten=='PCA' :
        print('在 %i 个特征值中截取前 %i 个较大的特征用以降维'%(s.shape[0],tr),file=sys.stderr)
        print('计算降维后的向量',file=sys.stderr)
        xdot=numpy.dot(u.T[:tr],data)
        print('对数据进行PCA白化',file=sys.stderr)
        pcawhite=numpy.dot(numpy.diag(1/numpy.sqrt(s[:tr]+epsilon)),xdot)
        return pcawhite
    elif whitten=='ZCA' :
        print('计算PCA但不降维的向量',file=sys.stderr)
        xdot=numpy.dot(u.T,data)
        print('对数据进行PCA白化',file=sys.stderr)
        pcawhite=numpy.dot(numpy.diag(1/numpy.sqrt(s+epsilon)),xdot)
        print('对数据进行ZCA白化',file=sys.stderr)
        zcawhite=numpy.dot(u,pcawhite)
        return zcawhite
    else :
        print('在 %i 个特征值中截取前 %i 个较大的特征用以降维'%(s.shape[0],tr),file=sys.stderr)
        print('计算降维后的向量',file=sys.stderr)
        xdot=numpy.dot(u.T[:tr],data)
        return xdot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--iteration',type=int,default=5, help='')
    parser.add_argument('--train',type=str, help='')
    parser.add_argument('--result',type=str, help='')
    parser.add_argument('--vector',type=str,default='list', help='')
    parser.add_argument('--white',type=str,default='', help='')
    parser.add_argument('--with_id',action='store_true', help='')
    parser.add_argument('--epsilon',type=float,default=0.00001, help='')
    #parser.add_argument('--model',type=str, help='')
    args = parser.parse_args()

    vectors={'int': conv_int, 'list' : conv_list}
    if args.vector not in vectors :
        exit()

    result_file=open(args.result,'w') if args.result else sys.stdout
    train_file=open(args.train) if args.train else sys.stdin

    ids,raw=load_raw(train_file,with_id=args.with_id)

    data=vectors[args.vector](raw)
    mat=pca(data,whitten=args.white,epsilon=args.epsilon)
    dump(ids,mat,of=result_file,with_id=args.with_id)

    # debug : to check that sigma == I 
    #sigma=numpy.dot(mat,mat.T)/mat.shape[1]
    #print(sigma)

########NEW FILE########
__FILENAME__ = perceptron
#!/usr/bin/python3
import argparse
import sys
import json
import time
import random


def make_color(s,color=36):
    return '\033['+str(color)+';01m%s\033[1;m'%str(s) #blue

class Perceptron(dict):
    def __init__(self):
        self._cats=set()
        #only used by training
        self._step=0
        self._acc=dict()
    def predict(self,features):
        score,y=max((sum(self.get(c+'~'+f,0)*v for f,v in features.items()),c)
                for c in self._cats)
        return y
    def _update(self,key,delta):
        if key not in self : self[key]=0
        self[key]+=delta
        if key not in self._acc : self._acc[key]=0
        self._acc[key]+=self._step*delta
    def learn(self,cat,features,is_burnin=False):#core algorithm of the perceptron
        self._cats.add(cat)
        y=self.predict(features)#predict a label
        if y != cat : # if it is not right, update weights
            for f,v in features.items():
                self._update(cat+'~'+f,v)
                self._update(y+'~'+f,-v)
        if not is_burnin : self._step+=1
        return y==cat
    def average(self):
        self._backup=dict(self)
        for k,v in self._acc.items():
            self[k]=self[k]-self._acc[k]/self._step
    def unaverage(self):
        for k,v in self._backup.items():
            self[k]=v
        del self._backup
    def save(self,file):
        file=open(file,'w')
        print(json.dumps(list(self._cats)),file=file)#categories
        json.dump(dict(self),file,ensure_ascii=False,indent=1)#weights
    def load(self,file):
        file=open(file)
        self._cats=set(json.loads(file.readline()))#categories
        self.update(json.load(file))#weights

class Record :
    def __init__(self):
        self.reset()
    def reset(self):
        self.total=0
        self.cor=0
        self.start_time=time.time()
    def __call__(self,a,b=True):
        self.total+=1
        if a==b : self.cor+=1
    def report(self,stream=sys.stderr):
        if self.total==0 : return {}
        results={
                'total':self.total,
                'speed':self.total/(time.time()-self.start_time),
                'correct':self.cor,
                'accuracy':self.cor/self.total,
                }
        if stream :
            print(('样本数:%i (%.0f/秒) 正确数:%i ('+make_color('%.2f'))
                    %(self.total,self.total/(time.time()-self.start_time),
                        self.cor,self.cor/self.total*100)+'%)'
                    ,file=sys.stderr)
        return results

def parse_example(example):
    cat,*features=example.strip().split()
    features=[x.rpartition(':') for x in features]
    features={k : float(v)for k,_,v in features}
    return cat,features

class Miniper :
    def __init__(self):
        self._perceptron=Perceptron()
        self._record=Record()
    def load(self,filename):
        self._perceptron.load(filename)
    def save(self,filename):
        self._perceptron.save(filename)
    def learn(self,cat,features,**args):
        self._record(self._perceptron.learn(cat,features,**args))
    def test(self,cat,features):
        self._record(cat,self._perceptron.predict(features))
    def predict(self,features):
        return self._perceptron.predict(features)
    def report(self,stream=sys.stderr):
        result=self._record.report(stream=stream)
        self._record.reset()
        return result
    def average(self):
        self._perceptron.average()
    def unaverage(self):
        self._perceptron.unaverage()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--burnin',type=int,default=0, help='')
    parser.add_argument('--iteration',type=int,default=5, help='')
    parser.add_argument('--train',type=str, help='')
    parser.add_argument('--test',type=str, help='')
    parser.add_argument('--predict',type=str, help='')
    parser.add_argument('--result',type=str, help='')
    parser.add_argument('--model',type=str, help='')
    parser.add_argument('--CV',type=int, help='')
    args = parser.parse_args()

    if args.CV :#
        if not args.train : print('has CV but no train_file',file=sys.stderr)
        examples=[parse_example(line) for line in open(args.train)]
        random.shuffle(examples)
        folds=[[]for i in range(args.CV)]
        for i,e in enumerate(examples):
            folds[i%args.CV].append(e)

        accs=[]
        
        for i in range(args.CV) :
            for t in range(args.iteration):
                per=Miniper()
                for j in range(args.CV) :
                    if j==i : continue
                    for e in folds[j] : per.learn(*e)
                per.report(None)
            per.average()
            for e in folds[i] : per.test(*e)
            accs.append(per.report(None)['accuracy'])
        print(sum(accs)/len(accs))
        exit()

    if args.train:
        per=Miniper()
        for i in range(args.iteration+args.burnin):
            for l in open(args.train):
                per.learn(*parse_example(l.strip()),is_burnin=(i<args.burnin))
            per.report()
        per.average()
        per.save(args.model)

    if args.test :
        per=Miniper()
        per.load(args.model)
        for l in open(args.test):
            per.test(*parse_example(l.strip()))
        per.report()

    if args.model and (not args.train and not args.test and not args.CV) :
        per=Miniper()
        per.load(args.model)
        instream=open(args.predict) if args.predict else sys.stdin
        outstream=open(args.result,'w') if args.result else sys.stdout
        for l in instream:
            label=per.predict(*parse_example(l.strip())[1:])
            print(label,file=outstream)


########NEW FILE########
__FILENAME__ = apcluster
#!/usr/bin/python3
"""

"""
import argparse
import sys
import collections

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',type=str, help='')
    parser.add_argument('--output',type=str, help='')
    parser.add_argument('--index',type=str, help='')
    parser.add_argument('--put',action='store_true',help='')
    parser.add_argument('--get',action='store_true',help='')

    args = parser.parse_args()

    instream=open(args.input) if args.input else sys.stdin
    outstream=open(args.output,'w') if args.output else sys.stdout

    if args.put :
        indexer={}
        for line in instream:
            a,b,s=line.split()
            if a not in indexer : indexer[a]=len(indexer)
            if b not in indexer : indexer[b]=len(indexer)
            print(indexer[a]+1,indexer[b]+1,s)
        outf=open(args.index,'w')
        for k,v in sorted((indexer.items()),key=lambda x : x[1]):
            print(k,file=outf)
        exit()
    if args.get :
        clus={}
        for it,x in zip(open(args.index),enumerate(instream)):
            ind,c=x
            ind=ind+1
            it=it.strip()
            c=int(c)
            if c==0 : c=ind
            if c not in clus : clus[c]=[[],[]]
            clus[c][0 if c==ind else 1].append(it)
        for v in sorted([sum(v,[])for v in clus.values()],key=lambda x : len(x),reverse=True):
            print(*v,file=outstream)



########NEW FILE########
__FILENAME__ = count
#!/usr/bin/python3
"""
Zhang, Kaixu: kareyzhang@gmail.com
用于数数
"""
import argparse
import sys
import collections

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',type=str, help='')
    parser.add_argument('--output',type=str, help='')
    parser.add_argument('--with_weight',action="store_true", help='')
    args = parser.parse_args()

    instream=open(args.input) if args.input else sys.stdin
    outstream=open(args.output,'w') if args.output else sys.stdout

    counter=collections.Counter()
    for line in instream :
        line=line.strip()
        if args.with_weight :
            k,_,w=line.rpartition(' ')
            counter.update({k : float(w)})
        else :
            counter.update({line : 1})

    for k,v in counter.most_common():
        print(k,v,file=outstream)


########NEW FILE########
__FILENAME__ = fold
#!/usr/bin/python3
"""
用于交叉验证中输出相应行的子集
大部分情况下，用 awk 命令可以代替
"""
import argparse
import sys
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',type=str, help='')
    parser.add_argument('--output',type=str, help='')
    parser.add_argument('--folds',type=int,default=10, help='')
    parser.add_argument('--ind',type=int,default=0, help='')
    parser.add_argument('--include',type=int,nargs='*', help='')
    parser.add_argument('--exclude',type=int,nargs='*', help='')
    parser.add_argument('--block_size',type=int,default=1, help='')

    args = parser.parse_args()

    instream=open(args.input) if args.input else sys.stdin
    outstream=open(args.output,'w') if args.output else sys.stdout

    inds=set()
    if args.include : 
        inds.update(args.include)
    if args.exclude :
        inds=set(ind for ind in range(args.folds))
        inds-=set(args.exclude)

    block_size=args.block_size
    N=args.folds
    ind=args.ind
    for i,line in enumerate(instream):
        if ((i//block_size)%N) in inds :
            print(line,end='',file=outstream)

########NEW FILE########
__FILENAME__ = pipeline
#!/usr/bin/python3
import sys
import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',type=str, help='')
    parser.add_argument('--output',type=str, help='')
    parser.add_argument('--before',type=str,nargs='*', help='')
    parser.add_argument(dest='mid',type=str,nargs='*', help='')
    parser.add_argument('--after',type=str,nargs='*', help='')
    parser.add_argument('--if',dest='iiff',type=str, help='')
    parser.add_argument('--with_weight',action="store_true", help='')
    args = parser.parse_args()

    instream=open(args.input) if args.input else sys.stdin
    outstream=open(args.output,'w') if args.output else sys.stdout

    if args.before :
        for c in args.before :
            exec(c)
    for line in sys.stdin :
        line=line.strip()
        if args.iiff:
            if eval(args.iiff) :
                print(line)
        if args.mid :
            for c in args.mid :
                exec(c)
    if args.after :
        for c in args.after :
            exec(c)

########NEW FILE########
