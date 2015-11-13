__FILENAME__ = filesize
'''
hurry.filesize

@author: Martijn Faassen, Startifact
@license: ZPL 2.1
'''

traditional = [
    (1024 ** 5, 'P'),
    (1024 ** 4, 'T'),
    (1024 ** 3, 'G'),
    (1024 ** 2, 'M'),
    (1024 ** 1, 'K'),
    (1024 ** 0, 'B'),
    ]

alternative = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'),
    (1024 ** 3, ' GB'),
    (1024 ** 2, ' MB'),
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
    ]

verbose = [
    (1024 ** 5, (' petabyte', ' petabytes')),
    (1024 ** 4, (' terabyte', ' terabytes')),
    (1024 ** 3, (' gigabyte', ' gigabytes')),
    (1024 ** 2, (' megabyte', ' megabytes')),
    (1024 ** 1, (' kilobyte', ' kilobytes')),
    (1024 ** 0, (' byte', ' bytes')),
    ]

iec = [
    (1024 ** 5, 'Pi'),
    (1024 ** 4, 'Ti'),
    (1024 ** 3, 'Gi'),
    (1024 ** 2, 'Mi'),
    (1024 ** 1, 'Ki'),
    (1024 ** 0, ''),
    ]

si = [
    (1000 ** 5, 'P'),
    (1000 ** 4, 'T'),
    (1000 ** 3, 'G'),
    (1000 ** 2, 'M'),
    (1000 ** 1, 'K'),
    (1000 ** 0, 'B'),
    ]



def size(bytes, system=traditional):
    """Human-readable file size.

    Using the traditional system, where a factor of 1024 is used::

    >>> size(10)
    '10B'
    >>> size(100)
    '100B'
    >>> size(1000)
    '1000B'
    >>> size(2000)
    '1K'
    >>> size(10000)
    '9K'
    >>> size(20000)
    '19K'
    >>> size(100000)
    '97K'
    >>> size(200000)
    '195K'
    >>> size(1000000)
    '976K'
    >>> size(2000000)
    '1M'

    Using the SI system, with a factor 1000::

    >>> size(10, system=si)
    '10B'
    >>> size(100, system=si)
    '100B'
    >>> size(1000, system=si)
    '1K'
    >>> size(2000, system=si)
    '2K'
    >>> size(10000, system=si)
    '10K'
    >>> size(20000, system=si)
    '20K'
    >>> size(100000, system=si)
    '100K'
    >>> size(200000, system=si)
    '200K'
    >>> size(1000000, system=si)
    '1M'
    >>> size(2000000, system=si)
    '2M'

    """
    for factor, suffix in system:
        if bytes >= factor:
            break
    amount = int(bytes/factor)
    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

########NEW FILE########
__FILENAME__ = ThreadPool
'''
ThreadPool Implementation

@author: Morten Holdflod Moeller - morten@holdflod.dk
@license: LGPL v3 
'''

from __future__ import with_statement
from threading import Thread, RLock
from time import sleep
from Queue import Queue, Empty
import logging
import sys

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = sys.stderr
logging.getLogger('threadpool').addHandler(h)
logging.getLogger('threadpool.worker').addHandler(h)



class ThreadPoolMixIn:
    """Mix-in class to handle each request in a new thread from the ThreadPool."""

    def __init__(self, threadpool=None):
        if (threadpool == None):
            threadpool = ThreadPool()
            self.__private_threadpool = True
        else:
            self.__private_threadpool = False
        
        self.__threadpool = threadpool

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.

        In addition, exception handling is done here.

        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address) #IGNORE:W0702
            self.close_request(request)

    def process_request(self, request, client_address):
        self.__threadpool.add_job(self.process_request_thread, [request, client_address])      

    def shutdown(self):
        if (self.__private_threadpool): self.__threadpool.shutdown()
        

class AddJobException(Exception):
    '''
    Exceptoion raised when a Job could not be added
    to the queue
    '''
    def __init__(self, msg):
        Exception.__init__(self, msg)
    

