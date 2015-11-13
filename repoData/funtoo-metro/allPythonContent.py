__FILENAME__ = catalyst_support

import sys,string,os,types,re,signal,traceback
#import md5,sha
selinux_capable = False
#userpriv_capable = (os.getuid() == 0)
#fakeroot_capable = False
BASH_BINARY             = "/bin/bash"

class MetroError(Exception):
	def __init__(self, *args):
		self.args = args
	def __str__(self):
		if len(self.args) == 1:
			return str(self.args[0])
		else:
			return "(no message)"

try:
        import resource
        max_fd_limit=resource.getrlimit(RLIMIT_NOFILE)
except SystemExit, e:
        raise
except:
        # hokay, no resource module.
        max_fd_limit=256

# pids this process knows of.
spawned_pids = []

def cleanup(pids,block_exceptions=True):
        """function to go through and reap the list of pids passed to it"""
        global spawned_pids
        if type(pids) == int:
                pids = [pids]
        for x in pids:
                try:
                        os.kill(x,signal.SIGTERM)
                        if os.waitpid(x,os.WNOHANG)[1] == 0:
                                # feisty bugger, still alive.
                                os.kill(x,signal.SIGKILL)
                                os.waitpid(x,0)

                except OSError, oe:
                        if block_exceptions:
                                pass
                        if oe.errno not in (10,3):
                                raise oe
                except SystemExit:
                        raise
                except Exception:
                        if block_exceptions:
                                pass
                try:                    spawned_pids.remove(x)
                except IndexError:      pass

verbosity=1

def warn(msg):
	print "!!! metro: "+msg

def spawn_bash(mycommand,env={},debug=False,opt_name=None,**keywords):
	"""spawn mycommand as an arguement to bash"""
	args=[BASH_BINARY]
	if not opt_name:
	    opt_name=mycommand.split()[0]
	if debug:
	    args.append("-x")
	args.append("-c")
	args.append(mycommand)
	return spawn(args,env=env,opt_name=opt_name,**keywords)

#def spawn_get_output(mycommand,spawn_type=spawn,raw_exit_code=False,emulate_gso=True, \
#        collect_fds=[1],fd_pipes=None,**keywords):
def spawn_get_output(mycommand,raw_exit_code=False,emulate_gso=True, \
        collect_fds=[1],fd_pipes=None,**keywords):
        """call spawn, collecting the output to fd's specified in collect_fds list
        emulate_gso is a compatability hack to emulate commands.getstatusoutput's return, minus the
        requirement it always be a bash call (spawn_type controls the actual spawn call), and minus the
        'lets let log only stdin and let stderr slide by'.

        emulate_gso was deprecated from the day it was added, so convert your code over.
        spawn_type is the passed in function to call- typically spawn_bash, spawn, spawn_sandbox, or spawn_fakeroot"""
        global selinux_capable
        pr,pw=os.pipe()

        #if type(spawn_type) not in [types.FunctionType, types.MethodType]:
        #        s="spawn_type must be passed a function, not",type(spawn_type),spawn_type
        #        raise Exception,s

        if fd_pipes==None:
                fd_pipes={}
                fd_pipes[0] = 0

        for x in collect_fds:
                fd_pipes[x] = pw
        keywords["returnpid"]=True

        mypid=spawn_bash(mycommand,fd_pipes=fd_pipes,**keywords)
        os.close(pw)
        if type(mypid) != types.ListType:
                os.close(pr)
                return [mypid, "%s: No such file or directory" % mycommand.split()[0]]

        fd=os.fdopen(pr,"r")
        mydata=fd.readlines()
        fd.close()
        if emulate_gso:
                mydata=string.join(mydata)
                if len(mydata) and mydata[-1] == "\n":
                        mydata=mydata[:-1]
        retval=os.waitpid(mypid[0],0)[1]
        cleanup(mypid)
        if raw_exit_code:
                return [retval,mydata]
        retval=process_exit_code(retval)
        return [retval, mydata]


# base spawn function
def spawn(mycommand,env={},raw_exit_code=False,opt_name=None,fd_pipes=None,returnpid=False,\
	 uid=None,gid=None,groups=None,umask=None,logfile=None,path_lookup=True,\
	 selinux_context=None, raise_signals=False, func_call=False):
        """base fork/execve function.
	mycommand is the desired command- if you need a command to execute in a bash/sandbox/fakeroot
	environment, use the appropriate spawn call.  This is a straight fork/exec code path.
	Can either have a tuple, or a string passed in.  If uid/gid/groups/umask specified, it changes
	the forked process to said value.  If path_lookup is on, a non-absolute command will be converted
	to an absolute command, otherwise it returns None.

	selinux_context is the desired context, dependant on selinux being available.
	opt_name controls the name the processor goes by.
	fd_pipes controls which file descriptor numbers are left open in the forked process- it's a dict of
	current fd's raw fd #, desired #.

	func_call is a boolean for specifying to execute a python function- use spawn_func instead.
	raise_signals is questionable.  Basically throw an exception if signal'd.  No exception is thrown
	if raw_input is on.

	logfile overloads the specified fd's to write to a tee process which logs to logfile
	returnpid returns the relevant pids (a list, including the logging process if logfile is on).

	non-returnpid calls to spawn will block till the process has exited, returning the exitcode/signal
	raw_exit_code controls whether the actual waitpid result is returned, or intrepretted."""


	myc=''
	if not func_call:
		if type(mycommand)==types.StringType:
			mycommand=mycommand.split()
		myc = mycommand[0]
		if not os.access(myc, os.X_OK):
			if not path_lookup:
				return None
			myc = find_binary(myc)
			if myc == None:
				return None
        mypid=[]
	if logfile:
		pr,pw=os.pipe()
		mypid.extend(spawn(('tee','-i','-a',logfile),returnpid=True,fd_pipes={0:pr,1:1,2:2}))
		retval=os.waitpid(mypid[-1],os.WNOHANG)[1]
		if retval != 0:
			# he's dead jim.
			if raw_exit_code:
				return retval
			return process_exit_code(retval)

		if fd_pipes == None:
			fd_pipes={}
			fd_pipes[0] = 0
		fd_pipes[1]=pw
		fd_pipes[2]=pw

	if not opt_name:
		opt_name = mycommand[0]
	myargs=[opt_name]
	myargs.extend(mycommand[1:])
	global spawned_pids
	mypid.append(os.fork())
	if mypid[-1] != 0:
		#log the bugger.
		spawned_pids.extend(mypid)

	if mypid[-1] == 0:
		if func_call:
			spawned_pids = []

		# this may look ugly, but basically it moves file descriptors around to ensure no
		# handles that are needed are accidentally closed during the final dup2 calls.
		trg_fd=[]
		if type(fd_pipes)==types.DictType:
			src_fd=[]
			k=fd_pipes.keys()
			k.sort()

			#build list of which fds will be where, and where they are at currently
			for x in k:
				trg_fd.append(x)
				src_fd.append(fd_pipes[x])

			# run through said list dup'ing descriptors so that they won't be waxed
			# by other dup calls.
			for x in range(0,len(trg_fd)):
				if trg_fd[x] == src_fd[x]:
					continue
				if trg_fd[x] in src_fd[x+1:]:
					new=os.dup2(trg_fd[x],max(src_fd) + 1)
					os.close(trg_fd[x])
					try:
						while True:
							src_fd[s.index(trg_fd[x])]=new
					except SystemExit, e:
						raise
					except:
						pass

			# transfer the fds to their final pre-exec position.
			for x in range(0,len(trg_fd)):
				if trg_fd[x] != src_fd[x]:
					os.dup2(src_fd[x], trg_fd[x])
		else:
			trg_fd=[0,1,2]

		# wax all open descriptors that weren't requested be left open.
		for x in range(0,max_fd_limit):
			if x not in trg_fd:
				try:
					os.close(x)
                                except SystemExit, e:
                                        raise
                                except:
                                        pass

                # note this order must be preserved- can't change gid/groups if you change uid first.
                if selinux_capable and selinux_context:
                        import selinux
                        selinux.setexec(selinux_context)
                if gid:
                        os.setgid(gid)
                if groups:
                        os.setgroups(groups)
                if uid:
                        os.setuid(uid)
                if umask:
                        os.umask(umask)

                try:
                        #print "execing", myc, myargs
                        if func_call:
                                # either use a passed in func for interpretting the results, or return if no exception.
                                # note the passed in list, and dict are expanded.
                                if len(mycommand) == 4:
                                        os._exit(mycommand[3](mycommand[0](*mycommand[1],**mycommand[2])))
                                try:
                                        mycommand[0](*mycommand[1],**mycommand[2])
                                except Exception,e:
                                        print "caught exception",e," in forked func",mycommand[0]
                                sys.exit(0)

			#os.execvp(myc,myargs)
                        os.execve(myc,myargs,env)
                except SystemExit, e:
                        raise
                except Exception, e:
                        if not func_call:
                                raise MetroError, str(e)+":\n   "+myc+" "+string.join(myargs)
                        print "func call failed"

                # If the execve fails, we need to report it, and exit
                # *carefully* --- report error here
                os._exit(1)
                sys.exit(1)
                return # should never get reached

        # if we were logging, kill the pipes.
        if logfile:
                os.close(pr)
                os.close(pw)

        if returnpid:
                return mypid

        # loop through pids (typically one, unless logging), either waiting on their death, or waxing them
        # if the main pid (mycommand) returned badly.
        while len(mypid):
		try:
                	retval=os.waitpid(mypid[-1],0)[1]
		except KeyboardInterrupt:
			print "Keyboard interrupt detected, aborting script..."
			os.kill(mypid[-1],signal.SIGINT)
			continue
                if retval != 0:
                        cleanup(mypid[0:-1],block_exceptions=False)
                        # at this point we've killed all other kid pids generated via this call.
                        # return now.
                        if raw_exit_code:
                                return retval
                        return process_exit_code(retval,throw_signals=raise_signals)
                else:
                        mypid.pop(-1)
        cleanup(mypid)
        return 0

