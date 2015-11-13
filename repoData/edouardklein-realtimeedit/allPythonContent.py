__FILENAME__ = RTEAgent
#!/usr/bin/env python3
import os
import logging
import subprocess

mount_tmpfs_command = r'diskutil erasevolume HFS+ "ramdisk" `hdiutil attach -nomount ram://1165430`' # from http://osxdaily.com/2007/03/23/create-a-ram-disk-in-mac-os-x/
umount_tmpfs_command = r'umount /Volumes/ramdisk && hdiutil detach /dev/disk1' #make disk1 a variable, it is not always disk1
#mount_tmpfs_command = "/home/edouard/Documents/relatimeedit/linux/mount_tmpfs.sh"
#umount_tmpfs_command = "//home/edouard/Documents/relatimeedit/linux/umount_tmpfs.sh"

class RTEAgent:

    def __init__( self, cwd=os.getcwd(), compileCmd="make RTEcompile", firstViewCmd="make RTEstartView", viewCmd="make RTEview", stopViewCmd="make RTEstopView", ramdisk="/Volumes/ramdisk" ):
        self.cwd = cwd
        self.compileCmd = compileCmd
        self.ramdisk = ramdisk
        self.firstViewCmd = firstViewCmd
        self.viewCmd = viewCmd
        self.stopViewCmd = stopViewCmd
        self.cdToRamdiskCmd = "cd "+self.ramdisk+" && "
        logging.debug("Mounting the ramdisk")
        self.mountRamDisk()
        logging.debug("Copying to ramdisk")
        self.cpyWDtoRamdisk()
        logging.debug("First compilation and view")
        logging.info( "Running : "+self.cdToRamdiskCmd+self.compileCmd+"&&"+self.firstViewCmd)
        subprocess.Popen(self.cdToRamdiskCmd+self.compileCmd+" && "+self.firstViewCmd, shell=True )
        logging.info("Done")

    def __del__(self):
        self.umountRamDisk()
        
    def input( self, filename, contents ):
        logging.info("Input received on "+filename+", compiling")
        #logging.debug("contents :"+contents)
        f = open(self.ramdisk+'/'+filename, "wb")
        f.write(contents)
        f.close()
        try:
            logging.info( "Running : "+self.cdToRamdiskCmd+self.compileCmd)
            subprocess.check_output( self.cdToRamdiskCmd+self.compileCmd, shell=True,stderr=subprocess.STDOUT )
            logging.info("Compilation succeeded")
        except subprocess.CalledProcessError as err:
            logging.info("Failure with error :"+err.output)
            return err.returncode, err.output
        logging.debug( "Running : "+self.cdToRamdiskCmd+self.viewCmd)
        subprocess.check_output( self.cdToRamdiskCmd+self.viewCmd, shell=True ) #Voluntarily uncaught exception, there should be no error there
        logging.debug("done")
        return 0

    def mountRamDisk(self):
        #FIXME: gracefully handling permissions would be nice
        #FIXME: A way to change the size of the ramdisk would be nice
        logging.debug("Ramdisk command : "+mount_tmpfs_command)
        subprocess.check_call(mount_tmpfs_command,shell=True)

    def umountRamDisk(self):
        #FIXME: gracefully handling permissions would be nice
        #FIXME: A way to change the size of the ramdisk would be nice
        subprocess.check_call(self.stopViewCmd+"&& sleep 1",shell=True)
        subprocess.check_call(umount_tmpfs_command, shell=True)#+" "+self.ramdisk ,shell=True)

    def cpyWDtoRamdisk( self ):
        subprocess.check_call("cp -r "+self.cwd+"/* "+self.ramdisk+"/", shell=True)
        
        

########NEW FILE########
__FILENAME__ = RTEFS
#!/usr/bin/env python3

import logging
import sys
sys.path+=['..']
from RTEAgent import *
import threading

from collections import defaultdict
from errno import ENOENT,EACCES
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, Operations, LoggingMixIn, FuseOSError

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class RTEAThread( threading.Thread ):
    def __init__( self, rteFS, rteAgent,filename, contents ):
        threading.Thread.__init__(self)
        self.rteFS = rteFS
        self.rteAgent = rteAgent
        self.filename = filename
        self.contents = contents
    def run( self ):
        logging.debug("Compile thread compiling, from change in file "+self.filename)
        self.rteAgent.input( self.filename, self.contents )
        self.rteFS.files['/input']['st_mode'] = (S_IFDIR | 0o777)
        logging.debug("Compile thread finished")
        
class RTEFS(LoggingMixIn, Operations):
    'FS for control of the Real-Time Editing agent, drawing from the fusepy Example memory filesystem.'

    def __init__(self, agent):
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0o777), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)
        self.files['/input'] = dict(st_mode=(S_IFDIR | 0o777), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)
        self.agent = agent
        
    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        if path[0:7] == "/input/":
            st = os.lstat(agent.cwd + path[6:])
            self.files[path] = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                            'st_gid', 'st_mode', 'st_mtime', 'st_nlink',
                                                            'st_size', 'st_uid'))
            return self.files[path]
        if path not in self.files:
            raise OSError(ENOENT)

        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        return ['.', '..'] + [x[1:] for x in self.files if x != '/']

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0o777), st_nlink=1,
                                  st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)

    def release( self, path, fh ):
        #logging.debug("Releasing path : "+path)
        #logging.debug("Data at the end of interaction is :"+self.data[path])
        if path[0:7] == '/input/':
            #logging.debug("input file written, let's launch the whole shebang")
            #Input file written
            #We remove writing rights to /input/ to prevent further editing
            self.files['/input']['st_mode'] = (S_IFDIR | 0000)
            #We launch the thread that will give them back
            RTEAThread( self, self.agent,path[7:],self.data[path] ).start()
            #TODO: We should check if a previous compilation is still running
            #logging.debug("thread started, returning")
        #Give back control to user
        return 0

    def access( self, path, mode ):
        logging.debug("Calling access on "+path)
        if path[0:6] == '/input':
            logging.debug("Checking wether /input can be accessed")
            if self.files['/input']['st_mode'] == (S_IFDIR | 0000):
                logging.debug("Nope")
                raise FuseOSError(EACCES)
            logging.debug("Yep")
        return 0
        


    