class ThreadPool:
    '''
    The class implementing the ThreadPool.
    
    Instantiate and add jobs using add_job(func, args_list) 
    '''

    class Job: #IGNORE:R0903
        '''
        Class encapsulating a job to be handled
        by ThreadPool workers 
        '''
        def __init__(self, function, args, return_callback=None):
            self.callable = function
            self.arguments = args
            self.return_callback = return_callback
            
        def execute(self):
            '''
            Called to execute the function
            '''
            try:
                return_value = self.callable(*self.arguments) #IGNORE:W0142
            except Exception, excep: #IGNORE:W0703
                logger = logging.getLogger("threadpool.worker")
                logger.warning("A job in the ThreadPool raised an exception: " + excep)
                #else do nothing cause we don't know what to do...
                return 
                    
            try:
                if (self.return_callback != None):
                    self.return_callback(return_value)
            except Exception, _: #IGNORE:W0703 everything could go wrong... 
                logger = logging.getLogger('threadpool')
                logger.warning('Error while delivering return value to callback function')

    class Worker(Thread):
        '''
        A worker thread handling jobs in the thread pool 
        job queue
        '''
        
        def __init__(self, pool):
            Thread.__init__(self)
            
            if (not isinstance(pool, ThreadPool)):
                raise TypeError("pool is not a ThreadPool instance")
            
            self.pool = pool
            
            self.alive = True
            self.start()
                
        def run(self):
            '''
            The workers main-loop getting jobs from queue 
            and executing them
            '''
            while self.alive:
                #print self.pool.__active_worker_count,  self.pool.__worker_count
                job = self.pool.get_job()
                if (job != None):
                    self.pool.worker_active()
                    job.execute()
                    self.pool.worker_inactive()
                else:
                    self.alive = False
                
            self.pool.punch_out()
                       
    def __init__(self, max_workers = 5, kill_workers_after = 3):
        if (not isinstance(max_workers, int)):
            raise TypeError("max_workers is not an int")
        if (max_workers < 1):
            raise ValueError('max_workers must be >= 1')
        
        if (not isinstance(kill_workers_after, int)):
            raise TypeError("kill_workers_after is not an int")
        
        self.__max_workers = max_workers
        self.__kill_workers_after = kill_workers_after
        
        # This Queue is assumed Thread Safe
        self.__jobs = Queue()
                      
        self.__worker_count_lock = RLock() 
        self.__worker_count = 0
        self.__active_worker_count = 0
        
        self.__shutting_down = False
        logger = logging.getLogger('threadpool')
        logger.info('started')
    
    def shutdown(self,  wait_for_workers_period = 1, clean_shutdown_reties = 5):
        if (not isinstance(clean_shutdown_reties, int)):
            raise TypeError("clean_shutdown_reties is not an int")
        if (not clean_shutdown_reties >= 0):
            raise ValueError('clean_shutdown_reties must be >= 0')
        
        if (not isinstance(wait_for_workers_period, int)):
            raise TypeError("wait_for_workers_period is not an int")
        if (not wait_for_workers_period >= 0):
            raise ValueError('wait_for_workers_period must be >= 0')
        
        logger = logging.getLogger("threadpool")
        logger.info("shutting down")
        
        with self.__worker_count_lock:
            self.__shutting_down = True
            self.__max_workers = 0
            self.__kill_workers_after = 0
        
        retries_left = clean_shutdown_reties
        while (retries_left > 0):
            
            with self.__worker_count_lock:
                logger.info("waiting for workers to shut down (%i), %i workers left"%(retries_left, self.__worker_count))
                if (self.__worker_count > 0):
                    retries_left -= 1
                else:
                    retries_left = 0
                    
                sleep(wait_for_workers_period)
        
        
        with self.__worker_count_lock:
            if (self.__worker_count > 0):
                logger.warning("shutdown stopped waiting. Still %i active workers"%self.__worker_count)
                clean_shutdown = False
            else:
                clean_shutdown = True
            
        logger.info("shutdown complete")
        
        return clean_shutdown
    
    def punch_out(self):
        '''
        Called by worker to update worker count 
        when the worker is shutting down
        '''
        with self.__worker_count_lock:
            self.__worker_count -= 1
        
    def __new_worker(self):
        '''
        Adding a new worker thread to the thread pool
        '''
        with self.__worker_count_lock:
            ThreadPool.Worker(self)
            self.__worker_count += 1
        
    def worker_active(self):
        with self.__worker_count_lock:
            self.__active_worker_count = self.__active_worker_count + 1
            
    def worker_inactive(self):
        with self.__worker_count_lock:
            self.__active_worker_count = self.__active_worker_count - 1
        
    def add_job(self, function, args = None, return_callback=None):
        '''
        Put new job into queue
        '''
        
        if (not callable(function)):
            raise TypeError("function is not a callable")
        if (not ( args == None or isinstance(args, list))):
            raise TypeError("args is not a list")
        if (not (return_callback == None or callable(return_callback))):
            raise TypeError("return_callback is not a callable")
                
        if (args == None):
            args = []
        
        job = ThreadPool.Job(function, args, return_callback)
        
        with self.__worker_count_lock:
            if (self.__shutting_down):
                raise AddJobException("ThreadPool is shutting down")
            
            try:
                start_new_worker = False
                if (self.__worker_count < self.__max_workers):
                    if (self.__active_worker_count == self.__worker_count):
                        start_new_worker = True
                        
                self.__jobs.put(job)
                
                if (start_new_worker): 
                    self.__new_worker()
                    
            except Exception:
                raise AddJobException("Could not add job")
        
    
    def get_job(self):
        '''
        Retrieve next job from queue 
        workers die (and should) when 
        returning None  
        '''
        
        job = None
        try:
            if (self.__kill_workers_after < 0):
                job = self.__jobs.get(True)
            elif (self.__kill_workers_after == 0):
                job = self.__jobs.get(False)
            else:
                job = self.__jobs.get(True, self.__kill_workers_after)
        except Empty:
            job = None
        
        return job