def process_exit_code(retval,throw_signals=False):
        """process a waitpid returned exit code, returning exit code if it exit'd, or the
        signal if it died from signalling
        if throw_signals is on, it raises a SystemExit if the process was signaled.
        This is intended for usage with threads, although at the moment you can't signal individual
        threads in python, only the master thread, so it's a questionable option."""
        if (retval & 0xff)==0:
                return retval >> 8 # return exit code
        else:
                if throw_signals:
                        #use systemexit, since portage is stupid about exception catching.
                        raise SystemExit()
                return (retval & 0xff) << 8 # interrupted by signal

def msg(mymsg,verblevel=1):
	if verbosity>=verblevel:
		print mymsg

def ismount(path):
	"enhanced to handle bind mounts"
	if os.path.ismount(path):
		return 1
	a=os.popen("mount")
	mylines=a.readlines()
	a.close()
	for line in mylines:
		mysplit=line.split()
		if os.path.normpath(path) == os.path.normpath(mysplit[2]):
			return 1
	return 0

def touch(myfile):
	try:
		myf=open(myfile,"w")
		myf.close()
	except IOError:
		raise MetroError, "Could not touch "+myfile+"."

########NEW FILE########
__FILENAME__ = flexdata
#!/usr/bin/python

import sys,os,types,StringIO,string

class FlexDataError(Exception):
	def __init__(self, message):
		if message:
			print
			print "Metro Parser: "+message
			print

