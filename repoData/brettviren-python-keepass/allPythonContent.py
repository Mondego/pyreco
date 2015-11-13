__FILENAME__ = keepassc
#!/usr/bin/env python

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import sys
from keepass import cli

cliobj = cli.Cli(sys.argv[1:])
cliobj()

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
'''
Command line interface to manipulating keepass files
'''

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import sys

class Cli(object):
    '''
    Process command line
    '''

    commands = [
        'help',                 # print help message
        'open',                 # open and decrypt a file
        'save',                 # save current DB to file
        'dump',                 # dump current DB to text
        'entry',                # add an entry
        ]

    def __init__(self,args=None):
        self.db = None
        self.hier = None
        self.command_line = None
        self.ops = {}
        if args: self.parse_args(args)
        return

    def parse_args(self,args):
        '''
        keepass.cli [options] [cmd [options]] [...]

        The command line consists of general options followed by zero
        or more commands and their options.

        '''

        def splitopts(argv):
            'Split optional command and its args removing them from input'
            if not argv: return None

            cmd=""
            if argv[0][0] != '-':
                if argv[0] not in Cli.commands:
                    raise ValueError,'Unknown command: "%s"'%argv[0]
                cmd = argv.pop(0)
                pass
            copy = list(argv)
            cmdopts = []
            for arg in copy:
                if arg in Cli.commands: break
                cmdopts.append(argv.pop(0))
                continue
            return [cmd,cmdopts]

        cmdline = []
        copy = list(args)
        while copy:
            chunk = splitopts(copy)
            if not chunk: break

            if not chunk[0]: chunk[0] = 'general'
            meth = eval('self._%s_op'%chunk[0])
            self.ops[chunk[0]] = meth()
            cmdline.append(chunk)
            continue

        self.command_line = cmdline

        return

    def __call__(self):
        'Process commands'
        if not self.command_line:
            print self._general_op().print_help()
            return
        for cmd,cmdopts in self.command_line:
            meth = eval('self._%s'%cmd)
            meth(cmdopts)
            continue
        return

    def _general_op(self):
        '''
        keepassc [options] [cmd cmd_options] ...
        
        Example: open, dump to screen and save

        keepassc open -m "My Secret" input.kpdb \
                 dump -f '"%(title)s" "%(username)s" %(url)s' \
                 save -m "New Secret" output.kpdb

        execute "help" command for more information.
        '''
        from optparse import OptionParser
        op = OptionParser(usage=self._general_op.__doc__)
        return op

    def _general(self,opts):
        'Process general options'
        opts,args = self.ops['general'].parse_args(opts)
        return


    def _help_op(self):
        return None
    def _help(self,opts):
        'Print some helpful information'

        print 'Available commands:'
        for cmd in Cli.commands:
            meth = eval('self._%s'%cmd)
            print '\t%s: %s'%(cmd,meth.__doc__)
            continue
        print '\nPer-command help:\n'

        for cmd in Cli.commands:
            meth = eval('self._%s_op'%cmd)
            op = meth()
            if not op: continue
            print '%s'%cmd.upper()
            op.print_help()
            print
            continue

    def _open_op(self):
        'open [options] filename'
        from optparse import OptionParser
        op = OptionParser(usage=self._open_op.__doc__,add_help_option=False)
        op.add_option('-m','--masterkey',type='string',default="",
                      help='Set master key for decrypting file, default: ""')
        return op

    def _open(self,opts):
        'Read a file to the in-memory database'
        opts,files = self.ops['open'].parse_args(opts)
        import kpdb
        # fixme - add support for openning/merging multiple DBs!
        try:
            dbfile = files[0]
        except IndexError:
            print "No database file specified"
            sys.exit(1)
        self.db = kpdb.Database(files[0],opts.masterkey)
        self.hier = self.db.hierarchy()
        return

    def _save_op(self):
        'save [options] filename'
        from optparse import OptionParser
        op = OptionParser(usage=self._save_op.__doc__,add_help_option=False)
        op.add_option('-m','--masterkey',type='string',default="",
                      help='Set master key for encrypting file, default: ""')
        return op

    def _save(self,opts):
        'Save the current in-memory database to a file'
        opts,files = self.ops['save'].parse_args(opts)
        self.db.update(self.hier)
        self.db.write(files[0],opts.masterkey)
        return

    def _dump_op(self):
        'dump [options] [name|/group/name]'
        from optparse import OptionParser
        op = OptionParser(usage=self._dump_op.__doc__,add_help_option=False)
        op.add_option('-p','--show-passwords',action='store_true',default=False,
                      help='Show passwords as plain text')
        op.add_option('-f','--format',type='string',
                      default='%(group_name)s/%(username)s: %(title)s %(url)s',
                      help='Set the format of the dump')
        return op

    def _dump(self,opts):
        'Print the current database in a formatted way.'
        opts,files = self.ops['dump'].parse_args(opts)
        if not self.hier:
            sys.stderr.write('Can not dump.  No database open.\n')
            return
        print self.hier
        #self.hier.dump(opts.format,opts.show_passwords)
        return
        
    def _entry_op(self):
        'entry [options] username [password]'
        from optparse import OptionParser
        op = OptionParser(usage=self._entry_op.__doc__,add_help_option=False)
        op.add_option('-p','--path',type='string',default='/',
                      help='Set folder path in which to store this entry')
        op.add_option('-t','--title',type='string',default="",
                      help='Set the title for the entry, defaults to username')
        op.add_option('-u','--url',type='string',default="",
                      help='Set a URL for the entry')
        op.add_option('-n','--note',type='string',default="",
                      help='Set a note for the entry')
        op.add_option('-i','--imageid',type='int',default=1,
                      help='Set the image ID number for the entry')
        op.add_option('-a','--append',action='store_true',default=False,
                      help='The entry will be appended instead of overriding matching entry')
        return op

    def _entry(self,opts):
        'Add an entry into the database'
        import getpass
        opts,args = self.ops['entry'].parse_args(opts)
        username = args[0]
        try:
            password = args[1]
        except:
            password1 = password2 = None
            while True:
                password1 = getpass.getpass()
                password2 = getpass.getpass()
                if password1 != password2: 
                    sys.stderr.write("Error: Your passwords didn't match\n")
                    continue
                break
            pass

        self.db.add_entry(opts.path,opts.title or username,username,password,
                          opts.url,opts.note,opts.imageid,opts.append)
        return