########NEW FILE########
__FILENAME__ = trimage
#!/usr/bin/python
import time
import sys
import errno
from os import listdir
from os import path
from os import remove
from os import access
from os import W_OK as WRITEABLE
from shutil import copy
from subprocess import call, PIPE
from optparse import OptionParser

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from filesize import *
from imghdr import what as determinetype

from Queue import Queue
from ThreadPool import ThreadPool
from multiprocessing import cpu_count

from ui import Ui_trimage

VERSION = "1.0.5"


class StartQT4(QMainWindow):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_trimage()
        self.ui.setupUi(self)

        self.showapp = True
        self.verbose = True
        self.imagelist = []

        QCoreApplication.setOrganizationName("Kilian Valkhof")
        QCoreApplication.setOrganizationDomain("trimage.org")
        QCoreApplication.setApplicationName("Trimage")
        self.settings = QSettings()
        self.restoreGeometry(self.settings.value("geometry").toByteArray())

        # check if apps are installed
        if self.checkapps():
            quit()

        #add quit shortcut
        if hasattr(QKeySequence, "Quit"):
            self.quit_shortcut = QShortcut(QKeySequence(QKeySequence.Quit),
                self)
        else:
            self.quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)

        # disable recompress
        self.ui.recompress.setEnabled(False)
        #self.ui.recompress.hide()

        # make a worker thread
        self.thread = Worker()

        # connect signals with slots
        QObject.connect(self.ui.addfiles, SIGNAL("clicked()"),
            self.file_dialog)
        QObject.connect(self.ui.recompress, SIGNAL("clicked()"),
            self.recompress_files)
        QObject.connect(self.quit_shortcut, SIGNAL("activated()"),
            qApp, SLOT('quit()'))
        QObject.connect(self.ui.processedfiles, SIGNAL("fileDropEvent"),
            self.file_drop)
        QObject.connect(self.thread, SIGNAL("finished()"), self.update_table)
        QObject.connect(self.thread, SIGNAL("terminated()"), self.update_table)
        QObject.connect(self.thread, SIGNAL("updateUi"), self.update_table)

        self.compressing_icon = QIcon(QPixmap(self.ui.get_image("pixmaps/compressing.gif")))

        # activate command line options
        self.commandline_options()

        if QSystemTrayIcon.isSystemTrayAvailable() and not self.cli:
            self.systemtray = Systray(self)

    def commandline_options(self):
        self.cli = False
        """Set up the command line options."""
        parser = OptionParser(version="%prog " + VERSION,
            description="GUI front-end to compress png and jpg images via "
                "optipng, advpng and jpegoptim")

        parser.set_defaults(verbose=True)
        parser.add_option("-v", "--verbose", action="store_true",
            dest="verbose", help="Verbose mode (default)")
        parser.add_option("-q", "--quiet", action="store_false",
            dest="verbose", help="Quiet mode")

        parser.add_option("-f", "--file", action="store", type="string",
            dest="filename", help="compresses image and exit")
        parser.add_option("-d", "--directory", action="store", type="string",
            dest="directory", help="compresses images in directory and exit")

        options, args = parser.parse_args()

        # make sure we quit after processing finished if using cli
        if options.filename or options.directory:
            QObject.connect(self.thread, SIGNAL("finished()"), quit)
            self.cli = True

        # send to correct function
        if options.filename:
            self.file_from_cmd(options.filename.decode("utf-8"))
        if options.directory:
            self.dir_from_cmd(options.directory.decode("utf-8"))

        self.verbose = options.verbose

    """
    Input functions
    """

    def dir_from_cmd(self, directory):
        """
        Read the files in the directory and send all files to compress_file.
        """
        self.showapp = False
        dirpath = path.abspath(directory)
        imagedir = listdir(directory)
        filelist = [path.join(dirpath, image) for image in imagedir]
        self.delegator(filelist)

    def file_from_cmd(self, image):
        """Get the file and send it to compress_file"""
        self.showapp = False
        filelist = [path.abspath(image)]
        self.delegator(filelist)

    def file_drop(self, images):
        """
        Get a file from the drag and drop handler and send it to compress_file.
        """
        self.delegator(images)

    def file_dialog(self):
        """Open a file dialog and send the selected images to compress_file."""
        fd = QFileDialog(self)
        fd.restoreState(self.settings.value("fdstate").toByteArray())
        directory = self.settings.value("directory", QVariant("")).toString()
        fd.setDirectory(directory)

        images = fd.getOpenFileNames(self,
            "Select one or more image files to compress",
            directory,
            # this is a fix for file dialog differentiating between cases
            "Image files (*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG)")

        self.settings.setValue("fdstate", QVariant(fd.saveState()))
        if images:
          self.settings.setValue("directory", QVariant(path.dirname(unicode(images[0]))))
        self.delegator([unicode(fullpath) for fullpath in images])

    def recompress_files(self):
        """Send each file in the current file list to compress_file again."""
        self.delegator([row.image.fullpath for row in self.imagelist])

    """
    Compress functions
    """

    def delegator(self, images):
        """
        Receive all images, check them and send them to the worker thread.
        """
        delegatorlist = []
        for fullpath in images:
            try: # recompress images already in the list
                image = (i.image for i in self.imagelist
                    if i.image.fullpath == fullpath).next()
                if image.compressed:
                    image.reset()
                    image.recompression = True
                    delegatorlist.append(image)
            except StopIteration:
            	if not path.isdir(fullpath):
                    self. add_image(fullpath, delegatorlist)
                else:
                    self.walk(fullpath, delegatorlist)

        self.update_table()
        self.thread.compress_file(delegatorlist, self.showapp, self.verbose,
            self.imagelist)

    def walk(self, dir, delegatorlist):
        """
        Walks a directory, and executes a callback on each file
        """
        dir = path.abspath(dir)
        for file in [file for file in listdir(dir) if not file in [".","..",".svn",".git",".hg",".bzr",".cvs"]]:
            nfile = path.join(dir, file)

            if path.isdir(nfile):
                self.walk(nfile, delegatorlist)
            else:
                self.add_image(nfile, delegatorlist)

    def add_image(self, fullpath, delegatorlist):
        """
        Adds an image file to the delegator list and update the tray and the title of the window
        """
        image = Image(fullpath)
        if image.valid:
            delegatorlist.append(image)
            self.imagelist.append(ImageRow(image, self.compressing_icon))
            if QSystemTrayIcon.isSystemTrayAvailable() and not self.cli:
                self.systemtray.trayIcon.setToolTip("Trimage image compressor (" + str(len(self.imagelist)) + " files)")
                self.setWindowTitle("Trimage image compressor (" + str(len(self.imagelist)) + " files)")
        else:
            print >> sys.stderr, u"[error] %s not a supported image file and/or not writeable" % image.fullpath

    """
    UI Functions
    """

    def update_table(self):
        """Update the table view with the latest file data."""
        tview = self.ui.processedfiles
        # set table model
        tmodel = TriTableModel(self, self.imagelist,
            ["Filename", "Old Size", "New Size", "Compressed"])
        tview.setModel(tmodel)

        # set minimum size of table
        vh = tview.verticalHeader()
        vh.setVisible(False)

        # set horizontal header properties
        hh = tview.horizontalHeader()
        hh.setStretchLastSection(True)

        # set all row heights
        nrows = len(self.imagelist)
        for row in range(nrows):
            tview.setRowHeight(row, 25)

        # set the second column to be longest
        tview.setColumnWidth(0, 300)

        # enable recompress button
        self.enable_recompress()

    """
    Helper functions
    """

    def enable_recompress(self):
        """Enable the recompress button."""
        self.ui.recompress.setEnabled(True)
        if QSystemTrayIcon.isSystemTrayAvailable() and not self.cli:
            self.systemtray.recompress.setEnabled(True)

    def checkapps(self):
        """Check if the required command line apps exist."""
        exe = ".exe" if (sys.platform == "win32") else ""
        status = False
        retcode = self.safe_call("jpegoptim" + exe + " --version")
        if retcode != 0:
            status = True
            sys.stderr.write("[error] please install jpegoptim")

        retcode = self.safe_call("optipng" + exe + " -v")
        if retcode != 0:
            status = True
            sys.stderr.write("[error] please install optipng")

        retcode = self.safe_call("advpng" + exe + " --version")
        if retcode != 0:
            status = True
            sys.stderr.write("[error] please install advancecomp")

        retcode = self.safe_call("pngcrush" + exe + " -version")
        if retcode != 0:
            status = True
            sys.stderr.write("[error] please install pngcrush")
        return status

    def safe_call(self, command):
        """ cross-platform command-line check """
        while True:
            try:
                return call(command, shell=True, stdout=PIPE)
            except OSError, e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise

    def hide_main_window(self):
        if self.isVisible():
            self.hide()
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.systemtray.hideMain.setText("&Show window")
        else:
            self.show()
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.systemtray.hideMain.setText("&Hide window")

    def closeEvent(self, event):
      self.settings.setValue("geometry", QVariant(self.saveGeometry()))
      event.accept()