class collection:
	""" The collection class holds our parser.

	__init__() contains several important variable definitions.

	self.immutable - if set to true, the parser will throw a warning if a variable is redefined. Otherwise it will not.
	This variable can be toggled at any time, so a collection can start out in a mutable state and then be switched to
	immutable for parsing of additional files.

	self.lax = the "lax" option, if True, will allow for a undefined single-line variable to expand to the empty string.
	If lax is False, then the parser will throw an exception if an undefined single-line variable is expanded.

	"""
	def __init__(self,debug=False):
		self.clear()
		self.debug=debug
		self.pre = "$["
		self.suf = "]"
		self.immutable=False
		# lax means: if a key isn't found, pretend it exists but return the empty string.
		self.lax=False
		self.laxvars={}
		self.blanks={}
		# self.collected holds the names of files we've collected (parsed)
		self.collected=[]
		self.section=""
		self.sectionfor={}
		self.conditional=None
		self.collector=[]
		self.collectorcond={}
	def clear(self):
		self.raw={}
		self.conditionals={}
		self.blanks={}

	def expand_all(self):
		# try to expand all variables to find any undefined elements, to record all blanks or throw an exception
		for key in self.keys():
			myvar = self[key]

	def get_condition_for(self,varname):
		if not self.conditionals.has_key(varname):
			return None
		truekeys=[]
		for cond in self.conditionals[varname].keys():
			#if self.conditionOnConditional(cond):
			#	raise FlexDataError, "Not Allowed: conditional variable %s depends on condition %s which is itself a conditional variable." % ( varname, cond )
			if self.conditionTrue(cond):
				truekeys.append(cond)
			if len(truekeys) > 1:
				raise FlexDataError, "Multiple true conditions exist for %s: conditions: %s" % (varname, repr(truekeys))
		if len(truekeys) == 1:
			return self.conditionals[varname][truekeys[0]]
		elif len(truekeys) == 0:
			return None
		else:
			#shouldn't get here
			raise FlexDataError


	def expand(self,myvar,options={}):
		if myvar[-1] == "?":
			boolean = True
			myvar = myvar[:-1]
		else:
			boolean = False
		if self.raw.has_key(myvar):
			typetest = self.raw[myvar]
		elif self.conditionals.has_key(myvar):
			# test the type of the first conditional - in the future, we should ensure all conditional values are of the same type
			typetest = self.conditionals[myvar][self.conditionals[myvar].keys()[0]]
		# FIXME: COME BACK HERE AND FIX THIS
		elif self.laxvars.has_key(myvar) and self.laxvars[myvar]:
			# record that we looked up an undefined element
			self.blanks[myvar]=True
			if boolean:
				return "no"
			else:
				return ""
		else:
			if boolean:
				return "no"
			else:
				raise FlexDataError,"Variable \""+myvar+"\" not found foo"
		if type(typetest) == types.ListType:
			if boolean:
				return "yes"
			else:
				return self.expandMulti(myvar,options=options)
		else:
			return self.expandString(myvar=myvar,options=options)

	def expandString(self,mystring=None,myvar=None,stack=[],options={}):
		# Expand all variables in a basic value, ie. a string
		if mystring == None:
			if myvar[-1] == "?":
				boolean = True
				myvar = myvar[:-1]
			else:
				boolean = False
			if self.raw.has_key(myvar):
				if boolean:
					if self.raw[myvar].strip() == "":
						# blanks are considered undefined
						mystring = "no"
					else:
						mystring = "yes"
				else:
					mystring = self.raw[myvar]
			else:
				mystring = self.get_condition_for(myvar)
				if mystring == None:
					if boolean:
						mystring = "no"
					elif len(stack) and self.laxvars.has_key(stack[-1]) and self.laxvars[stack[-1]]:
						mystring = ""
					else:
						raise KeyError, "Variable "+repr(myvar)+" not found."
				elif boolean:
					mystring = "yes"

		#if type(string) != types.StringType:
		#		if len(stack) >=1:
		#		raise FlexDataError("expandString received non-string when expanding "+repr(myvar)+" ( stack = "+repr(stack)+")")
		#	else:
		#		raise FlexDataError("expandString received non-string: %s" % repr(string) )

		if type(mystring) == types.StringType:
			mysplit = mystring.strip().split(" ")
		else:
			# concatenate multi-line element, then strip
			mysplit = []
			for line in mystring:
				mysplit.append(line.strip())
			mystring = " ".join(mysplit).strip()
			mysplit = mystring.split(" ")

		if len(mysplit) == 2 and mysplit[0] == "<<":
		 	fromfile = True
			mystring = " ".join(mysplit[1:])
		else:
			fromfile = False

		unex = mystring
		ex = ""
		while unex != "":
			varpos = unex.find(self.pre)
			if varpos == -1:
				ex += unex
				unex = ""
				continue
			if unex[varpos:varpos+len(self.pre)+1] == "$[[":
				# extra [, so it's a multi-line element .... which we just pass to the output unexpanded since it might be comented out...
				# (we don't want to throw an excption if someone put a # in front of it.
				ex += unex[0:varpos+len(self.pre)+1]
				unex = unex[varpos+len(self.pre)+1:]
				continue
			# OK, this looks like a regular single-line element
			ex += unex[0:varpos]
			unex = unex[varpos+len(self.pre):] # remove "$["
			endvarpos = unex.find(self.suf)
			if endvarpos == -1:
				raise FlexDataError,"Error expanding variable for '"+mystring+"'"
			varname = unex[0:endvarpos]
			if len(varname)>0 and varname[-1] == "?":
				boolean = True
				varname = varname[:-1]
			else:
				boolean = False
			# $[] and $[:] expansion
			if varname == "" or varname == ":":
				if self.sectionfor.has_key(myvar):
					varname = self.sectionfor[myvar]
				else:
					raise FlexDataError, "no section name for "+myvar+" in "+mystring
			# NEW STUFF BELOW:
			elif varname[0] == ":":
				# something like $[:foo/bar]
				if self.sectionfor.has_key(myvar):
					varname = self.sectionfor[myvar]+"/"+varname[1:]
				else:
					raise FlexDataError, "no section name for "+myvar+" in "+mystring
			varsplit=varname.split(":")
			newoptions=options.copy()
			zapmode=False
			if len(varsplit) == 1:
				pass
			elif len(varsplit) == 2:
				if varsplit[1] == "zap":
					zapmode=True
					varname=varsplit[0]
				elif varsplit[1] == "lax":
					newoptions["lax"]=True
					varname=varsplit[0]
				else:
					raise FlexDataError, "expanding variable %s - mode %s does not exist" % (varname, varsplit[1])
			else:
				raise FlexDataError, 'expanding variable %s - invalid variable' % varname
			unex = unex[endvarpos+len(self.suf):]
			if varname in stack:
				raise KeyError, "Circular reference of '"+varname+"' by "+repr(myvar)+" ( Call stack: "+repr(stack)+' )'
			if self.raw.has_key(varname):
				# if myvar == None, we are being called from self.expand_all() and we don't care where we are being expanded from
				#if myvar != None and type(self.raw[varname]) == types.ListType:
				#	raise FlexDataError,"Trying to expand multi-line value "+repr(varname)+" in single-line value "+repr(myvar)
				newstack = stack[:]
				newstack.append(myvar)
				if not boolean:
					newex = self.expandString(self.raw[varname],varname,newstack,options=newoptions)
					if newex == "" and zapmode==True:
						# when expandMulti gets None, it won't add this line so we won't get a blank line even
						return None
					else:
						if newex != None:
							ex += newex
						else:
							return None
				else:
					# self.raw[varname] can be a list .. if it's a string and blank, we treat it as undefined.
					if type(self.raw[varname]) == types.StringType and self.raw[varname].strip() == "":
						ex += "no"
					else:
						ex += "yes"
			elif self.conditionals.has_key(varname):
				expandme = self.get_condition_for(varname)
				newstack=stack[:]
				newstack.append(myvar)
				if expandme == None:
					raise KeyError, "Variable %s not found (stack: %s )" % (varname, repr(newstack))
				if not boolean:
					ex += self.expandString(expandme,varname,newstack,options=newoptions)
				else:
					ex += "yes"
			else:
				if zapmode:
					# a ":zap" will cause the line to be deleted if there is no variable defined or the var evals to an empty string
					# when expandMulti gets None, it won't add this line so we won't get a blank line even
					return None
				if ("lax" in newoptions.keys()) or (len(stack) and self.laxvars.has_key(stack[-1]) and self.laxvars[stack[-1]]):
					# record variables that we attempted to expand but were blank, so we can inform the user of possible bugs
					if boolean:
						ex += "no"
					else:
						self.blanks[varname] = True
						ex += ""
				else:
					if not boolean:
						raise KeyError, "Cannot find variable %s (in %s)" % (varname,myvar)
					else:
						ex += "no"
		if fromfile == False:
			return ex

		#use "ex" as a filename
		try:
			myfile=open(ex,"r")
		except:
			raise FlexDataError,"Cannot open file "+ex+" specified in variable \""+mystring+"\""
		outstring=""
		for line in myfile.readlines():
			outstring=outstring+line[:-1]+" "
		myfile.close()
		return outstring[:-1]


	def expandMulti(self,myvar,stack=[],options={}):
		# TODO: ADD BOOLEAN SUPPORT HERE - NOT DONE YET
		mylocals = {}
		myvarsplit=myvar.split(":")
		# any future expansions will get our "new" options, but we don't want to pollute our current options by modifying
		# options...
		newoptions=options.copy()
		# detect and properly handle $[[foo:lax]]
		if len(myvarsplit) == 2:
			if myvarsplit[1] == "lax":
				newoptions["lax"] = True
				myvar = myvarsplit[0]
			else:
				raise FlexDataError, "Invalid multi-line variable"

		# Expand all variables in a multi-line value. stack is used internally to detect circular references.
		if self.raw.has_key(myvar):
			multi = self.raw[myvar]
			if type(multi) != types.ListType:
				raise FlexDataError("expandMulti received non-multi")
		else:
			multi = self.get_condition_for(myvar)
			if multi == None:
				if ("lax" in newoptions.keys()) or (len(stack) and self.laxvars.has_key(stack[-1]) and self.laxvars[stack[-1]]):
					self.blanks[myvar] = True
					return ""
				else:
					raise FlexDataError("referenced variable \""+myvar+"\" not found")
		newlines=[]

		pos=0
		while pos<len(multi):
			mystrip = multi[pos].strip()
			mysplit = mystrip.split(" ")
			if len(mysplit) > 0 and len(mysplit) < 3 and mystrip[0:3] == "$[[" and mystrip[-2:] == "]]":
				myref=mystrip[3:-2]
				if myref in stack:
					raise FlexDataError,"Circular reference of '"+myref+"' by '"+stack[-1]+"' ( Call stack: "+repr(stack)+' )'
				newstack = stack[:]
				newstack.append(myvar)
				newlines += self.expandMulti(self.expandString(mystring=myref),newstack,options=newoptions)
			elif len(mysplit) >=1 and mysplit[0] == "<?python":
				sys.stdout = StringIO.StringIO()
				mycode=""
				pos += 1
				while (pos < len(multi)):
				    	newsplit = multi[pos].split()
				     	if len(newsplit) >= 1 and newsplit[0] == "?>":
				      		break
				       	else:
						mycode += multi[pos] + "\n"
					 	pos += 1
				exec mycode in { "os": os }, mylocals
				newlines.append(sys.stdout.getvalue())
				sys.stdout = sys.__stdout__
			else:
				newline = self.expandString(mystring=multi[pos],options=newoptions)
				if newline != None:
					newlines.append(newline)
			pos += 1
		return newlines

	def __setitem__(self,key,value):
		if self.immutable and self.raw.has_key(key):
			raise IndexError, "Attempting to redefine "+key+" to "+value+" when immutable."
		self.raw[key]=value

	def __delitem__(self,key):
		if self.immutable and self.raw.has_key(key):
			raise IndexError, "Attempting to delete "+key+" when immutable."
		del self.raw[key]

	def __getitem__(self,element):
		return self.expand(element)

	def has_key(self,key):
		if self.raw.has_key(key):
			return True
		else:
			ret = self.get_condition_for(key)
		if ret != None:
			return True
		else:
			return False

	def keys(self):
		mylist=self.raw.keys()
		for x in self.conditionals:
			mycond = self.get_condition_for(x)
			if mycond != None:
				mylist.append(x)
		return mylist

	def missing(self,keylist):
		""" return list of any keys that are not defined. good for validating that we have a bunch of required things defined."""
		missing=[]
		for key in keylist:
			if not self.raw.has_key(key):
				missing.append(key)
		return missing

	def skipblock(self,openfile=None):
		while 1:
			curline=openfile.readline()
			mysplit = curline[:-1].strip().split(" ")
			if len(mysplit) == 0:
				continue
			if mysplit[0] == "}":
				return
			else:
				continue

	def parseline(self,filename,openfile=None,dups=False):

		# parseline() will parse a line and return None on EOF, return [] on a blank line with no data, or will
		# return a list of string elements if there is data on the line, split along whitespace: [ "foo:", "bar", "oni" ]
		# parseline() will also remove "# comments" from a line as appropriate
		# parseline() will update self.raw with new data as it finds it.
		if type(openfile) == types.StringType:
			curline = openfile + '\n'
		else:
			curline = openfile.readline()
		if curline == "": #EOF
			return None
		# get list of words separated by whitespace
		mysplit = curline[:-1].strip().split(" ")
		if len(mysplit) == 1 and  mysplit[0] == '':
			# blank line
			return []
		#strip comments
		spos = 0
		while 1:
			if spos >= len(mysplit):
				break
			if len(mysplit[spos]) == 0:
				spos += 1
				continue
			if mysplit[spos][0] == "#":
				mysplit=mysplit[0:spos]
				break
			spos += 1

		if len(mysplit) == 0:
			return []

		#parse elements
		if len(mysplit[0]) == 0:
			# not an element
			return []

		if len(mysplit) == 2 and mysplit[0][-1] == ":" and mysplit[1] == "[":
			# for myvar, remove trailing colon:
			myvar = mysplit[0][:-1]
			if self.section:
				myvar = self.section+"/"+myvar
				self.sectionfor[myvar] = self.section
			self.laxvars[myvar] = self.lax
			mylines = []
			while 1:
				curline = openfile.readline()
				if curline == "":
					raise KeyError,"Error - incomplete [[ multi-line block,"
				mysplit = curline[:-1].strip().split(" ")
				if len(mysplit) == 1 and mysplit[0] == "]":
					# record value and quit
					# FIXME - MISSING COND HERE!?!?!?
					if self.conditional:
						if not self.conditionals.has_key(myvar):
							self.conditionals[myvar]={}
						if self.conditionals[myvar].has_key(self.conditional):
							raise FlexDataError,"Conditional element %s already defined for condition %s" % (myvar, self.conditional)
						self.conditionals[myvar][self.conditional] = mylines
					elif not dups and self.raw.has_key(myvar):
						raise FlexDataError,"Error - \""+myvar+"\" already defined."
					else:
						self.raw[myvar] = mylines
					break
				else:
					# append new line
					mylines.append(curline[:-1])
		elif mysplit[0][0]=="[" and mysplit[-1][-1]=="]":
			# possible section
			mysplit[0] = mysplit[0][1:]
			mysplit[-1]= mysplit[-1][:-1]
			mysection=string.join(mysplit).split()
			if mysection[0] == "section":
				self.section = mysection[1]
				if len(mysection) > 2:
					if mysection[2] != "when":
						raise FlexDataError,"Expecting \"when\": "+curline[:-1]
					self.conditional=" ".join(mysection[3:])
					if self.conditional == "*":
						self.conditional = None
				elif len(mysection) == 2:
					# clear conditional:
					self.conditional = None
				else:
					raise FlexDataError,"Invalid section specifier: "+curline[:-1]
			elif mysection[0] == "option":
				if mysection[1] == "parse/lax":
					self.lax = True
				elif mysection[1] == "parse/strict":
					self.lax = False
				else:
					raise FlexDataError,"Unexpected option in [option ] section: %s" % mysection[1]
			elif mysection[0] == "when":
				# conditional block
				self.conditional=" ".join(mysection[1:])
				if self.conditional == "*":
					self.conditional = None
			elif mysection[0] == "collect":
				if self.conditional:
					# This part of the code handles a [collect] annotation that appears inside a [when] block - we use the [when] condition in this case
					if len(mysection)>=3:
						raise FlexDataError, "Conditional collect annotations not allowed inside \"when\" annotations: %s" % repr(mysection)
					self.collectorcond[mysection[1]]=self.conditional
					# append what to collect, followed by the filename that the collect annotation appeared in. We will use this later, for
					# expanding relative paths.
					self.collector.append([mysection[1],filename]),
				elif len(mysection)>3:
					if mysection[2] == "when":
						self.collectorcond[mysection[1]]=" ".join(mysection[3:])
						# even with a conditional, we still put the thing on the main collector list:
						self.collector.append([mysection[1],filename])
						#self.collector.append(mysection[1])
					else:
						raise FlexDataError,"Ow, [collect] clause seems invalid"
				elif len(mysection)==2:
					self.collector.append([mysection[1],filename])
				else:
					raise FlexDataError,"Ow, [collect] expects 1 or 4+ arguments."
			else:
				raise FlexDataError,"Invalid annotation: %s in %s" % (mysection[0], curline[:-1])
		elif mysplit[0][-1] == ":":
			#basic element - rejoin all data elements with spaces and add to self.raw
			mykey = mysplit[0][:-1]
			if mykey == "":
				# ":" tag
				mykey = self.section
			elif self.section:
				mykey = self.section+"/"+mykey
				self.sectionfor[mykey]=self.section
			self.laxvars[mykey]=self.lax
			myvalue = " ".join(mysplit[1:])
			if self.conditional:
				if not self.conditionals.has_key(mykey):
					self.conditionals[mykey]={}
				if self.conditionals[mykey].has_key(self.conditional):
					raise FlexDataError,"Conditional element %s already defined for condition %s" % (mykey, self.conditional)
				self.conditionals[mykey][self.conditional] = myvalue
			else:
				if not dups and self.raw.has_key(mykey):
					raise FlexDataError,"Error - \""+mykey+"\" already defined. Value: %s. New line: %s." % ( repr(self.raw[mykey]), curline[:-1] )
				self.raw[mykey] = myvalue
		return mysplit

	def collect(self,filename,origfile):
		if not os.path.isabs(filename):
			# relative path - use origfile (the file the collect annotation appeared in) to figure out what we are relative to
			filename=os.path.normpath(os.path.dirname(origfile)+"/"+filename)
		if not os.path.exists(filename):
			raise IOError, "File '"+filename+"' does not exist."
		if not os.path.isfile(filename):
			raise IOError, "File to be parsed '"+filename+"' is not a regular file."
		self.conditional = None
		openfile = open(filename,"r")
		self.section=""
		while 1:
			out=self.parseline(filename,openfile)
			if out == None:
				break
		openfile.close()
		# add to our list of parsed files
		if self.debug:
			sys.stdout.write("Debug: collected: %s\n" % os.path.normpath(filename))
		self.collected.append(os.path.normpath(filename))

	def conditionOnConditional(self,cond):
		"""defining a conditial var based on another conditional var is illegal. This function will tell us if we are in this mess."""
		if cond == None:
			return False
		cond=cond.split()
		if len(cond) == 1:
			if self.raw.has_key(cond[0]):
				return False
			elif self.conditionals.has_key(cond[0]):
				return True
			else:
				# undefined
				return False
		elif len(cond) == 0:
			raise FlexDataError, "Condition %s is invalid" % cond
		elif len(cond) >= 3:
			if cond[1] not in [ "is", "in"]:
				raise FlexDataError, "Expecting 'is' or 'in' in %s" % cond
			if self.raw.has_key(cond[0]):
				return False
			elif self.conditionals.has_key(cond[0]):
				return True
			else:
				# undefined
				return False


	def conditionTrue(self,cond):
		cond=cond.split()
		if len(cond) == 1:
			if self.raw.has_key(cond[0]):
				return True
			else:
				return False
		elif len(cond) == 0:
			raise FlexDataError, "Condition "+repr(cond)+" is invalid"
		elif len(cond) >= 3 and cond[1] in [ "is", "in" ]:
			if not self.raw.has_key(cond[0]):
				# maybe it's not defined
				return False
			# loop over multiple values, such as "target is ~x86 x86 amd64", if one is equal, then it's true
			for curcond in cond[2:]:
				if self[cond[0]] == curcond:
					return True
			return False
		else:
			raise FlexDataError, "Invalid condition"


	def runCollector(self):
		# BUG? we may need to have an expandString option that will disable the ability to go to the evaluated dict,
		# because as we parse new files, we have new data and some "lax" evals may evaluate correctly now.

		# BUG: detect if we are trying to collect a single file multiple times. :)

		# contfails means "continuous expansion failures" - if we get to the point where we are not making progress,
		# ie. contfails >= len(self.collector), then abort with a failure as we can't expand our cute little variable.
		contfails = 0
		oldlax = self.lax
		self.lax = False
		while len(self.collector) != 0 and contfails < len(self.collector):
			# grab the first item from our collector list
			try:
				myitem, origfile = self.collector[0]
			except ValueError:
				raise FlexDataError, repr(self.collector[0])+" does not appear to be good"
			if self.collectorcond.has_key(myitem):
				cond = self.collectorcond[myitem]
				if self.conditionOnConditional(cond):
					raise FlexDataError,"Collect annotation %s has conditional %s that references a conditional variable, which is not allowed." % (myitem, cond)
				# is the condition true?:
				if not self.conditionTrue(cond):
					contfails += 1
					self.collector = self.collector[1:] + [self.collector[0]]
					continue
				else:
					try:
						myexpand = self.expandString(mystring=myitem)
					except KeyError:
						contfails +=1
						self.collector = self.collector[1:] + [self.collector[0]]
						continue
					self.collect(myexpand, origfile)
					self.collector=self.collector[1:]
					contfails = 0
			else:
				try:
					myexpand = self.expandString(mystring=myitem)
				except KeyError:
					contfails += 1
					# move failed item to back of list
					self.collector = self.collector[1:] + [self.collector[0]]
					continue
				# read in data:
				if myexpand not in [ "", None ]:
					# if expands to blank, with :zap, we skip it: (a silly fix for now)
					self.collect(myexpand, origfile)
				# we already parsed it, so remove filename from list:
				self.collector = self.collector[1:]
				# reset continuous fail counter, we are making progress:
				contfails = 0
		self.lax=oldlax
		# leftovers are ones that had false conditions, so we don't want to raise an exception:
		#if len(self.collector) != 0:
		#	raise FlexDataError, "Unable to collect all files - uncollected are: "+repr(self.collector)