if '__main__' == __name__:
    cliobj = Cli(sys.argv[1:])
    cliobj()

########NEW FILE########
__FILENAME__ = header
#!/usr/bin/env python

'''
The keepass file header.

From the KeePass doc:

Database header: [DBHDR]

[ 4 bytes] DWORD    dwSignature1  = 0x9AA2D903
[ 4 bytes] DWORD    dwSignature2  = 0xB54BFB65
[ 4 bytes] DWORD    dwFlags
[ 4 bytes] DWORD    dwVersion       { Ve.Ve.Mj.Mj:Mn.Mn.Bl.Bl }
[16 bytes] BYTE{16} aMasterSeed
[16 bytes] BYTE{16} aEncryptionIV
[ 4 bytes] DWORD    dwGroups        Number of groups in database
[ 4 bytes] DWORD    dwEntries       Number of entries in database
[32 bytes] BYTE{32} aContentsHash   SHA-256 hash value of the plain contents
[32 bytes] BYTE{32} aMasterSeed2    Used for the dwKeyEncRounds AES
                                    master key transformations
[ 4 bytes] DWORD    dwKeyEncRounds  See above; number of transformations

Notes:

- dwFlags is a bitmap, which can include:
  * PWM_FLAG_SHA2     (1) for SHA-2.
  * PWM_FLAG_RIJNDAEL (2) for AES (Rijndael).
  * PWM_FLAG_ARCFOUR  (4) for ARC4.
  * PWM_FLAG_TWOFISH  (8) for Twofish.
- aMasterSeed is a salt that gets hashed with the transformed user master key
  to form the final database data encryption/decryption key.
  * FinalKey = SHA-256(aMasterSeed, TransformedUserMasterKey)
- aEncryptionIV is the initialization vector used by AES/Twofish for
  encrypting/decrypting the database data.
- aContentsHash: "plain contents" refers to the database file, minus the
  database header, decrypted by FinalKey.
  * PlainContents = Decrypt_with_FinalKey(DatabaseFile - DatabaseHeader)
'''

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import Crypto.Random

class DBHDR(object):
    '''
    Interface to the database header chunk.
    '''

    format = [
        ('signature1',4,'I'),
        ('signature2',4,'I'),
        ('flags',4,'I'),
        ('version',4,'I'),
        ('master_seed',16,'16s'),
        ('encryption_iv',16,'16s'),
        ('ngroups',4,'I'),
        ('nentries',4,'I'),
        ('contents_hash',32,'32s'),
        ('master_seed2',32,'32s'),
        ('key_enc_rounds',4,'I'),
        ]
    
    signatures = (0x9AA2D903,0xB54BFB65)
    length = 124

    encryption_flags = (
        ('SHA2',1),
        ('Rijndael',2),
        ('AES',2),
        ('ArcFour',4),
        ('TwoFish',8),
        )

    def __init__(self,buf=None):
        'Create a header, read self from binary string if given'
        if buf:
            self.decode(buf)
        else:
            self.signature1, self.signature2 = self.signatures
            # defaults taken from a file generated with KeePassX 0.4.3 on default settings
            self.version = 0x30002
            self.flags = 3 # SHA2 hashing, AES encryption
            self.key_enc_rounds = 50000
            self.reset_random_fields()
    
    def reset_random_fields(self):
        rng = Crypto.Random.new()
        self.encryption_iv  = rng.read(16)
        self.master_seed    = rng.read(16)
        self.master_seed2   = rng.read(32)
        rng.close()
    
    def __str__(self):
        ret = ['Header:']
        for field in DBHDR.format:
            name = field[0]
            size = field[1]
            typ = field[2]
            ret.append('\t%s %s'%(name,self.__dict__[name]))
            continue
        return '\n'.join(ret)

    def encryption_type(self):
        for encflag in DBHDR.encryption_flags[1:]:
            if encflag[1] & self.flags: return encflag[0]
        return 'Unknown'

    def encode(self):
        'Provide binary string representation'
        import struct

        ret = ""

        for field in DBHDR.format:
            name,bytes,typecode = field
            value = self.__dict__[name]
            buf = struct.pack('<'+typecode,value)
            ret += buf
            continue
        return ret

    def decode(self,buf):
        'Fill self from binary string.'
        import struct

        index = 0

        for field in DBHDR.format:
            name,nbytes,typecode = field
            string = buf[index:index+nbytes]
            index += nbytes
            value = struct.unpack('<'+typecode, string)[0]
            self.__dict__[name] = value
            continue

        if DBHDR.signatures[0] != self.signature1 or \
                DBHDR.signatures[1] != self.signature2:
            msg = 'Bad sigs:\n%s %s\n%s %s'%\
                (DBHDR.signatures[0],DBHDR.signatures[1],
                 self.signature1,self.signature2)
            raise IOError,msg

        return

    pass                        # DBHDR