class TriTableModel(QAbstractTableModel):

    def __init__(self, parent, imagelist, header, *args):
        """
        @param parent Qt parent object.
        @param imagelist A list of tuples.
        @param header A list of strings.
        """
        QAbstractTableModel.__init__(self, parent, *args)
        self.imagelist = imagelist
        self.header = header

    def rowCount(self, parent):
        """Count the number of rows."""
        return len(self.imagelist)

    def columnCount(self, parent):
        """Count the number of columns."""
        return len(self.header)

    def data(self, index, role):
        """Fill the table with data."""
        if not index.isValid():
            return QVariant()
        elif role == Qt.DisplayRole:
            data = self.imagelist[index.row()][index.column()]
            return QVariant(data)
        elif index.column() == 0 and role == Qt.DecorationRole:
            # decorate column 0 with an icon of the image itself
            f_icon = self.imagelist[index.row()][4]
            return QVariant(f_icon)
        else:
            return QVariant()

    def headerData(self, col, orientation, role):
        """Fill the table headers."""
        if orientation == Qt.Horizontal and (role == Qt.DisplayRole or
        role == Qt.DecorationRole):
            return QVariant(self.header[col])
        return QVariant()


class ImageRow:

    def __init__(self, image, waitingIcon=None):
        """ Build the information visible in the table image row. """
        self.image = image
        d = {
            'shortname': lambda i: self.statusStr() % i.shortname,
            'oldfilesizestr': lambda i: size(i.oldfilesize, system=alternative)
                if i.compressed else "",
            'newfilesizestr': lambda i: size(i.newfilesize, system=alternative)
                if i.compressed else "",
            'ratiostr': lambda i:
                "%.1f%%" % (100 - (float(i.newfilesize) / i.oldfilesize * 100))
                if i.compressed else "",
            'icon': lambda i: i.icon if i.compressed else waitingIcon,
            'fullpath': lambda i: i.fullpath, #only used by cli
        }
        names = ['shortname', 'oldfilesizestr', 'newfilesizestr',
                      'ratiostr', 'icon']
        for i, n in enumerate(names):
            d[i] = d[n]

        self.d = d

    def statusStr(self):
        """ Set the status message. """
        if self.image.failed:
            return "ERROR: %s"
        if self.image.compressing:
            message = "Compressing %s..."
            return message
        if not self.image.compressed and self.image.recompression:
            return "Queued for recompression..."
        if not self.image.compressed:
            return "Queued..."
        return "%s"

    def __getitem__(self, key):
        return self.d[key](self.image)