if __name__ == "__main__":
	coll = collection(debug=False)
	for arg in sys.argv[1:]:
		coll.collect(arg)
	coll.runCollector()
	sys.exit(0)


########NEW FILE########
__FILENAME__ = base
import os, sys, types
from glob import glob

from catalyst_support import MetroError, spawn, spawn_bash

class BaseTarget:
    cmds = {
        "bash": "/bin/bash",
        "chroot": "/usr/bin/chroot",
        "install": "/usr/bin/install",
        "kill": "/bin/kill",
        "linux32": "/usr/bin/linux32",
        "mount": "/bin/mount",
        "rm": "/bin/rm",
    }

    def __init__(self, settings):
        self.settings = settings
        self.env = {}
        self.env["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin"
        self.required_files = []

    def run(self):
        self.check_required_files()
        self.clean_path(recreate=True)
        self.run_script("steps/run")
        self.clean_path()

    def run_script(self, key, chroot=None, optional=False):
        if not self.settings.has_key(key):
            if optional:
                return
            raise MetroError, "run_script: key '%s' not found." % (key,)

        if type(self.settings[key]) != types.ListType:
            raise MetroError, "run_script: key '%s' is not a multi-line element." % (key, )

        print "run_script: running %s..." % key

        os.environ["PATH"] = self.env["PATH"]

        if chroot:
            chrootfile = "/tmp/"+key+".metro"
            outfile = chroot+chrootfile
        else:
            outfile = self.settings["path/tmp"]+"/pid/"+repr(os.getpid())

        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        with open(outfile, "w") as outfd:
            outfd.write("\n".join(self.settings[key]) + "\n")

        os.chmod(outfile, 0755)

        cmds = []
        if chroot:
            if self.settings["target/arch"] == "x86" and os.uname()[4] == "x86_64":
                cmds.append(self.cmds["linux32"])
            cmds.append(self.cmds["chroot"])
            cmds.append(chroot)
            cmds.append(chrootfile)
        else:
            cmds.append(outfile)

        retval = spawn(cmds, env=self.env)
        if retval != 0:
            raise MetroError, "Command failure (key %s, return value %s) : %s" % (key, repr(retval), " ".join(cmds))

        # it could have been cleaned by our outscript, so if it exists:
        if os.path.exists(outfile):
            os.unlink(outfile)

    def target_exists(self, key):
        if self.settings.has_key("metro/options") and "replace" in self.settings["metro/options"].split():
            if os.path.exists(self.settings[key]):
                print "Removing existing file %s..." % self.settings[key]
                self.cmd(self.cmds["rm"] + " -f " + self.settings[key])
            return False
        elif os.path.exists(self.settings[key]):
            print "File %s already exists - skipping..." % self.settings[key]
            return True
        else:
            return False

    def check_required_files(self):
        for loc in self.required_files:
            try:
                matches = glob(self.settings[loc])
            except:
                raise MetroError, "Setting %s is set to %s; glob failed." % (loc, repr(self.settings[loc]))
            if len(matches) == 0:
                raise MetroError, "Required file "+self.settings[loc]+" not found. Aborting."
            elif len(matches) > 1:
                raise MetroError, "Multiple matches found for required file pattern defined in '%s'; Aborting." % loc

    def clean_path(self, path=None, recreate=False):
        if path == None:
            path = self.settings["path/work"]
        if os.path.exists(path):
            print "Cleaning up %s..." % path
        self.cmd(self.cmds["rm"]+" -rf "+path)
        if recreate:
            # This line ensures that the root /var/tmp/metro path has proper 0700 perms:
            self.cmd(self.cmds["install"]+" -d -m 0700 -g root -o root " + self.settings["path/tmp"])
            # This creates the directory we want.
            self.cmd(self.cmds["install"]+" -d -m 0700 -g root -o root "+path)
            # The 0700 perms prevent Metro-generated /tmp directories from being abused by others -
            # because they are world-writeable, they could be used by malicious local users to
            # inject arbitrary data/executables into a Metro build.

    def cmd(self, mycmd, myexc="", badval=None):
        print "Executing \""+mycmd+"\"..."
        try:
            sys.stdout.flush()
            retval = spawn_bash(mycmd, self.env)
            if badval:
                # This code is here because tar has a retval of 1 for non-fatal warnings
                if retval == badval:
                    raise MetroError, myexc
            else:
                if retval != 0:
                    raise MetroError, myexc
        except:
            raise

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = chroot
import os

from catalyst_support import MetroError, ismount

from .base import BaseTarget

class ChrootTarget(BaseTarget):
    def __init__(self, settings):
        BaseTarget.__init__(self, settings)

        # we need a source archive
        self.required_files.append("path/mirror/source")

        # define general linux mount points
        self.mounts = {"/proc": "/proc"}

        if not self.settings.has_key("target/class"):
            return

        okey = "metro/options/"+self.settings["target/class"]

        if not self.settings.has_key(okey):
            return

        options = self.settings[okey].split()

        # define various mount points for our cache support (ccache, binpkgs,
        # genkernel, etc).
        caches = [
            [ "path/cache/compiler", "cache/compiler", "/var/tmp/cache/compiler" ] ,
            [ "path/cache/package", "cache/package", "/var/tmp/cache/package" ] ,
            [ "path/cache/kernel", "cache/kernel", "/var/tmp/cache/kernel" ] ,
            [ "path/cache/probe", "probe", "/var/tmp/cache/probe" ],
        ]

        for key, name, dst in caches:
            if name in options:
                if not self.settings.has_key(key):
                    raise MetroError, "Required setting %s not found (for %s option support)" % (key, name)
                self.mounts[dst] = self.settings[key]

    def run(self):
        if self.target_exists("path/mirror/target"):
            self.run_script("trigger/ok/run", optional=True)
            return

        self.check_required_files()

        # before we clean up - make sure we are unmounted
        self.kill_chroot_pids()
        self.unbind()

        # before we start - clean up any messes
        self.clean_path(recreate=True)

        try:
            self.run_script("steps/unpack")
            self.run_script("steps/unpack/post", optional=True)

            self.bind()

            self.run_script_in_chroot("steps/chroot/prerun", optional=True)
            self.run_script_in_chroot("steps/chroot/run")
            self.run_script_in_chroot("steps/chroot/postrun", optional=True)

            self.unbind()

            self.run_script_in_chroot("steps/chroot/clean", optional=True)
            self.run_script_in_chroot("steps/chroot/test", optional=True)
            self.run_script_in_chroot("steps/chroot/postclean", optional=True)
        except:
            self.kill_chroot_pids()
            self.unbind()
            raise

        self.run_script("steps/capture")
        self.run_script("trigger/ok/run", optional=True)

        self.kill_chroot_pids()
        self.unbind()
        self.clean_path()

    def get_chroot_pids(self):
        cdir = self.settings["path/work"]
        pids = []
        for pid in os.listdir("/proc"):
            if not os.path.isdir("/proc/"+pid):
                continue
            try:
                mylink = os.readlink("/proc/"+pid+"/exe")
            except OSError:
                # not a pid directory
                continue
            if mylink[0:len(cdir)] == cdir:
                pids.append([pid, mylink])
        return pids

    def kill_chroot_pids(self):
        for pid, mylink in self.get_chroot_pids():
            print "Killing process "+pid+" ("+mylink+")"
            self.cmd(self.cmds["kill"]+" -9 "+pid)

    def run_script_in_chroot(self, key, chroot=None, optional=False):
        if chroot == None:
            return self.run_script(key, chroot=self.settings["path/work"], optional=optional)
        else:
            return self.run_script(key, chroot=chroot, optional=optional)

    def bind(self):
        """ Perform bind mounts """
        for dst, src in self.mounts.items():
            if not os.path.exists(src):
                os.makedirs(src, 0755)

            wdst = self.settings["path/work"]+dst
            if not os.path.exists(wdst):
                os.makedirs(wdst, 0755)

            print "Mounting %s to %s ..." % (src, dst)
            if os.system(self.cmds["mount"]+" --bind "+src+" "+wdst) != 0:
                self.unbind()
                raise MetroError, "Couldn't bind mount "+src

    def unbind(self, attempt=0):
        mounts = self.get_active_mounts()
        while len(mounts) != 0:
            # now, go through our dictionary and try to unmound
            progress = 0
            mpos = 0
            while mpos < len(mounts):
                self.cmd("umount "+mounts[mpos], badval=10)
                if not ismount(mounts[mpos]):
                    del mounts[mpos]
                    progress += 1
                else:
                    mpos += 1
            if progress == 0:
                break

        mounts = self.get_active_mounts()
        if len(mounts):
            if attempt >= 3:
                mstring = ""
                for mount in mounts:
                    mstring += mount+"\n"
                raise MetroError, "The following bind mounts could not be unmounted: \n"+mstring
            else:
                attempt += 1
                self.kill_chroot_pids()
                self.unbind(attempt=attempt)

    def get_active_mounts(self):
        # os.path.realpath should ensure that we are comparing the right thing,
        # if something in the path is a symlink - like /var/tmp -> /foo.
        # Because /proc/mounts will store the resolved path (ie.  /foo/metro)
        # not the regular one (ie. /var/tmp/metro)
        prefix = os.path.realpath(self.settings["path/work"])

        # this used to have a "os.popen("mount")" which is not as accurate as
        # the kernel list /proc/mounts.  The "mount" command relies on
        # /etc/mtab which is not necessarily correct.
        with open("/proc/mounts", "r") as myf:
            mounts = [line.split()[1] for line in myf]
            mounts = [mount for mount in mounts if mount.startswith(prefix)]
            return mounts

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = ec2
import os, sys, time, types, glob
import subprocess

import boto.ec2
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

from catalyst_support import MetroError, ismount

from .remote import RemoteTarget

class Ec2Target(RemoteTarget):
    def __init__(self, settings):
        RemoteTarget.__init__(self, settings)

        # ec2 specifics
        self.region = self.settings["ec2/region"]
        self.ec2 = boto.ec2.connect_to_region(self.region)

        if self.settings["target/arch"] == "amd64":
            self.arch = "x86_64"
        else:
            self.arch = "i386"

    def prepare_remote(self):
        if self.settings["target/arch"] not in ["amd64", "x86"]:
            raise MetroError, "EC2 target class only supports x86 targets"

        self.clean_remote()

        self.ec2.create_security_group(self.name, self.name)
        self.ec2.authorize_security_group(group_name=self.name,
                ip_protocol='tcp',
                from_port=22, to_port=22,
                cidr_ip='0.0.0.0/0')

        self.ssh_key_path = "%s/%s.pem" % (self.settings["path/tmp"],
                self.name)

        try:
            os.unlink(self.ssh_key_path)
        except:
            pass

        key_pair = self.ec2.create_key_pair(self.name)
        key_pair.save(self.settings["path/tmp"])

    def clean_remote(self):
        try:
            self.ec2.delete_security_group(self.name)
        except boto.exception.EC2ResponseError:
            pass

        try:
            self.ec2.delete_key_pair(self.name)
        except boto.exception.EC2ResponseError:
            pass

    def start_remote(self):
        self.get_bootstrap_kernel()
        self.get_bootstrap_image()

        # create EBS volume for /mnt/gentoo
        device = BlockDeviceType()
        device.size = self.settings["ec2/instance/device/size"]
        device.delete_on_termination = True

        mapping = BlockDeviceMapping()
        self.root_device = "/dev/" + self.settings["ec2/instance/device/name"]
        mapping[self.root_device] = device

        # start bootstrapping instance
        reservation = self.ec2.run_instances(self.bootstrap_image.id,
                kernel_id=self.bootstrap_kernel.id,
                instance_type=self.settings["ec2/instance/type"],
                security_groups=[self.name],
                key_name=self.name,
                block_device_map=mapping)

        self.instance = reservation.instances[0]

        sys.stdout.write("waiting for instance to come up ..")
        while self.instance.update() != 'running':
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(5)
        sys.stdout.write("\n")
        time.sleep(120)

        self.ssh_uri = "ec2-user@" + self.instance.public_dns_name
        self.remote_upload_path = "/tmp"

        # enable sudo without a tty
        cmd = "sudo sed -i -e '/requiretty/d' /etc/sudoers"
        cmd = ["ssh", "-t"] + self.ssh_options() + [self.ssh_uri, cmd]
        ssh = subprocess.Popen(cmd)
        ssh.wait()

        self.run_script_at_remote("steps/remote/postboot")

    def wait_for_shutdown(self):
        sys.stdout.write("waiting for instance to shutdown ..")
        while self.instance.update() != 'stopped':
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(5)
        sys.stdout.write("\n")

    def capture(self):
        volume = self.ec2.get_all_volumes(filters={
            'attachment.instance-id': self.instance.id,
            'attachment.device': self.root_device,
        })[0]

        snapshot = self.ec2.create_snapshot(volume.id)

        sys.stdout.write("waiting for snapshot to complete ..")
        while snapshot.status != 'completed':
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(5)
            snapshot.update()
        sys.stdout.write("\n")

        # create EBS mapping
        device = BlockDeviceType()
        device.snapshot_id = snapshot.id

        mapping = BlockDeviceMapping()
        mapping['/dev/sda'] = device

        self.get_instance_kernel()
        image = self.ec2.register_image(name=self.name, description=self.name,
                architecture=self.arch, kernel_id=self.instance_kernel.id,
                root_device_name='/dev/sda', block_device_map=mapping)

        if self.settings["target/permission"] == "public":
            self.ec2.modify_image_attribute(image, groups='all')

        with open(self.settings["path/mirror/target"], "w") as fd:
            cmd = [
                "ec2-run-instances",
                "--region", self.region,
                "--instance-type", "t1.micro",
                image,
            ]
            fd.write(" ".join(cmd))
            fd.write("\n")

    def destroy_remote(self):
        if hasattr(self, 'instance'):
            self.ec2.terminate_instances([self.instance.id])

    def get_bootstrap_kernel(self):
        kernels = self.ec2.get_all_images(owners=['amazon'], filters={
            'image-type': 'kernel',
            'architecture': self.arch,
            'manifest-location': '*pv-grub-hd0_*'
        })

        self.bootstrap_kernel = sorted(kernels, key=lambda k: k.location)[-1]
        print "bootstrap kernel-id: " + self.bootstrap_kernel.id

    def get_instance_kernel(self):
        kernels = self.ec2.get_all_images(owners=['amazon'], filters={
            'image-type': 'kernel',
            'architecture': self.arch,
            'manifest-location': '*pv-grub-hd00_*'
        })

        self.instance_kernel = sorted(kernels, key=lambda k: k.location)[-1]
        print "instance kernel-id: " + self.instance_kernel.id

    def get_bootstrap_image(self):
        images = self.ec2.get_all_images(filters={
            'image-type': 'machine',
            'architecture': self.arch,
            'manifest-location': 'amazon/amzn-ami-*',
            'root-device-type': 'ebs',
            'virtualization-type': 'paravirtual',
            'kernel-id': self.bootstrap_kernel.id
        })

        self.bootstrap_image = images[-1]
        print "bootstrap image-id: " + self.bootstrap_image.id

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = remote
import os, sys, time, types, glob
import subprocess

from catalyst_support import MetroError

from .base import BaseTarget

class RemoteTarget(BaseTarget):
    def __init__(self, settings):
        BaseTarget.__init__(self, settings)

        self.required_files.append("path/mirror/source")
        self.required_files.append("path/mirror/snapshot")

        # vm config
        self.name = self.settings["target/name"]

    def run(self):
        if self.target_exists("path/mirror/target"):
            self.run_script("trigger/ok/run", optional=True)
            return

        self.check_required_files()
        self.prepare_remote()

        # before we start - clean up any messes
        self.destroy_remote()
        self.clean_path(recreate=True)

        try:
            self.start_remote()
            self.upload_file(glob.glob(self.settings["path/mirror/source"])[0])
            self.upload_file(glob.glob(self.settings["path/mirror/snapshot"])[0])
            self.run_script_at_remote("steps/remote/run")
        except:
            self.destroy_remote()
            self.clean_remote()
            raise

        self.wait_for_shutdown()
        self.capture()
        self.run_script("trigger/ok/run", optional=True)

        self.destroy_remote()
        self.clean_remote()
        self.clean_path()

    def ssh_options(self):
        os.chmod(self.ssh_key_path, 0400)
        return [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "GlobalKnownHostsFile=/dev/null'",
            "-i", self.ssh_key_path,
            "-q"
        ]

    def ssh_pipe_to_remote(self, cmd, scp=False):
        cmd = ["ssh"] + self.ssh_options() + [self.ssh_uri, cmd]
        return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=sys.stdout)

    def run_script_at_remote(self, key, optional=False):
        if not self.settings.has_key(key):
            if optional:
                return
            raise MetroError, "run_script: key '%s' not found." % (key,)

        if type(self.settings[key]) != types.ListType:
            raise MetroError, "run_script: key '%s' is not a multi-line element." % (key, )

        print "run_script_at_remote: running %s..." % key

        ssh = self.ssh_pipe_to_remote("sudo -i /bin/bash -s")
        ssh.stdin.write("\n".join(self.settings[key]))
        ssh.stdin.close()
        ssh.wait()

        if ssh.returncode != 0:
            raise MetroError, "Command failure (key %s, return value %s)" % (key, repr(ssh.returncode))

    def upload_file(self, src_path):
        dst_path = "%s:%s/%s" % (self.ssh_uri, self.remote_upload_path,
                os.path.basename(src_path))

        print "Uploading %s to %s" % (src_path, dst_path)

        cmd = ["scp"] + self.ssh_options() + [src_path, dst_path]
        ssh = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=sys.stdout)
        ssh.stdin.close()
        ssh.wait()

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = snapshot
from .base import BaseTarget