########NEW FILE########
__FILENAME__ = hier
#!/usr/bin/env python
'''
Classes to construct a hiearchy holding infoblocks.
'''

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import datetime

def path2list(path):
    '''
    Maybe convert a '/' separated string into a list.
    '''
    if isinstance(path,str): 
        path = path.split('/')
        if path[-1] == '': path.pop() # remove trailing '/'
        return path

    return list(path)           # make copy

class Visitor(object):
    '''
    A class that can visit group/entry hierarchy via hier.visit(). 

    A visitor should be a callable with the signature
        
        visitor(obj) -> (value, bail)
        
    The obj is either the node's group or one of it's entries or None.
    The return values control the descent
        
    If value is ever non-None it is assumed the descent is over
    and this value is returned.

    If bail is ever True, the current node is abandoned in the
    descent.  This can be used to avoid sub trees that are not
    interesting to the visitor.
    '''
    def __call__(self):
        notimplemented

    pass

class Walker(object):
    '''
    A class that can visit the node hierarchy

    Like a visitor, this callable should return a tuple of
    (value,bail). non-None to abort the descent and return that value.
    If bail is True, then drop the current node and move to its next
    sister.
    '''
    def __call__(self,node):
        notimplemented
    pass

class NodeDumper(Walker):
    def __call__(self,node):
        if not node.group:
            print 'Top'
            return None, False
        print '  '*node.level()*2,node.group.name(),node.group.groupid,\
            len(node.entries),len(node.nodes)
        return None, False

class FindGroupNode(object):
    '''Return the node holding the group of the given name.  If name
    has any slashes it will be interpreted as a path ending in that
    group'''
    def __init__(self,path, stop_on_first = True):
        self._collected = []
        self.best_match = None
        self.path = path2list(path)
        self.stop_on_first = stop_on_first
        return

    def __call__(self,node):
        if not self.path: 
            return (None,True)
        if not node.group:
            if self.path[0] == "" or self.path[0] == "None" or self.path[0] is None:
                self.path.pop(0)
            return (None,None)

        top_name = self.path[0]
        obj_name = node.group.name()

        groupid = node.group.groupid

        from infoblock import GroupInfo

        if top_name != obj_name:
            return (None,True) # bail on the current node

        self.best_match = node

        if len(self.path) == 1: # we have a full match
            if self.stop_on_first:
                return node,True # got it!
            else:                # might have a matching sister
                self._collected.append(node)
                return (None,None)
            pass

        self.path.pop(0)
        return (None,None)  # keep going


class CollectVisitor(Visitor):
    '''
    A callable visitor that will collect the groups and entries into
    flat lists.  After the descent the results are available in the
    .groups and .entries data memebers.
    '''
    def __init__(self):
        self.groups = []
        self.entries = []
        return

    def __call__(self,g_or_e):
        if g_or_e is None: return (None,None)
        from infoblock import GroupInfo
        if isinstance(g_or_e,GroupInfo):
            self.groups.append(g_or_e)
        else:
            self.entries.append(g_or_e)
        return (None,None)
    pass


class PathVisitor(Visitor):
    '''
    A callable visitor to descend via hier.visit() method and
    return the group or the entry matching a given path.

    The path is a list of group names with the last element being
    either a group name or an entry title.  The path can be a list
    object or a string interpreted to be delimited by slashs (think
    UNIX pathspec).

    If stop_on_first is False, the visitor will not abort after the
    first match but will instead keep collecting all matches.  This
    can be used to collect groups or entries that are degenerate in
    their group_name or title, respectively.  After the descent the
    collected values can be retrived from PathVisitor.results()

    This visitor also maintains a best match.  In the event of failure
    (return of None) the .best_match data member will hold the group
    object that was located where the path diverged from what was
    found.  The .path data memeber will retain the remain part of the
    unmatched path.
    '''
    def __init__(self,path,stop_on_first = True):
        self._collected = []
        self.best_match = None
        self.stop_on_first = stop_on_first
        self.path = path2list(path)
        return

    def results(self): 
        'Return a list of the matched groups or entries'
        return self._collected

    def __call__(self,g_or_e):
        if not self.path: return (None,None)

        top_name = self.path[0] or "None"
        obj_name = "None"
        if g_or_e: obj_name = g_or_e.name()

        groupid = None
        if g_or_e: groupid = g_or_e.groupid

        from infoblock import GroupInfo

        if top_name != obj_name:
            if isinstance(g_or_e,GroupInfo):
                return (None,True) # bail on the current node
            else:
                return (None,None) # keep going

        self.best_match = g_or_e

        if len(self.path) == 1: # we have a full match
            if self.stop_on_first:
                return g_or_e,True # got it!
            else:                  # might have a matching sister
                self._collected.append(g_or_e)
                return (None,None)
            pass

        self.path.pop(0)
        return (None,None)  # keep going