class Image:

    def __init__(self, fullpath):
        """ gather image information. """
        self.valid = False
        self.reset()
        self.fullpath = fullpath
        if path.isfile(self.fullpath) and access(self.fullpath, WRITEABLE):
            self.filetype = determinetype(self.fullpath)
            if self.filetype in ["jpeg", "png"]:
                oldfile = QFileInfo(self.fullpath)
                self.shortname = oldfile.fileName()
                self.oldfilesize = oldfile.size()
                self.icon = QIcon(self.fullpath)
                self.valid = True

    #def _determinetype(self):
    #    """ Determine the filetype of the file using imghdr. """
    #    filetype = determinetype(self.fullpath)
    #    if filetype in ["jpeg", "png"]:
    #        self.filetype = filetype
    #    else:
    #        self.filetype = None
    #    return self.filetype

    def reset(self):
        self.failed = False
        self.compressed = False
        self.compressing = False
        self.recompression = False

    def compress(self):
        """ Compress the image and return it to the thread. """
        if not self.valid:
            raise "Tried to compress invalid image (unsupported format or not \
            file)"
        self.reset()
        self.compressing = True
        exe = ".exe" if (sys.platform == "win32") else ""
        runString = {
            "jpeg": u"jpegoptim" + exe + " -f --strip-all '%(file)s'",
            "png": u"optipng" + exe + " -force -o7 '%(file)s'&&advpng" + exe + " -z4 '%(file)s' && pngcrush -rem gAMA -rem alla -rem cHRM -rem iCCP -rem sRGB -rem time '%(file)s' '%(file)s.bak' && mv '%(file)s.bak' '%(file)s'"
        }
        # Create a backup file
        copy(self.fullpath, self.fullpath + '~')
        try:
            retcode = call(runString[self.filetype] % {"file": self.fullpath},
                shell=True, stdout=PIPE)
        except:
            retcode = -1
        if retcode == 0:
            self.newfilesize = QFile(self.fullpath).size()
            self.compressed = True

            # Checks the new file and copy the backup
            if self.newfilesize >= self.oldfilesize:
                copy(self.fullpath + '~', self.fullpath)
                self.newfilesize = self.oldfilesize

            # Removes the backup file
            remove(self.fullpath + '~')
        else:
            self.failed = True
        self.compressing = False
        self.retcode = retcode
        return self


