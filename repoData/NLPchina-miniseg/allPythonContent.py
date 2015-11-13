__FILENAME__ = prob_start
{'B': -0.8877383940489068, 'S': -0.5303237243812831}

########NEW FILE########
__FILENAME__ = prob_trans
{'B': {'E': -0.16518441189682853, 'M': -1.8821483335951348},
 'E': {'B': -0.8064261824909028, 'S': -0.591404555286857},
 'M': {'E': -0.365305528574006, 'M': -1.184119806934594},
 'S': {'B': -0.8973769931843144, 'S': -0.5236364912754701}}

########NEW FILE########
__FILENAME__ = test
#encoding=utf-8
import sys
import miniseg


def cuttest(test_sent):
    result = miniseg.cut(test_sent)
    print " / ".join(result)


if __name__ == "__main__":
    cuttest("这是一个伸手不见五指的黑夜。我叫孙悟空，我爱北京，我爱Python和C++。")
    cuttest("我不喜欢日本和服。")
    cuttest("雷猴回归人间。")
    cuttest("工信处女干事每月经过下属科室都要亲口交代24口交换机等技术性器件的安装工作")
    cuttest("我需要廉租房")
    cuttest("永和服装饰品有限公司")
    cuttest("我爱北京天安门")
    cuttest("abc")
    cuttest("隐马尔可夫")
    cuttest("雷猴是个好网站")
    cuttest("“Microsoft”一词由“MICROcomputer（微型计算机）”和“SOFTware（软件）”两部分组成")
    cuttest("草泥马和欺实马是今年的流行词汇")
    cuttest("伊藤洋华堂总府店")
    cuttest("中国科学院计算技术研究所")
    cuttest("罗密欧与朱丽叶")
    cuttest("我购买了道具和服装")
    cuttest("PS: 我觉得开源有一个好处，就是能够敦促自己不断改进，避免敞帚自珍")
    cuttest("湖北省石首市")
    cuttest("湖北省十堰市")
    cuttest("总经理完成了这件事情")
    cuttest("电脑修好了")
    cuttest("做好了这件事情就一了百了了")
    cuttest("人们审美的观点是不同的")
    cuttest("我们买了一个美的空调")
    cuttest("线程初始化时我们要注意")
    cuttest("一个分子是由好多原子组织成的")
    cuttest("祝你马到功成")
    cuttest("他掉进了无底洞里")
    cuttest("中国的首都是北京")
    cuttest("孙君意")
    cuttest("外交部发言人马朝旭")
    cuttest("领导人会议和第四届东亚峰会")
    cuttest("在过去的这五年")
    cuttest("还需要很长的路要走")
    cuttest("60周年首都阅兵")
    cuttest("你好人们审美的观点是不同的")
    cuttest("买水果然后来世博园")
    cuttest("买水果然后去世博园")
    cuttest("但是后来我才知道你是对的")
    cuttest("存在即合理")
    cuttest("的的的的的在的的的的就以和和和")
    cuttest("I love你，不以为耻，反以为rong")
    cuttest("因")
    cuttest("")
    cuttest("hello你好人们审美的观点是不同的")
    cuttest("很好但主要是基于网页形式")
    cuttest("hello你好人们审美的观点是不同的")
    cuttest("为什么我不能拥有想要的生活")
    cuttest("后来我才")
    cuttest("此次来中国是为了")
    cuttest("使用了它就可以解决一些问题")
    cuttest(",使用了它就可以解决一些问题")
    cuttest("其实使用了它就可以解决一些问题")
    cuttest("好人使用了它就可以解决一些问题")
    cuttest("是因为和国家")
    cuttest("老年搜索还支持")
    cuttest("干脆就把那部蒙人的闲法给废了拉倒！RT @laoshipukong : 27日，全国人大常委会第三次审议侵权责任法草案，删除了有关医疗损害责任“举证倒置”的规定。在医患纠纷中本已处于弱势地位的消费者由此将陷入万劫不复的境地。 ")
    cuttest("大")
    cuttest("")
    cuttest("他说的确实在理")
    cuttest("长春市长春节讲话")
    cuttest("结婚的和尚未结婚的")
    cuttest("结合成分子时")
    cuttest("旅游和服务是最好的")
    cuttest("这件事情的确是我的错")
    cuttest("供大家参考指正")
    cuttest("哈尔滨政府公布塌桥原因")
    cuttest("我在机场入口处")
    cuttest("邢永臣摄影报道")
    cuttest("BP神经网络如何训练才能在分类时增加区分度？")
    cuttest("南京市长江大桥")
    cuttest("应一些使用者的建议，也为了便于利用NiuTrans用于SMT研究")
    cuttest('长春市长春药店')
    cuttest('邓颖超生前最喜欢的衣服')
    cuttest('胡锦涛是热爱世界和平的政治局常委')
    cuttest('程序员祝海林和朱会震是在孙健的左面和右面, 范凯在最右面.再往左是李松洪')
    cuttest('一次性交多少钱')
    cuttest('两块五一套，三块八一斤，四块七一本，五块六一条')
    cuttest('小和尚留了一个像大和尚一样的和尚头')
    cuttest('我是中华人民共和国公民;我爸爸是共和党党员; 地铁和平门站')
    cuttest('张晓梅去人民医院做了个B超然后去买了件T恤')
    cuttest('AT&T是一件不错的公司，给你发offer了吗？')
    cuttest('C++和c#是什么关系？11+122=133，是吗？PI=3.14159')
    cuttest('你认识那个和主席握手的的哥吗？他开一辆黑色的士。')
    cuttest('枪杆子中出政权')
    cuttest('张三风同学走上了不归路')
    cuttest('一个和尚')