class Node(object):
    '''
    A node in the group hiearchy.  

    This basically associates entries to their group

    Holds:

     * zero or one group - zero implies top of hierarchy
     * zero or more nodes
     * zero or more entries
    '''

    def __init__(self,group=None,entries=None,nodes=None):
        self.group = group
        self.nodes = nodes or list()
        self.entries = entries or list()
        return

    def level(self):
        'Return the level of the group or -1 if have no group'
        if self.group: return self.group.level
        return -1

    def __str__(self):
        return self.pretty()

    def name(self):
        'Return name of group or None if no group'
        if self.group: return self.group.group_name
        return None

    def pretty(self,depth=0):
        'Pretty print this Node and its contents'
        tab = '  '*depth


        me = "%s%s (%d entries) (%d subnodes)\n"%\
            (tab,self.name(),len(self.entries),len(self.nodes))

        children=[]
        for e in self.entries:
            s = "%s%s(%s: %s)\n"%(tab,tab,e.title,e.username)
            children.append(s)
            continue

        for n in self.nodes:
            children.append(n.pretty(depth+1))
            continue

        return me + ''.join(children)

    def node_with_group(self,group):
        'Return the child node holding the given group'
        if self.group == group:
            return self
        for child in self.nodes:
            ret = child.node_with_group(group)
            if ret: return ret
            continue
        return None

    pass


def visit(node,visitor):
    '''
    Depth-first descent into the group/entry hierarchy.
    
    The order of visiting objects is: this node's group,
    recursively calling this function on any child nodes followed
    by this node's entries.
    
    See docstring for hier.Visitor for information on the given visitor. 
    '''
    val,bail = visitor(node.group)
    if val is not None or bail: return val
    
    for n in node.nodes:
        val = visit(n,visitor)
        if val is not None: return val
        continue
    
    for e in node.entries:
        val,bail = visitor(e)
        if val is not None or bail: return val
        continue

    return None

def walk(node,walker):
    '''
    Depth-first descent into the node hierarchy.
    
    See docstring for hier.Walker for information on the given visitor. 
    '''
    value,bail = walker(node)
    if value is not None or bail: return value

    for sn in node.nodes:
        value = bail = walk(sn,walker)
        if value is not None: return value
        continue
    return None    

def mkdir(top, path, gen_groupid):
    '''
    Starting at given top node make nodes and groups to satisfy the
    given path, where needed.  Return the node holding the leaf group.
    
    @param gen_groupid: Group ID factory from kpdb.Database instance.
    '''
    import infoblock

    path = path2list(path)
    pathlen = len(path)

    fg = FindGroupNode(path)
    node = walk(top,fg)

    if not node:                # make remaining intermediate folders
        node = fg.best_match or top
        pathlen -= len(fg.path)
        for group_name in fg.path:
            # fixme, this should be moved into a new constructor
            new_group = infoblock.GroupInfo()
            new_group.groupid = gen_groupid()
            new_group.group_name = group_name
            new_group.imageid = 1
            new_group.creation_time = datetime.datetime.now() 
            new_group.last_mod_time = datetime.datetime.now() 
            new_group.last_acc_time = datetime.datetime.now() 
            new_group.expiration_time = datetime.datetime(2999, 12, 28, 23, 59, 59) # KeePassX 0.4.3 default
            new_group.level = pathlen
            new_group.flags = 0
            new_group.order = [(1, 4), 
			       (2, len(new_group.group_name) + 1), 
			       (3, 5), 
			       (4, 5), 
			       (5, 5), 
			       (6, 5), 
			       (7, 4), 
			       (8, 2), 
			       (9, 4), 
			       (65535, 0)]
            pathlen += 1
            
            new_node = Node(new_group)
            node.nodes.append(new_node)
            
            node = new_node
            group = new_group
            continue
        pass
    return node

########NEW FILE########
__FILENAME__ = infoblock
#!/usr/bin/env python

'''
Classes and functions for the GroupInfo and EntryInfo blocks of a keepass file
'''

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import struct
import sys

# return tupleof (decode,encode) functions

def null_de(): return (lambda buf:None, lambda val:None)
def shunt_de(): return (lambda buf:buf, lambda val:val)

def ascii_de():
    from binascii import b2a_hex, a2b_hex
    return (lambda buf:b2a_hex(buf).replace('\0',''), 
            lambda val:a2b_hex(val)+'\0')

def string_de():
    return (lambda buf: buf.replace('\0',''), lambda val: val+'\0')

def short_de():
    return (lambda buf:struct.unpack("<H", buf)[0],
            lambda val:struct.pack("<H", val))

def int_de():
    return (lambda buf:struct.unpack("<I", buf)[0],
            lambda val:struct.pack("<I", val))