class SnapshotTarget(BaseTarget):
    def __init__(self, settings):
        BaseTarget.__init__(self, settings)

    def run(self):
        if not self.target_exists("path/mirror/snapshot"):
            BaseTarget.run(self)
        self.run_script("trigger/ok/run", optional=True)


# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = stage
from .chroot import ChrootTarget

class StageTarget(ChrootTarget):
    def __init__(self, settings):
        ChrootTarget.__init__(self, settings)

        # stages need a snapshot to install packages
        self.required_files.append("path/mirror/snapshot")

        # define gentoo specific mounts
        if self.settings.has_key("path/distfiles"):
            self.mounts["/usr/portage/distfiles"] = self.settings["path/distfiles"]

        # let's bind-mount our main system's device nodes in place
        #if self.settings["portage/ROOT"] != "/":
            # this seems to be needed for libperl to build (x2p) during stage1
        #    self.mounts["/dev"] = "/dev"
        #    self.mounts["/dev/pts"] = "/dev/pts"

    def run(self):
        ChrootTarget.run(self)

        # now, we want to clean up our build-related caches, if configured to do so:
        if self.settings.has_key("metro/options"):
            if "clean/auto" in self.settings["metro/options"].split():
                if self.settings.has_key("path/cache/build"):
                    self.clean_path(self.settings["path/cache/build"])

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = virtualbox
import os, sys, time, types, glob
import subprocess