########NEW FILE########
__FILENAME__ = test_file
import urllib2
import sys,time
import sys
import miniseg

url = sys.argv[1]
content = open(url,"rb").read()
t1 = time.time()
words = list(miniseg.cut(content))

t2 = time.time()
tm_cost = t2-t1

log_f = open("1.log","wb")
for w in words:
	print >> log_f, w.encode("utf-8"), "/" ,
print 'cost',tm_cost
print 'speed' , len(content)/tm_cost, " bytes/second"


########NEW FILE########
__FILENAME__ = gen_feature
import glob,sys

feature_count = 11

def line2items(line):
	items =[x.split('/') for x in  line.split("  ") if x!=""]
	items = [x for x in items if x[1] in ('B','M','E','S')]
	return items

def item2feature(items,idx):
	feature = []
	for j in xrange(idx-2,idx+3):
		if j<0 or j>=len(items):
			feature.append(" ")
		else:
			feature.append(items[j][0].replace("\t"," "))
	
	feature.append(feature[0]+feature[1])
	feature.append(feature[1]+feature[2])
	feature.append(feature[2]+feature[3])
	feature.append(feature[3]+feature[4])
	feature.append(feature[1]+feature[3])
	feature.append(feature[0]+feature[2]+feature[4])

	tag = items[idx][1]
	if not (tag in ('B','M','E','S')):
		raise Exception("invalid tag: " + tag)
	if len(feature)<feature_count:
		raise Exception("invalid feature: "+ str(feature))

	return feature,tag

def process_file(fname,out_f):
	for line in open(fname,'rb'):
			line = line.rstrip().replace("\t"," ").upper()
			items = line2items(line)
			for idx in range(len(items)):
				feature, tag = item2feature(items,idx)
				#print feature
				out_f.write("\t".join(feature)+"\t"+tag+"\n")

if __name__ == "__main__":
	out_f = open("feature.txt","wb")
	if len(sys.argv)<2:
		for fname in glob.glob("train_txt/*.txt"):
			print "reading ", fname
			process_file(fname,out_f)
	else:
		process_file(sys.argv[1],out_f)
	out_f.close()









########NEW FILE########
__FILENAME__ = gen_prob
import glob
import pprint
from math import log

prob_start ={
	'S':0.0,
	'B':0.0
}

prob_trans={
	'S':{},
	'B':{},
	'M':{},
	'E':{}	
}

def line2items(line):
	items =[x.split('/') for x in  line.split("  ") if x!=""]
	items = [x[1] for x in items if x[1] in ('B','M','E','S')]
	return items

def update_freq(items):
	global prob_trans,prob_start
	prev_state = None
	for item in items:
		try:
			if prev_state == None:
				prob_start[item]+=1.0
				prev_state = item
			else:
				if not (item in prob_trans[prev_state]):
					prob_trans[prev_state][item] = 0.0
				prob_trans[prev_state][item]+=1.0
				prev_state = item
		except:
			import traceback
			print traceback.format_exc()

def log_norm_freq():
	global prob_trans,prob_start
	total = sum(prob_start.values())
	prob_start = dict( [ (k, log(v/total)) for k,v in prob_start.iteritems() ] )
	for k,v in prob_trans.iteritems():
		sub_sum = sum(v.values())
		prob_trans[k] = dict([ (kk,log(vv/sub_sum)) for kk,vv in v.iteritems()])

def dump():
	global prob_trans,prob_start
	pprint.pprint(prob_start,open("prob_start.py",'wb'))
	pprint.pprint(prob_trans,open("prob_trans.py",'wb'))

if __name__ == "__main__":

	for fname in glob.glob("train_txt/*.txt"):
		print "reading ", fname
		for line in open(fname,'rb'):
			line = line.rstrip().replace("\t"," ").upper()
			items = line2items(line)
			update_freq(items)
	log_norm_freq()
	dump()