class Worker(QThread):

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.toDisplay = Queue()
        self.threadpool = ThreadPool(max_workers=cpu_count())

    def __del__(self):
        self.threadpool.shutdown()

    def compress_file(self, images, showapp, verbose, imagelist):
        """Start the worker thread."""
        for image in images:
            #FIXME:http://code.google.com/p/pythonthreadpool/issues/detail?id=5
            time.sleep(0.05)
            self.threadpool.add_job(image.compress, None,
                                    return_callback=self.toDisplay.put)
        self.showapp = showapp
        self.verbose = verbose
        self.imagelist = imagelist
        self.start()

    def run(self):
        """Compress the given file, get data from it and call update_table."""
        tp = self.threadpool
        while self.showapp or not (tp._ThreadPool__active_worker_count == 0 and
                                   tp._ThreadPool__jobs.empty()):
            image = self.toDisplay.get()

            self.emit(SIGNAL("updateUi"))

            if not self.showapp and self.verbose: # we work via the commandline
                if image.retcode == 0:
                    ir = ImageRow(image)
                    print("File: " + ir['fullpath'] + ", Old Size: "
                        + ir['oldfilesizestr'] + ", New Size: "
                        + ir['newfilesizestr'] + ", Ratio: " + ir['ratiostr'])
                else:
                    print >> sys.stderr, u"[error] %s could not be compressed" % image.fullpath