def date_de():
    from datetime import datetime
    def decode(buf):
        b = struct.unpack('<5B', buf)
        year = (b[0] << 6) | (b[1] >> 2);
        mon  = ((b[1] & 0b11)     << 2) | (b[2] >> 6);
        day  = ((b[2] & 0b111111) >> 1);
        hour = ((b[2] & 0b1)      << 4) | (b[3] >> 4);
        min  = ((b[3] & 0b1111)   << 2) | (b[4] >> 6);
        sec  = ((b[4] & 0b111111));
        return datetime(year, mon, day, hour, min, sec)

    def encode(val):
        year, mon, day, hour, min, sec = val.timetuple()[:6]
        b0 = 0x0000FFFF & ( (year>>6)&0x0000003F )
        b1 = 0x0000FFFF & ( ((year&0x0000003f)<<2) | ((mon>>2) & 0x00000003) )
        b2 = 0x0000FFFF & ( (( mon&0x00000003)<<6) | ((day&0x0000001F)<<1) \
                                | ((hour>>4)&0x00000001) )
        b3 = 0x0000FFFF & ( ((hour&0x0000000F)<<4) | ((min>>2)&0x0000000F) )
        b4 = 0x0000FFFF & ( (( min&0x00000003)<<6) | (sec&0x0000003F))
        return struct.pack('<5B',b0,b1,b2,b3,b4)
    return (decode,encode)

class InfoBase(object):
    'Base class for info type blocks'

    def __init__(self,format,string=None):
        self.format = format
        self.order = []         # keep field order
        if string: self.decode(string)
        return

    def __str__(self):
        ret = [self.__class__.__name__ + ':']
        for num,form in self.format.iteritems():
            try:
                value = self.__dict__[form[0]]
            except KeyError:
                continue
            ret.append('\t%s %s'%(form[0],value))
        return '\n'.join(ret)

    def decode(self,string):
        'Fill self from binary string'
        index = 0
        while True:
            substr = string[index:index+6]
            index += 6
            typ,siz = struct.unpack('<H I',substr)
            self.order.append((typ,siz))

            substr = string[index:index+siz]
            index += siz
            buf = struct.unpack('<%ds'%siz,substr)[0]

            name,decenc = self.format[typ]
            if name is None: break
            try:
                value = decenc[0](buf)
            except struct.error,msg:
                msg = '%s, typ = %d[%d] -> %s buf = "%s"'%\
                    (msg,typ,siz,self.format[typ],buf)
                raise struct.error,msg

            self.__dict__[name] = value
            continue
        return

    def __len__(self):
        length = 0
        for typ,siz in self.order:
            length += 2+4+siz
        return length

    def encode(self):
        'Return binary string representatoin'
        string = ""
        for typ,siz in self.order:
            if typ == 0xFFFF:   # end of block
                encoded = None
            else:
                name,decenc = self.format[typ]
                value = self.__dict__[name]
                encoded = decenc[1](value)
                pass
            buf = struct.pack('<H',typ)
            buf += struct.pack('<I',siz)
            if encoded is not None:
                buf += struct.pack('<%ds'%siz,encoded)
            string += buf
            continue
        return string

    pass



class GroupInfo(InfoBase):
    '''One group: [FIELDTYPE(FT)][FIELDSIZE(FS)][FIELDDATA(FD)]
           [FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)]...

[ 2 bytes] FIELDTYPE
[ 4 bytes] FIELDSIZE, size of FIELDDATA in bytes
[ n bytes] FIELDDATA, n = FIELDSIZE

Notes:
- Strings are stored in UTF-8 encoded form and are null-terminated.
- FIELDTYPE can be one of the following identifiers:
  * 0000: Invalid or comment block, block is ignored
  * 0001: Group ID, FIELDSIZE must be 4 bytes
          It can be any 32-bit value except 0 and 0xFFFFFFFF
  * 0002: Group name, FIELDDATA is an UTF-8 encoded string
  * 0003: Creation time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 0004: Last modification time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 0005: Last access time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 0006: Expiration time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 0007: Image ID, FIELDSIZE must be 4 bytes
  * 0008: Level, FIELDSIZE = 2
  * 0009: Flags, 32-bit value, FIELDSIZE = 4
  * FFFF: Group entry terminator, FIELDSIZE must be 0
  '''

    format = {
        0x0: ('ignored',null_de()),
        0x1: ('groupid',int_de()),
        0x2: ('group_name',string_de()),
        0x3: ('creation_time',date_de()),
        0x4: ('last_mod_time',date_de()),
        0x5: ('last_acc_time',date_de()),
        0x6: ('expiration_time',date_de()),
        0x7: ('imageid',int_de()),
        0x8: ('level',short_de()),      #size = 2
        0x9: ('flags',int_de()),
        0xFFFF: (None,None),
        }

    def __init__(self,string=None):
        super(GroupInfo,self).__init__(GroupInfo.format,string)
        return

    def name(self):
        'Return the group_name'
        return self.group_name

    pass