from catalyst_support import MetroError, ismount

from .remote import RemoteTarget

class VirtualboxTarget(RemoteTarget):
    def __init__(self, settings):
        RemoteTarget.__init__(self, settings)

        # virtualbox specifics
        self.required_files.append("path/mirror/generator")
        self.basedir = self.settings["path/work"]+"/vm"

        self.cmds["modprobe"] = "/sbin/modprobe"
        self.cmds["vbox"] = "/usr/bin/VBoxManage"

        self.ssh_uri = "root@10.99.99.2"
        self.remote_upload_path = "/tmp"

        if self.settings["target/arch"] == "amd64":
            self.ostype = "Gentoo_64"
        else:
            self.ostype = "Gentoo"

    def prepare_remote(self):
        if self.settings["target/arch"] not in ["amd64", "x86"]:
            raise MetroError, "VirtualBox target class only supports x86 targets"

        for mod in ["vboxdrv", "vboxpci", "vboxnetadp", "vboxnetflt"]:
            self.cmd(self.cmds["modprobe"]+" "+mod)

        self.ssh_key_path = self.settings["path/config"]+"/keys/vagrant"

    def clean_remote(self):
        pass

    def start_remote(self):
        # create vm
        self.vbm("createvm --name %s --ostype %s --basefolder '%s' --register" % (self.name, self.ostype, self.basedir))
        self.vbm("modifyvm %s --rtcuseutc on --boot1 disk --boot2 dvd --boot3 none --boot4 none" % (self.name))
        self.vbm("modifyvm %s --memory %s" % (self.name, self.settings["virtualbox/memory"]))
        self.vbm("modifyvm %s --vrde on --vrdeport 3389 --vrdeauthtype null" % (self.name))

        # create hard drive
        self.vbm("createhd --filename '%s/%s.vdi' --size $((%s*1024)) --format vdi" % (self.basedir, self.name, self.settings["virtualbox/hddsize"]))
        self.vbm("storagectl %s --name 'SATA Controller' --add sata --controller IntelAhci --bootable on --sataportcount 2" % (self.name))
        self.vbm("storageattach %s --storagectl 'SATA Controller' --type hdd --port 0 --medium '%s/%s.vdi'" % (self.name, self.basedir, self.name))

        # attach generator
        self.vbm("storageattach %s --storagectl 'SATA Controller' --type dvddrive --port 1 --medium '%s'" % (self.name, self.settings["path/mirror/generator"]))

        # create hostonly network
        ifcmd = self.cmds["vbox"]+" hostonlyif create 2>/dev/null | /bin/egrep -o 'vboxnet[0-9]+'"
        self.ifname = subprocess.check_output(ifcmd, shell=True).strip()
        self.vbm("hostonlyif ipconfig %s --ip 10.99.99.1" % (self.ifname,))
        self.cmd("ip link set %s up" % (self.ifname,))

        # setup vm networking
        self.vbm("modifyvm %s --nic1 nat --nic2 hostonly" % (self.name))
        self.vbm("modifyvm %s --hostonlyadapter2 %s" % (self.name, self.ifname))

        # start the vm
        self.vbm("startvm %s --type headless" % (self.name))

        # 60 seconds should be enough to boot
        # a better heuristic would be nice though
        time.sleep(60)

    def wait_for_shutdown(self):
        sys.stdout.write("Waiting for VM to shutdown .")
        check_cmd = self.cmds["vbox"]+" list runningvms | /bin/fgrep -o "+self.name

        while True:
            sys.stdout.write(".")
            try:
                subprocess.check_output(check_cmd, shell=True)
            except subprocess.CalledProcessError:
                sys.stdout.write(" done\n")
                break
            time.sleep(1)

        time.sleep(60)

    def capture(self):
        self.run_script("steps/capture")

    def destroy_remote(self):
        try:
            self.vbm("controlvm %s poweroff && sleep 5" % (self.name))
        except:
            pass

        # determine virtual network if we don't have it
        if not hasattr(self, "ifname"):
            ifcmd = self.cmds["vbox"]+" list hostonlyifs|grep -B3 10.99.99.1|head -n1|awk '{print $2}'"
            self.ifname = subprocess.check_output(ifcmd, shell=True).strip()

        try:
            self.vbm("unregistervm %s --delete" % (self.name))
        except:
            pass

        try:
            self.vbm("hostonlyif remove %s" % (self.ifname))
        except:
            pass

    def vbm(self, cmd):
        self.cmd(self.cmds["vbox"]+" "+cmd)