class Systray(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.createActions()
        self.createTrayIcon()
        self.trayIcon.show()

    def createActions(self):
        self.quitAction = QAction(self.tr("&Quit"), self)
        QObject.connect(self.quitAction, SIGNAL("triggered()"),
            qApp, SLOT("quit()"))

        self.addFiles = QAction(self.tr("&Add and compress"), self)
        icon = QIcon()
        icon.addPixmap(QPixmap(self.parent.ui.get_image(("pixmaps/list-add.png"))),
            QIcon.Normal, QIcon.Off)
        self.addFiles.setIcon(icon)
        QObject.connect(self.addFiles, SIGNAL("triggered()"), self.parent.file_dialog)

        self.recompress = QAction(self.tr("&Recompress"), self)
        icon2 = QIcon()
        icon2.addPixmap(QPixmap(self.parent.ui.get_image(("pixmaps/view-refresh.png"))),
            QIcon.Normal, QIcon.Off)
        self.recompress.setIcon(icon2)
        self.recompress.setDisabled(True)
        QObject.connect(self.addFiles, SIGNAL("triggered()"), self.parent.recompress_files)

        self.hideMain = QAction(self.tr("&Hide window"), self)
        QObject.connect(self.hideMain, SIGNAL("triggered()"), self.parent.hide_main_window)

    def createTrayIcon(self):
        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.addFiles)
        self.trayIconMenu.addAction(self.recompress)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.hideMain)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.trayIcon = QSystemTrayIcon(self)
            self.trayIcon.setContextMenu(self.trayIconMenu)
            self.trayIcon.setToolTip("Trimage image compressor")
            self.trayIcon.setIcon(QIcon(self.parent.ui.get_image("pixmaps/trimage-icon.png")))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myapp = StartQT4()

    if myapp.showapp:
        myapp.show()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = ui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from os import path