if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.getLogger().setLevel(logging.INFO) #Or DEBUG ...
    logging.debug("Launching the agent")
    agent = RTEAgent()
    fuse = FUSE(RTEFS( agent ), argv[1], foreground=True,auto_xattr=True)
    


########NEW FILE########
__FILENAME__ = GradientDescent
from numpy import * #FIXME:Normaliser les imports de numpy et scipy
import scipy.linalg
import os
import sys
class GradientDescent:
   def alpha( self, t ):
      raise NotImplementedError, "Cannot call abstract method"
   theta_0=array([])
   Threshold = 'a'
   T = -1
   sign = 0
   def run( self, f_grad, f_proj=None, b_norm=False ): #grad is a function of theta
      theta = self.theta_0.copy()
      best_theta = theta.copy()
      best_norm = 1000000.#FIXME:Il faudrait mettre plus l'infini
      best_iter = 0
      t=-1
      while True:#Do...while loop
         t += 1
         DeltaTheta = self.sign * self.alpha( t ) * f_grad( theta )
         norm = scipy.linalg.norm( DeltaTheta )
         if b_norm and  norm > 0.:
             DeltaTheta /= scipy.linalg.norm( DeltaTheta )
         theta = theta + DeltaTheta
         if f_proj:
             theta = f_proj( theta )
         sys.stderr.write("Norme du gradient : "+str(norm)+", pas : "+str(self.alpha(t))+", iteration : "+str(t)+"\n")
         if norm < best_norm:
             best_norm = norm
             best_theta = theta.copy()
             best_iter = t
         if norm < self.Threshold or (self.T != -1 and t >= self.T):
             break
      sys.stdout.write("Gradient de norme : "+str(best_norm)+", a l'iteration : "+str(best_iter)+"\n")
      return best_theta

########NEW FILE########
__FILENAME__ = GradientDescent_test
from numpy import * #FIXME:Normaliser les imports de numpy et scipy
import scipy
from GradientDescent import *


## function being optimized : x->x^2
class TestGD( GradientDescent ):
    def alpha( self, t ):
        return 1./(10*t+1)
    theta_0 = array( [1067] )
    Threshold = 0.001
    T = 100
    sign = -1

def grad( theta ):
    return 2*theta[0]

x = 0
print "Vanilla :"
test = TestGD()
x = test.run( grad )
print x    

print "Normalise :"
test = TestGD()
#test.T = -1
x = test.run( grad,b_norm=True )
print x    

print "Projete et normalise"
test = TestGD()
#test.T = -1
def proj( x ):
    if x == 0:
        return array([1.])
    return x / scipy.linalg.norm( x )
x = test.run( grad, f_proj=proj, b_norm=True )
print x    

print "Vanilla projete"
test = TestGD()
#test.T = -1
x = test.run( grad, f_proj=proj )
print x    

## function being optimized : x->||x||_2
class TestGD2( GradientDescent ):
    def alpha( self, t ):
        return 1./(t+1)
    theta_0 = array( [1067,455,-660] )
    Threshold = 0.001
    T = 100
    sign = -1

def grad( theta ):
    return 2*theta

print "Vanilla :"
test = TestGD2()
x = test.run( grad )
print x    

print "Normalise :"
test = TestGD2()
#test.T = -1
x = test.run( grad,b_norm=True )
print x    

print "Projete et normalise"
test = TestGD2()
#test.T = -1
def proj( x ):
    if scipy.linalg.norm( x ) == 0:
        return array([1.,0.,0.])
    return x / scipy.linalg.norm( x )
x = test.run( grad, f_proj=proj, b_norm=True )
print x

print "Vanilla projete"
test = TestGD2()
#test.T = -1
x = test.run( grad, f_proj=proj )
print x    


print "Projete et normalise (2eme type)"
test = TestGD2()
#test.T = -1
def proj2( x ):
    if scipy.linalg.norm( x ) == 0:
        return array([1.,0.,0.])
    x[0] = 1.
    return x
x = test.run( grad, f_proj=proj2, b_norm=True )
print x

print "Vanilla projete (2eme type)"
test = TestGD2()
#test.T = -1
x = test.run( grad, f_proj=proj2 )
print x    



########NEW FILE########
__FILENAME__ = testRTEAgent
#!/usr/bin/env python3

#This test checks that the RTEAgent can use the ramdisk and actually compile and view the examples it is given.
#This test do not use the Fuse filesystem, nor do we need a text editor
from RTEAgent import *
logging.getLogger().setLevel(logging.DEBUG)


f = open( "main1.tex",'r')
main1 = f.read()
f.close()
f = open( "main2.tex",'r')
main2 = f.read()
f.close()
f = open( "main3.tex",'r')
main3 = f.read()
f.close()
agent = RTEAgent()
var = input("Enter something: ")
print("Testing to put main1.tex contents in main")
agent.input("main.tex",main1)
var = input("Enter something: ")
print("main 2....")
agent.input("main.tex",main2)
var = input("Enter something: ")
print("main 3...")
agent.input("main.tex",main3)

########NEW FILE########