# vim: ts=4 sw=4 et

########NEW FILE########
__FILENAME__ = db
#!/usr/bin/python2

'''

This module is a fourth attempt at some clean design patterns for encapsulating
SQLAlchemy database objects, so that they can more easily be embedded in other
objects. This code takes advantage of the SQLAlchemy ORM but purposely DOES NOT
USE SQLAlchemy's declarative syntax.  This is intentional because I've come to
the conclusion (after using declarative for a long time) that it's a pain in
the butt, not well documented, and hides a lot of the power of SQLAlchemy, so
it's a liability to use it.

Instead of using a declarative_base, database objects are simply derived from
object,and contain a _mapTable() method.  This method creates the Table object
and maps this new table to the class. This method is called by the Database
object when it is initialized:

orm = Database([User])

Above, we create a new Database object (to hold metadata, engine and session
information,) and we pass it a list or tuple of all objects to include as part
of our Database. Above, when Database's __init__() method is called, it will ensure
that the User class' _mapTable() method is called, so that the User table is
associated with our Database, and that these tables are created in the underlying
metadata.

This design pattern is created to allow for the creation of a library of
different kinds of database-aware objects, such as our user object. Then, other
code can import this code, and create a database schema with one or more of
these objects very easily:

orm = Database([Class1, Class2, Class3])

Classes that should be part of the Database can be included, and those that we
don't want can be omitted.

We could also create two or more schemas:

user_db = Database([User])
user_db.associate(engine="sqlite:///users.db")

product_db = Database([Product, ProductID, ProductCategory])
product_db.associate(engine="sqlite:///products.db")

tmp_db = Database([TmpObj, TmpObj2])
tmp_db.associate(engine="sqlite:///:memory:")

Or two different types of User objects:

class OtherUser(User):
	pass

user_db = Database([User])
other_user_db = Database([OtherUser])

Since all the session, engine and metadata stuff is encapsulated inside the
Database instances, this makes it a lot easier to use multiple database engines
from the same source code. At least, it provides a framework to make this a lot
less confusing:

for u in userdb.session.Query(User).all():
	print u

'''
import logging
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.orderinglist import ordering_list