class TrimageTableView(QTableView):
    """Init the table drop event."""
    def __init__(self, parent=None):
        super(TrimageTableView, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        event.accept()
        filelist = []
        for url in event.mimeData().urls():
            filelist.append(unicode(url.toLocalFile()))

        self.emit(SIGNAL("fileDropEvent"), (filelist))


class Ui_trimage(object):
    def get_image(self, image):
        """ Get the correct link to the images used in the UI """
        imagelink = path.join(path.dirname(path.dirname(path.realpath(__file__))), "trimage/" + image)
        return imagelink

    def setupUi(self, trimage):
        """ Setup the entire UI """
        trimage.setObjectName("trimage")
        trimage.resize(600, 170)

        trimageIcon = QIcon(self.get_image("pixmaps/trimage-icon.png"))
        trimage.setWindowIcon(trimageIcon)

        self.centralwidget = QWidget(trimage)
        self.centralwidget.setObjectName("centralwidget")

        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setMargin(0)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")

        self.widget = QWidget(self.centralwidget)
        self.widget.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(
            self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setObjectName("widget")

        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName("verticalLayout")

        self.frame = QFrame(self.widget)
        self.frame.setObjectName("frame")

        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setMargin(10)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.addfiles = QPushButton(self.frame)
        font = QFont()
        font.setPointSize(9)
        self.addfiles.setFont(font)
        self.addfiles.setCursor(Qt.PointingHandCursor)
        icon = QIcon()
        icon.addPixmap(QPixmap(self.get_image("pixmaps/list-add.png")), QIcon.Normal, QIcon.Off)
        self.addfiles.setIcon(icon)
        self.addfiles.setObjectName("addfiles")
        self.addfiles.setAcceptDrops(True)
        self.horizontalLayout.addWidget(self.addfiles)

        self.label = QLabel(self.frame)
        font = QFont()
        font.setPointSize(8)
        self.label.setFont(font)
        self.label.setFrameShadow(QFrame.Plain)
        self.label.setMargin(1)
        self.label.setIndent(10)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)

        spacerItem = QSpacerItem(498, 20, QSizePolicy.Expanding,
                                 QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.recompress = QPushButton(self.frame)
        font = QFont()
        font.setPointSize(9)
        self.recompress.setFont(font)
        self.recompress.setCursor(Qt.PointingHandCursor)

        icon1 = QIcon()
        icon1.addPixmap(QPixmap(self.get_image("pixmaps/view-refresh.png")), QIcon.Normal, QIcon.Off)

        self.recompress.setIcon(icon1)
        self.recompress.setCheckable(False)
        self.recompress.setObjectName("recompress")
        self.horizontalLayout.addWidget(self.recompress)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.processedfiles = TrimageTableView(self.frame)
        self.processedfiles.setEnabled(True)
        self.processedfiles.setFrameShape(QFrame.NoFrame)
        self.processedfiles.setFrameShadow(QFrame.Plain)
        self.processedfiles.setLineWidth(0)
        self.processedfiles.setMidLineWidth(0)
        self.processedfiles.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.processedfiles.setTabKeyNavigation(True)
        self.processedfiles.setAlternatingRowColors(True)
        self.processedfiles.setTextElideMode(Qt.ElideRight)
        self.processedfiles.setShowGrid(True)
        self.processedfiles.setGridStyle(Qt.NoPen)
        self.processedfiles.setSortingEnabled(False)
        self.processedfiles.setObjectName("processedfiles")
        self.processedfiles.resizeColumnsToContents()
        self.processedfiles.setSelectionMode(QAbstractItemView.NoSelection)
        self.verticalLayout_2.addWidget(self.processedfiles)
        self.verticalLayout.addWidget(self.frame)
        self.gridLayout_2.addWidget(self.widget, 0, 0, 1, 1)
        trimage.setCentralWidget(self.centralwidget)

        self.retranslateUi(trimage)
        QMetaObject.connectSlotsByName(trimage)

    def retranslateUi(self, trimage):
        """ Fill in the texts for all UI elements """
        trimage.setWindowTitle(QApplication.translate("trimage",
            "Trimage image compressor", None, QApplication.UnicodeUTF8))
        self.addfiles.setToolTip(QApplication.translate("trimage",
            "Add file to the compression list", None,
            QApplication.UnicodeUTF8))
        self.addfiles.setText(QApplication.translate("trimage",
            "&Add and compress", None, QApplication.UnicodeUTF8))
        self.addfiles.setShortcut(QApplication.translate("trimage",
            "Alt+A", None, QApplication.UnicodeUTF8))
        self.label.setText(QApplication.translate("trimage",
            "Drag and drop images onto the table", None,
            QApplication.UnicodeUTF8))
        self.recompress.setToolTip(QApplication.translate("trimage",
            "Recompress all images", None, QApplication.UnicodeUTF8))
        self.recompress.setText(QApplication.translate("trimage",
            "&Recompress", None, QApplication.UnicodeUTF8))
        self.recompress.setShortcut(QApplication.translate("trimage",
            "Alt+R", None, QApplication.UnicodeUTF8))
        self.processedfiles.setToolTip(QApplication.translate("trimage",
            "Drag files in here", None, QApplication.UnicodeUTF8))
        self.processedfiles.setWhatsThis(QApplication.translate("trimage",
            "Drag files in here", None, QApplication.UnicodeUTF8))

########NEW FILE########