class EntryInfo(InfoBase):
    '''One entry: [FIELDTYPE(FT)][FIELDSIZE(FS)][FIELDDATA(FD)]
           [FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)]...

[ 2 bytes] FIELDTYPE
[ 4 bytes] FIELDSIZE, size of FIELDDATA in bytes
[ n bytes] FIELDDATA, n = FIELDSIZE

Notes:
- Strings are stored in UTF-8 encoded form and are null-terminated.
- FIELDTYPE can be one of the following identifiers:
  * 0000: Invalid or comment block, block is ignored
  * 0001: UUID, uniquely identifying an entry, FIELDSIZE must be 16
  * 0002: Group ID, identifying the group of the entry, FIELDSIZE = 4
          It can be any 32-bit value except 0 and 0xFFFFFFFF
  * 0003: Image ID, identifying the image/icon of the entry, FIELDSIZE = 4
  * 0004: Title of the entry, FIELDDATA is an UTF-8 encoded string
  * 0005: URL string, FIELDDATA is an UTF-8 encoded string
  * 0006: UserName string, FIELDDATA is an UTF-8 encoded string
  * 0007: Password string, FIELDDATA is an UTF-8 encoded string
  * 0008: Notes string, FIELDDATA is an UTF-8 encoded string
  * 0009: Creation time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 000A: Last modification time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 000B: Last access time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 000C: Expiration time, FIELDSIZE = 5, FIELDDATA = packed date/time
  * 000D: Binary description UTF-8 encoded string
  * 000E: Binary data
  * FFFF: Entry terminator, FIELDSIZE must be 0
  '''

    format = {
        0x0: ('ignored',null_de()),
        0x1: ('uuid',ascii_de()),        #size = 16 
        0x2: ('groupid',int_de()),       #size = 4
        0x3: ('imageid',int_de()),       #why size = 4??
        0x4: ('title',string_de()),      #syze = len+1
        0x5: ('url',string_de()),
        0x6: ('username',string_de()),
        0x7: ('password',string_de()),
        0x8: ('notes',string_de()),
        0x9: ('creation_time',date_de()), #size = 5 ?? always
        0xa: ('last_mod_time',date_de()),
        0xb: ('last_acc_time',date_de()),
        0xc: ('expiration_time',date_de()),
        0xd: ('binary_desc',string_de()),
        0xe: ('binary_data',shunt_de()),  #size ??  if None = 0?
        0xFFFF: (None,None),
        }

    def __init__(self,string=None):
        super(EntryInfo,self).__init__(EntryInfo.format,string)
        return

    def name(self):
        'Return the title'
        return self.title

    pass


########NEW FILE########
__FILENAME__ = kpdb
#!/usr/bin/env python
'''
KeePass v1 database file from Docs/DbFormat.txt of KeePass v1.

General structure:

[DBHDR][GROUPINFO][GROUPINFO][GROUPINFO]...[ENTRYINFO][ENTRYINFO][ENTRYINFO]...

[1x] Database header
[Nx] All groups
[Mx] All entries
'''

# This file is part of python-keepass and is Copyright (C) 2012 Brett Viren.
# 
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.

import sys, struct, os
import datetime
import uuid
import random
from copy import copy

from header import DBHDR
from infoblock import GroupInfo, EntryInfo