########NEW FILE########
__FILENAME__ = prob_start
{'B': -0.8877383940489068, 'S': -0.5303237243812831}

########NEW FILE########
__FILENAME__ = prob_trans
{'B': {'E': -0.16518441189682853, 'M': -1.8821483335951348},
 'E': {'B': -0.8064261824909028, 'S': -0.591404555286857},
 'M': {'E': -0.365305528574006, 'M': -1.184119806934594},
 'S': {'B': -0.8973769931843144, 'S': -0.5236364912754701}}

########NEW FILE########
__FILENAME__ = train_bayes_model
import marshal
import traceback
from math import log

feature_count = 11

model={
	'obs':
	{
		'S':[{} for x in range(feature_count)],
		'B':[{} for x in range(feature_count)],
		'M':[{} for x in range(feature_count)],
		'E':[{} for x in range(feature_count)],
	},
	'total':{
		'S':[0.0]*feature_count,
		'B':[0.0]*feature_count,
		'M':[0.0]*feature_count,
		'E':[0.0]*feature_count,
	}
}

def line_update(line):
	global model
	try:
		items = line.split("\t")
		features = items[:feature_count]
		state = items[feature_count].upper()
		for idx,chars in enumerate(features):
			if chars.strip()=="":
				continue
			table = model['obs'][state][idx]
			if not (chars in table):
				table[chars]=0.0
			table[chars]+=1.0
	except:
		try:
			print line
			print traceback.format_exc()
		except:
			pass

def log_normalize():
	global model
	for state in ('S','B','M','E'):
		for idx,table in enumerate(model['obs'][state]):
			ssum = sum([v for v in table.itervalues() if v>1])
			model['total'][state][idx] = ssum
			model['obs'][state][idx] = dict([ (k,log(v/ssum)) for k,v in table.iteritems() if v>1])

def dump_model(file_name):
	global model
	outf = open(file_name,"wb")
	with outf:
		marshal.dump(model,outf)

if __name__ == "__main__":

	ct = 0 
	for line in open("feature.txt",'rb'):
		line = line.rstrip().decode('utf-8')
		line_update(line)
		ct+=1
		if ct%10000==0:
			print "line ", ct, "completed."
	print "loaded."
	log_normalize()
	print "normalized."
	dump_model("bayes_model.marshal")
	print "dumped"


########NEW FILE########
__FILENAME__ = train_increamental
import marshal
import traceback
from math import log,exp
import sys

feature_count = 11

model={
	'obs':
	{
		'S':[{} for x in range(feature_count)],
		'B':[{} for x in range(feature_count)],
		'M':[{} for x in range(feature_count)],
		'E':[{} for x in range(feature_count)],
	},
	'total':{
		'S':[0.0]*feature_count,
		'B':[0.0]*feature_count,
		'M':[0.0]*feature_count,
		'E':[0.0]*feature_count,
	}
}

def line_update(line):
	global model
	try:
		items = line.split("\t")
		features = items[:feature_count]
		state = items[feature_count].upper()
		for idx,chars in enumerate(features):
			if chars.strip()=="":
				continue
			table = model['obs'][state][idx]
			if not (chars in table):
				table[chars]=0.0
			table[chars]+=1.0
	except:
		try:
			print line
			print traceback.format_exc()
		except:
			pass

def log_normalize():
	global model
	for state in ('S','B','M','E'):
		for idx,table in enumerate(model['obs'][state]):
			ssum = sum([v for v in table.itervalues() if v>1])
			model['total'][state][idx] = ssum
			model['obs'][state][idx] = dict([ (k,log(v/ssum)) for k,v in table.iteritems() if v>1])

def dump_model(file_name):
	global model
	outf = open(file_name,"wb")
	with outf:
		marshal.dump(model,outf)

def load_old_model(file_name):
	global model
	inf = open(file_name,"rb")
	with inf:
		model = marshal.load(inf)
	for state in ('S','B','M','E'):
		for idx,table in enumerate(model['obs'][state]):
			ssum = model['total'][state][idx]
			model['obs'][state][idx] = dict([ (k,exp(p)*ssum) for k,p in table.iteritems()])

if __name__ == "__main__":
	if len(sys.argv)<3:
		print "usage: python train_incremental.py [model file name] [feature file name]"
		sys.exit(0)

	old_model_file_name = sys.argv[1]
	feature_file_name = sys.argv[2]
	load_old_model(old_model_file_name)
	print "old model loaded."
	ct = 0 
	for line in open("feature.txt",'rb'):
		line = line.rstrip().decode('utf-8')
		line_update(line)
		ct+=1
		if ct%10000==0:
			print "line ", ct, "completed."
	
	log_normalize()
	print "normalized."
	new_model_name = old_model_file_name+".new"
	dump_model(new_model_name)
	print new_model_name,"dumped"



########NEW FILE########