logging.basicConfig(level=logging.DEBUG)

class DatabaseError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return self.value

'''
dbobject is a handy object to use as a base class for your database-aware objects. However,
using it is optional. It is perfectly OK to subclass a standard python new-style object.
'''

class dbobject(object):
	def __init__(self,id=None):
		self.id = id
	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, self.id)
	@classmethod
	def _mapTable(cls,db):
		mapper(cls, cls.__table__, primary_key=[cls.__table__.c.id])

class Database(object):

	def __init__(self,objs=[],engine=None):
		self._dbobj = objs 
		self._tables = {}
		self.engine = None
		self._session = None
		self._autodict = {}
		self.metadata = MetaData()
		self.sessionmaker = None
		if engine != None:
			self.associate(engine)

	def autoName(self,name):
		if name not in self._autodict:
			self._autodict[name] = 0
		self._autodict[name] += 1
		return name % self._autodict[name]
	
	def IntegerPrimaryKey(self,name):
		return Column(name, Integer, Sequence(self.autoName("id_seq_%s"), optional=True), primary_key=True)

	def UniqueString(self,name,length=80,index=True, nullable=False):
		return Column(name, String(length), unique=True, index=index, nullable=nullable)

	def associate(self,engine="sqlite:///:memory:"):
		self.engine = create_engine(engine)
		self.metadata.bind = self.engine
		self.initORM()
		self.initSession()
		self.createDatabaseTables()

	def initORM(self):
		for cls in self._dbobj:
			cls._makeTable(self)
		for cls in self._dbobj:
			cls._mapTable(self)

	def createDatabaseTables(self):
		self.metadata.create_all()

	def initSession(self):
		self.sessionmaker = sessionmaker(bind=self.engine)

	@property
	def session(self):
		if self.sessionmaker == None:
			raise DatabaseError("Database not associated with engine")
		if self._session == None:
			self._session = scoped_session(self.sessionmaker)
		return self._session


########NEW FILE########