class Database(object):
    '''
    Access a KeePass DB file of format v3
    '''
    
    def __init__(self, filename = None, masterkey=""):
        self.masterkey = masterkey
        if filename:
            self.read(filename)
            return
        self.header = DBHDR()
        self.groups = []
        self.entries = []
        return

    def read(self,filename):
        'Read in given .kdb file'
        fp = open(filename)
        buf = fp.read()
        fp.close()

        headbuf = buf[:124]
        self.header = DBHDR(headbuf)
        self.groups = []
        self.entries = []

        payload = buf[124:]

        self.finalkey = self.final_key(self.masterkey,
                                       self.header.master_seed,
                                       self.header.master_seed2,
                                       self.header.key_enc_rounds)
        payload = self.decrypt_payload(payload, self.finalkey, 
                                       self.header.encryption_type(),
                                       self.header.encryption_iv)

        ngroups = self.header.ngroups
        while ngroups:
            gi = GroupInfo(payload)
            self.groups.append(gi)
            length = len(gi)
            payload = payload[length:]
            ngroups -= 1
            continue

        nentries = self.header.nentries
        while nentries:
            ei = EntryInfo(payload)
            self.entries.append(ei)
            payload = payload[len(ei):]
            nentries -= 1
            continue
        return

    def final_key(self,masterkey,masterseed,masterseed2,rounds):
        '''Munge masterkey into the final key for decryping payload by
        encrypting it for the given number of rounds masterseed2 and
        hashing it with masterseed.'''
        from Crypto.Cipher import AES
        import hashlib

        key = hashlib.sha256(masterkey).digest()
        cipher = AES.new(masterseed2,  AES.MODE_ECB)
        
        while rounds:
            rounds -= 1
            key = cipher.encrypt(key)
            continue
        key = hashlib.sha256(key).digest()
        return hashlib.sha256(masterseed + key).digest()

    def decrypt_payload(self, payload, finalkey, enctype, iv):
        'Decrypt payload (non-header) part of the buffer'

        if enctype != 'Rijndael':
            raise ValueError, 'Unsupported decryption type: "%s"'%enctype

        payload = self.decrypt_payload_aes_cbc(payload, finalkey, iv)
        crypto_size = len(payload)

        if ((crypto_size > 2147483446) or (not crypto_size and self.header.ngroups)):
            raise ValueError, "Decryption failed.\nThe key is wrong or the file is damaged"

        import hashlib
        if self.header.contents_hash != hashlib.sha256(payload).digest():
            raise ValueError, "Decryption failed. The file checksum did not match."

        return payload

    def decrypt_payload_aes_cbc(self, payload, finalkey, iv):
        'Decrypt payload buffer with AES CBC'

        from Crypto.Cipher import AES
        cipher = AES.new(finalkey, AES.MODE_CBC, iv)
        payload = cipher.decrypt(payload)
        extra = ord(payload[-1])
        payload = payload[:len(payload)-extra]
        return payload

    def encrypt_payload(self, payload, finalkey, enctype, iv):
        'Encrypt payload'
        if enctype != 'Rijndael':
            raise ValueError, 'Unsupported encryption type: "%s"'%enctype
        return self.encrypt_payload_aes_cbc(payload, finalkey, iv)

    def encrypt_payload_aes_cbc(self, payload, finalkey, iv):
        'Encrypt payload buffer with AES CBC'
        from Crypto.Cipher import AES
        cipher = AES.new(finalkey, AES.MODE_CBC, iv)
        # pad out and store amount as last value
        length = len(payload)
        encsize = (length/AES.block_size+1)*16
        padding = encsize - length
        for ind in range(padding):
            payload += chr(padding)
        return cipher.encrypt(payload)
        
    def __str__(self):
        ret = [str(self.header)]
        ret += map(str,self.groups)
        ret += map(str,self.entries)
        return '\n'.join(ret)

    def encode_payload(self):
        'Return encoded, plaintext groups+entries buffer'
        payload = ""
        for group in self.groups:
            payload += group.encode()
        for entry in self.entries:
            payload += entry.encode()
        return payload

    def write(self,filename,masterkey=""):
        '''' 
        Write out DB to given filename with optional master key.
        If no master key is given, the one used to create this DB is used.
        Resets IVs and master seeds.
        '''
        import hashlib

        header = copy(self.header)
        header.ngroups = len(self.groups)
        header.nentries = len(self.entries)
        header.reset_random_fields()

        payload = self.encode_payload()
        header.contents_hash = hashlib.sha256(payload).digest()

        finalkey = self.final_key(masterkey = masterkey or self.masterkey,
                                  masterseed = header.master_seed,
                                  masterseed2 = header.master_seed2,
                                  rounds = header.key_enc_rounds)

        payload = self.encrypt_payload(payload, finalkey, 
                                       header.encryption_type(),
                                       header.encryption_iv)

        fp = open(filename,'w')
        fp.write(header.encode())
        fp.write(payload)
        fp.close()
        return

    def group(self,field,value):
        'Return the group which has the given field and value'
        for group in self.groups:
            if group.__dict__[field] == value: return group
            continue
        return None

    def dump_entries(self,format,show_passwords=False):
        for ent in self.entries:
            group = self.group('groupid',ent.groupid)
            if not group:
                sys.stderr.write("Skipping missing group with ID %d\n"%
                                 ent.groupid)
                continue
            dat = dict(ent.__dict__) # copy
            if not show_passwords:
                dat['password'] = '****'
            for what in ['group_name','level']:
                nick = what
                if 'group' not in nick: nick = 'group_'+nick
                dat[nick] = group.__dict__[what]

            print format%dat
            continue
        return

    def hierarchy(self):
        '''Return database with groups and entries organized into a
        hierarchy'''
        from hier import Node

        top = Node()
        breadcrumb = [top]
        node_by_id = {None:top}
        for group in self.groups:
            n = Node(group)
            node_by_id[group.groupid] = n

            while group.level - breadcrumb[-1].level() != 1:
                pn = breadcrumb.pop()
                continue

            breadcrumb[-1].nodes.append(n)
            breadcrumb.append(n)
            continue

        for ent in self.entries:
            n = node_by_id[ent.groupid]
            n.entries.append(ent)

        return top
    
    def update_by_hierarchy(self, hierarchy):
        '''
        Update the database using the given hierarchy.  
        This replaces the existing groups and entries.
        '''
        import hier
        collector = hier.CollectVisitor()
        hier.visit(hierarchy, collector)
        self.groups = collector.groups
        self.entries = collector.entries
        return
    
    def gen_groupid(self):
        """
        Generate a new groupid (4-byte value that isn't 0 or 0xffffffff).
        """
        existing_groupids = {group.groupid for group in self.groups}
        if len(existing_groupids) >= 0xfffffffe:
            raise Exception("All groupids are in use!")
        while True:
            groupid = random.randint(1, 0xfffffffe) # 0 and 0xffffffff are reserved
            if groupid not in existing_groupids:
                return groupid
    
    def update_entry(self,title,username,url,notes="",new_title=None,new_username=None,new_password=None,new_url=None,new_notes=None):
        for entry in self.entries:
            if entry.title == str(title) and entry.username == str(username) and entry.url == str(url):
                if new_title: entry.title = new_title
                if new_username: entry.username = new_username
                if new_password: entry.password = new_password
                if new_url: entry.url = new_url
                if new_notes: entry.notes = new_notes
                entry.new_entry.last_mod_time = datetime.datetime.now()

    def add_entry(self,path,title,username,password,url="",notes="",imageid=1,append=True):
        '''
        Add an entry to the current database at with given values.  If
        append is False a pre-existing entry that matches path, title
        and username will be overwritten with the new one.
        '''
        import hier, infoblock

        top = self.hierarchy()
        node = hier.mkdir(top, path, self.gen_groupid)

        # fixme, this should probably be moved into a new constructor
        def make_entry():
            new_entry = infoblock.EntryInfo()
            new_entry.uuid = uuid.uuid4().hex
            new_entry.groupid = node.group.groupid
            new_entry.imageid = imageid
            new_entry.title = title
            new_entry.url = url
            new_entry.username = username
            new_entry.password = password
            new_entry.notes = notes
            new_entry.creation_time = datetime.datetime.now() 
            new_entry.last_mod_time = datetime.datetime.now() 
            new_entry.last_acc_time = datetime.datetime.now() 
            new_entry.expiration_time = datetime.datetime(2999, 12, 28, 23, 59, 59) # KeePassX 0.4.3 default
            new_entry.binary_desc = ""
            new_entry.binary_data = None
            new_entry.order = [(1, 16), 
			       (2, 4), 
			       (3, 4), 
			       (4, len(title) + 1), 
			       (5, len(url) + 1), 
			       (6, len(username) + 1), 
			       (7, len(password) + 1), 
			       (8, len(notes) + 1), 
			       (9, 5), 
			       (10, 5), 
			       (11, 5), 
			       (12, 5), 
			       (13, len(new_entry.binary_desc) + 1), 
			       (14, 0), 
			       (65535, 0)]
            #new_entry.None = None
            #fixme, deal with times
            return new_entry
        
        existing_node_updated = False
        if not append:
            for i, ent in enumerate(node.entries):
                if ent.title != title: continue
                if ent.username != username: continue
                node.entries[i] = make_entry()
                existing_node_updated = True
                break
        
        if not existing_node_updated:
            node.entries.append(make_entry())
        
        self.update_by_hierarchy(top)

    def remove_entry(self, username, url):
        for entry in self.entries:
            if entry.username == str(username) and entry.url == str(url):
                self.entries.remove(entry)

    def remove_group(self, path, level=None):
        for group in self.groups:
            if group.group_name == str(path):
                if level:
                    if group.level == level:
                        self.groups.remove(group)
                        for entry in self.entries:
                            if entry.groupid == group.groupid:
                                self.entries.remove(entry)
                else:
                    self.groups.remove(group)
                    for entry in self.entries:
                        if entry.groupid == group.groupid:
                            self.entries.remove(entry)


    pass


########NEW FILE########
__FILENAME__ = test_cli
from keepass import cli

def test_parse_args():
    main = cli.Cli(['-a', '-b', '-c', 'open', '-a', '-b', '-c', 'foo'])
    assert main.command_line == [['general', ['-a', '-b', '-c']], 
                                 ['open', ['-a', '-b', '-c', 'foo']]]

########NEW FILE########
__FILENAME__ = test_de
'''
Test encode/decode functions
'''

from keepass import infoblock as ib

def test_null():
    dec,enc = ib.null_de()
    assert dec('\x42') is None
    assert enc(69) is None

def test_shunt():
    dec,enc = ib.shunt_de()
    assert dec('\x42') is '\x42'
    assert enc('foo') is 'foo'

def test_string():
    strings = ['foo','to encrypt or to decrypt, that is the ?','new\nline']
    dec,enc = ib.string_de()
    for string in strings:
        assert string == dec(enc(string))

########NEW FILE########
__FILENAME__ = test_hier
from keepass import hier

class GroupIDGenerator(object):
    def __init__(self):
        self.groupid = 0
    
    def gen_groupid(self):
        self.groupid += 1
        return self.groupid

def test_hierarchy():
    top = hier.Node()
    hier.mkdir(top, 'SubDir/SubSubDir', GroupIDGenerator().gen_groupid)
    dumper = hier.NodeDumper()
    hier.walk(top,dumper)


# filename = sys.argv[1]
# masterkey  = sys.argv[2]
# db = kpdb.Database(filename,masterkey)
# h = db.hierarchy()
# print h

# path = sys.argv[3]
# # obj = h.get(path)
# # print path,' --> ',obj

# from keepass import hier
# visitor = hier.PathVisitor(path,False)
# obj = hier.walk(h,visitor)
# print 'results for',path
# for res in visitor.results():
#     print res
# print 'best match:',visitor.best_match
# print 'remaining path:',visitor.path

# visitor= hier.CollectVisitor()
# hier.walk(h,visitor)
# print 'Groups:'
# for g in visitor.groups:
#     print '\t',g.name(),g.groupid
# print 'Entries:'
# for e in visitor.entries:
#     print '\t',e.name(),e.groupid

########NEW FILE########
__FILENAME__ = test_io
import tempfile
import shutil
import os

import keepass.kpdb

def test_write():
    """
    Try to create a file and then read it back in.
    """
    password = 'REINDEER FLOTILLA'
    tempdir = tempfile.mkdtemp()
    kdb_path = os.path.join(tempdir, 'test_write.kdb')
    try:
        db = keepass.kpdb.Database()
        db.add_entry(path='Secrets/Terrible', title='Gonk', username='foo', password='bar', url='https://example.org/')
        assert len(db.groups)  == 2
        assert len(db.entries) == 1
        db.write(kdb_path, password)
        assert os.path.isfile(kdb_path)
        
        db2 = keepass.kpdb.Database(kdb_path, password)
        assert len(db.groups)  == 2
        assert len(db.entries) == 1
        assert db.entries[0].name() == 'Gonk'
        
    finally:
        shutil.rmtree(tempdir)

########NEW FILE########
