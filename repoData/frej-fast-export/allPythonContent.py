__FILENAME__ = hg-fast-export
#!/usr/bin/env python

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import node
from hg2git import setup_repo,fixup_user,get_branch,get_changeset
from hg2git import load_cache,save_cache,get_git_sha1,set_default_branch,set_origin_name
from optparse import OptionParser
import re
import sys
import os

if sys.platform == "win32":
  # On Windows, sys.stdout is initially opened in text mode, which means that
  # when a LF (\n) character is written to sys.stdout, it will be converted
  # into CRLF (\r\n).  That makes git blow up, so use this platform-specific
  # code to change the mode of sys.stdout to binary.
  import msvcrt
  msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

# silly regex to catch Signed-off-by lines in log message
sob_re=re.compile('^Signed-[Oo]ff-[Bb]y: (.+)$')
# insert 'checkpoint' command after this many commits or none at all if 0
cfg_checkpoint_count=0
# write some progress message every this many file contents written
cfg_export_boundary=1000

def gitmode(flags):
  return 'l' in flags and '120000' or 'x' in flags and '100755' or '100644'

def wr_no_nl(msg=''):
  if msg:
    sys.stdout.write(msg)

def wr(msg=''):
  wr_no_nl(msg)
  sys.stdout.write('\n')
  #map(lambda x: sys.stderr.write('\t[%s]\n' % x),msg.split('\n'))

def checkpoint(count):
  count=count+1
  if cfg_checkpoint_count>0 and count%cfg_checkpoint_count==0:
    sys.stderr.write("Checkpoint after %d commits\n" % count)
    wr('checkpoint')
    wr()
  return count

def revnum_to_revref(rev, old_marks):
  """Convert an hg revnum to a git-fast-import rev reference (an SHA1
  or a mark)"""
  return old_marks.get(rev) or ':%d' % (rev+1)

def file_mismatch(f1,f2):
  """See if two revisions of a file are not equal."""
  return node.hex(f1)!=node.hex(f2)

def split_dict(dleft,dright,l=[],c=[],r=[],match=file_mismatch):
  """Loop over our repository and find all changed and missing files."""
  for left in dleft.keys():
    right=dright.get(left,None)
    if right==None:
      # we have the file but our parent hasn't: add to left set
      l.append(left)
    elif match(dleft[left],right) or gitmode(dleft.flags(left))!=gitmode(dright.flags(left)):
      # we have it but checksums mismatch: add to center set
      c.append(left)
  for right in dright.keys():
    left=dleft.get(right,None)
    if left==None:
      # if parent has file but we don't: add to right set
      r.append(right)
    # change is already handled when comparing child against parent
  return l,c,r

def get_filechanges(repo,revision,parents,mleft):
  """Given some repository and revision, find all changed/deleted files."""
  l,c,r=[],[],[]
  for p in parents:
    if p<0: continue
    mright=repo.changectx(p).manifest()
    l,c,r=split_dict(mleft,mright,l,c,r)
  l.sort()
  c.sort()
  r.sort()
  return l,c,r

def get_author(logmessage,committer,authors):
  """As git distincts between author and committer of a patch, try to
  extract author by detecting Signed-off-by lines.

  This walks from the end of the log message towards the top skipping
  empty lines. Upon the first non-empty line, it walks all Signed-off-by
  lines upwards to find the first one. For that (if found), it extracts
  authorship information the usual way (authors table, cleaning, etc.)

  If no Signed-off-by line is found, this defaults to the committer.

  This may sound stupid (and it somehow is), but in log messages we
  accidentially may have lines in the middle starting with
  "Signed-off-by: foo" and thus matching our detection regex. Prevent
  that."""

  loglines=logmessage.split('\n')
  i=len(loglines)
  # from tail walk to top skipping empty lines
  while i>=0:
    i-=1
    if len(loglines[i].strip())==0: continue
    break
  if i>=0:
    # walk further upwards to find first sob line, store in 'first'
    first=None
    while i>=0:
      m=sob_re.match(loglines[i])
      if m==None: break
      first=m
      i-=1
    # if the last non-empty line matches our Signed-Off-by regex: extract username
    if first!=None:
      r=fixup_user(first.group(1),authors)
      return r
  return committer

def export_file_contents(ctx,manifest,files,hgtags):
  count=0
  max=len(files)
  for file in files:
    # Skip .hgtags files. They only get us in trouble.
    if not hgtags and file == ".hgtags":
      sys.stderr.write('Skip %s\n' % (file))
      continue
    d=ctx.filectx(file).data()
    wr('M %s inline %s' % (gitmode(manifest.flags(file)),file))
    wr('data %d' % len(d)) # had some trouble with size()
    wr(d)
    count+=1
    if count%cfg_export_boundary==0:
      sys.stderr.write('Exported %d/%d files\n' % (count,max))
  if max>cfg_export_boundary:
    sys.stderr.write('Exported %d/%d files\n' % (count,max))

def sanitize_name(name,what="branch"):
  """Sanitize input roughly according to git-check-ref-format(1)"""

  def dot(name):
    if name[0] == '.': return '_'+name[1:]
    return name

  n=name
  p=re.compile('([[ ~^:?\\\\*]|\.\.)')
  n=p.sub('_', n)
  if n[-1] in ('/', '.'): n=n[:-1]+'_'
  n='/'.join(map(dot,n.split('/')))
  p=re.compile('_+')
  n=p.sub('_', n)

  if n!=name:
    sys.stderr.write('Warning: sanitized %s [%s] to [%s]\n' % (what,name,n))
  return n

def export_commit(ui,repo,revision,old_marks,max,count,authors,sob,brmap,hgtags,notes):
  def get_branchname(name):
    if brmap.has_key(name):
      return brmap[name]
    n=sanitize_name(name)
    brmap[name]=n
    return n

  (revnode,_,user,(time,timezone),files,desc,branch,_)=get_changeset(ui,repo,revision,authors)

  branch=get_branchname(branch)

  parents = [p for p in repo.changelog.parentrevs(revision) if p >= 0]

  if len(parents)==0 and revision != 0:
    wr('reset refs/heads/%s' % branch)

  wr('commit refs/heads/%s' % branch)
  wr('mark :%d' % (revision+1))
  if sob:
    wr('author %s %d %s' % (get_author(desc,user,authors),time,timezone))
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data %d' % (len(desc)+1)) # wtf?
  wr(desc)
  wr()

  ctx=repo.changectx(str(revision))
  man=ctx.manifest()
  added,changed,removed,type=[],[],[],''

  if len(parents) == 0:
    # first revision: feed in full manifest
    added=man.keys()
    added.sort()
    type='full'
  else:
    wr('from %s' % revnum_to_revref(parents[0], old_marks))
    if len(parents) == 1:
      # later non-merge revision: feed in changed manifest
      # if we have exactly one parent, just take the changes from the
      # manifest without expensively comparing checksums
      f=repo.status(repo.lookup(parents[0]),revnode)[:3]
      added,changed,removed=f[1],f[0],f[2]
      type='simple delta'
    else: # a merge with two parents
      wr('merge %s' % revnum_to_revref(parents[1], old_marks))
      # later merge revision: feed in changed manifest
      # for many files comparing checksums is expensive so only do it for
      # merges where we really need it due to hg's revlog logic
      added,changed,removed=get_filechanges(repo,revision,parents,man)
      type='thorough delta'

  sys.stderr.write('%s: Exporting %s revision %d/%d with %d/%d/%d added/changed/removed files\n' %
      (branch,type,revision+1,max,len(added),len(changed),len(removed)))

  map(lambda r: wr('D %s' % r),removed)
  export_file_contents(ctx,man,added,hgtags)
  export_file_contents(ctx,man,changed,hgtags)
  wr()

  count=checkpoint(count)
  count=generate_note(user,time,timezone,revision,ctx,count,notes)
  return count

def generate_note(user,time,timezone,revision,ctx,count,notes):
  if not notes:
    return count
  wr('commit refs/notes/hg')
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data 0')
  wr('N inline :%d' % (revision+1))
  hg_hash=ctx.hex()
  wr('data %d' % (len(hg_hash)))
  wr_no_nl(hg_hash)
  wr()
  return checkpoint(count)
  
def export_tags(ui,repo,old_marks,mapping_cache,count,authors):
  l=repo.tagslist()
  for tag,node in l:
    tag=sanitize_name(tag,"tag")
    # ignore latest revision
    if tag=='tip': continue
    # ignore tags to nodes that are missing (ie, 'in the future')
    if node.encode('hex_codec') not in mapping_cache:
      sys.stderr.write('Tag %s refers to unseen node %s\n' % (tag, node.encode('hex_codec')))
      continue

    rev=int(mapping_cache[node.encode('hex_codec')])

    ref=revnum_to_revref(rev, old_marks)
    if ref==None:
      sys.stderr.write('Failed to find reference for creating tag'
          ' %s at r%d\n' % (tag,rev))
      continue
    sys.stderr.write('Exporting tag [%s] at [hg r%d] [git %s]\n' % (tag,rev,ref))
    wr('reset refs/tags/%s' % tag)
    wr('from %s' % ref)
    wr()
    count=checkpoint(count)
  return count

def load_authors(filename):
  cache={}
  if not os.path.exists(filename):
    return cache
  f=open(filename,'r')
  l=0
  a=0
  lre=re.compile('^([^=]+)[ ]*=[ ]*(.+)$')
  for line in f.readlines():
    l+=1
    line=line.strip()
    if line=='' or line[0]=='#':
      continue
    m=lre.match(line)
    if m==None:
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[m.group(1).strip()]=m.group(2).strip()
    a+=1
  f.close()
  sys.stderr.write('Loaded %d authors\n' % a)
  return cache

def branchtip(repo, heads):
  '''return the tipmost branch head in heads'''
  tip = heads[-1]
  for h in reversed(heads):
    if 'close' not in repo.changelog.read(h)[5]:
      tip = h
      break
  return tip

def verify_heads(ui,repo,cache,force):
  branches={}
  for bn, heads in repo.branchmap().iteritems():
    branches[bn] = branchtip(repo, heads)
  l=[(-repo.changelog.rev(n), n, t) for t, n in branches.items()]
  l.sort()

  # get list of hg's branches to verify, don't take all git has
  for _,_,b in l:
    b=get_branch(b)
    sha1=get_git_sha1(b)
    c=cache.get(b)
    if sha1!=c:
      sys.stderr.write('Error: Branch [%s] modified outside hg-fast-export:'
        '\n%s (repo) != %s (cache)\n' % (b,sha1,c))
      if not force: return False

  # verify that branch has exactly one head
  t={}
  for h in repo.heads():
    (_,_,_,_,_,_,branch,_)=get_changeset(ui,repo,h)
    if t.get(branch,False):
      sys.stderr.write('Error: repository has at least one unnamed head: hg r%s\n' %
          repo.changelog.rev(h))
      if not force: return False
    t[branch]=True

  return True

def hg2git(repourl,m,marksfile,mappingfile,headsfile,tipfile,authors={},sob=False,force=False,hgtags=False,notes=False):
  _max=int(m)

  old_marks=load_cache(marksfile,lambda s: int(s)-1)
  mapping_cache=load_cache(mappingfile)
  heads_cache=load_cache(headsfile)
  state_cache=load_cache(tipfile)

  ui,repo=setup_repo(repourl)

  if not verify_heads(ui,repo,heads_cache,force):
    return 1

  try:
    tip=repo.changelog.count()
  except AttributeError:
    tip=len(repo)

  min=int(state_cache.get('tip',0))
  max=_max
  if _max<0 or max>tip:
    max=tip

  for rev in range(0,max):
  	(revnode,_,_,_,_,_,_,_)=get_changeset(ui,repo,rev,authors)
  	mapping_cache[revnode.encode('hex_codec')] = str(rev)


  c=0
  brmap={}
  for rev in range(min,max):
    c=export_commit(ui,repo,rev,old_marks,max,c,authors,sob,brmap,hgtags,notes)

  state_cache['tip']=max
  state_cache['repo']=repourl
  save_cache(tipfile,state_cache)
  save_cache(mappingfile,mapping_cache)

  c=export_tags(ui,repo,old_marks,mapping_cache,c,authors)

  sys.stderr.write('Issued %d commands\n' % c)

  return 0

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No %s option given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("-m","--max",type="int",dest="max",
      help="Maximum hg revision to import")
  parser.add_option("--mapping",dest="mappingfile",
      help="File to read last run's hg-to-git SHA1 mapping")
  parser.add_option("--marks",dest="marksfile",
      help="File to read git-fast-import's marks from")
  parser.add_option("--heads",dest="headsfile",
      help="File to read last run's git heads from")
  parser.add_option("--status",dest="statusfile",
      help="File to read status from")
  parser.add_option("-r","--repo",dest="repourl",
      help="URL of repo to import")
  parser.add_option("-s",action="store_true",dest="sob",
      default=False,help="Enable parsing Signed-off-by lines")
  parser.add_option("--hgtags",action="store_true",dest="hgtags",
      default=False,help="Enable exporting .hgtags files")
  parser.add_option("-A","--authors",dest="authorfile",
      help="Read authormap from AUTHORFILE")
  parser.add_option("-f","--force",action="store_true",dest="force",
      default=False,help="Ignore validation errors by force")
  parser.add_option("-M","--default-branch",dest="default_branch",
      help="Set the default branch")
  parser.add_option("-o","--origin",dest="origin_name",
      help="use <name> as namespace to track upstream")
  parser.add_option("--hg-hash",action="store_true",dest="notes",
      default=False,help="Annotate commits with the hg hash as git notes in the hg namespace")

  (options,args)=parser.parse_args()

  m=-1
  if options.max!=None: m=options.max

  if options.marksfile==None: bail(parser,'--marks')
  if options.mappingfile==None: bail(parser,'--mapping')
  if options.headsfile==None: bail(parser,'--heads')
  if options.statusfile==None: bail(parser,'--status')
  if options.repourl==None: bail(parser,'--repo')

  a={}
  if options.authorfile!=None:
    a=load_authors(options.authorfile)

  if options.default_branch!=None:
    set_default_branch(options.default_branch)

  if options.origin_name!=None:
    set_origin_name(options.origin_name)

  sys.exit(hg2git(options.repourl,m,options.marksfile,options.mappingfile,options.headsfile,
    options.statusfile,authors=a,sob=options.sob,force=options.force,hgtags=options.hgtags,notes=options.notes))

########NEW FILE########
__FILENAME__ = hg-reset
#!/usr/bin/env python

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: GPLv2

from mercurial import node
from hg2git import setup_repo,load_cache,get_changeset,get_git_sha1
from optparse import OptionParser
import sys

def heads(ui,repo,start=None,stop=None,max=None):
  # this is copied from mercurial/revlog.py and differs only in
  # accepting a max argument for xrange(startrev+1,...) defaulting
  # to the original repo.changelog.count()
  if start is None:
    start = node.nullid
  if stop is None:
    stop = []
  if max is None:
    max = repo.changelog.count()
  stoprevs = dict.fromkeys([repo.changelog.rev(n) for n in stop])
  startrev = repo.changelog.rev(start)
  reachable = {startrev: 1}
  heads = {startrev: 1}

  parentrevs = repo.changelog.parentrevs
  for r in xrange(startrev + 1, max):
    for p in parentrevs(r):
      if p in reachable:
        if r not in stoprevs:
          reachable[r] = 1
        heads[r] = 1
      if p in heads and p not in stoprevs:
        del heads[p]

  return [(repo.changelog.node(r),str(r)) for r in heads]

def get_branches(ui,repo,heads_cache,marks_cache,mapping_cache,max):
  h=heads(ui,repo,max=max)
  stale=dict.fromkeys(heads_cache)
  changed=[]
  unchanged=[]
  for node,rev in h:
    _,_,user,(_,_),_,desc,branch,_=get_changeset(ui,repo,rev)
    del stale[branch]
    git_sha1=get_git_sha1(branch)
    cache_sha1=marks_cache.get(str(int(rev)+1))
    if git_sha1!=None and git_sha1==cache_sha1:
      unchanged.append([branch,cache_sha1,rev,desc.split('\n')[0],user])
    else:
      changed.append([branch,cache_sha1,rev,desc.split('\n')[0],user])
  changed.sort()
  unchanged.sort()
  return stale,changed,unchanged

def get_tags(ui,repo,marks_cache,mapping_cache,max):
  l=repo.tagslist()
  good,bad=[],[]
  for tag,node in l:
    if tag=='tip': continue
    rev=int(mapping_cache[node.encode('hex_codec')])
    cache_sha1=marks_cache.get(str(int(rev)+1))
    _,_,user,(_,_),_,desc,branch,_=get_changeset(ui,repo,rev)
    if int(rev)>int(max):
      bad.append([tag,branch,cache_sha1,rev,desc.split('\n')[0],user])
    else:
      good.append([tag,branch,cache_sha1,rev,desc.split('\n')[0],user])
  good.sort()
  bad.sort()
  return good,bad

def mangle_mark(mark):
  return str(int(mark)-1)

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No option %s given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("--marks",dest="marksfile",
      help="File to read git-fast-import's marks from")
  parser.add_option("--mapping",dest="mappingfile",
      help="File to read last run's hg-to-git SHA1 mapping")
  parser.add_option("--heads",dest="headsfile",
      help="File to read last run's git heads from")
  parser.add_option("--status",dest="statusfile",
      help="File to read status from")
  parser.add_option("-r","--repo",dest="repourl",
      help="URL of repo to import")
  parser.add_option("-R","--revision",type=int,dest="revision",
      help="Revision to reset to")

  (options,args)=parser.parse_args()

  if options.marksfile==None: bail(parser,'--marks option')
  if options.mappingfile==None: bail(parser,'--mapping option')
  if options.headsfile==None: bail(parser,'--heads option')
  if options.statusfile==None: bail(parser,'--status option')
  if options.repourl==None: bail(parser,'--repo option')
  if options.revision==None: bail(parser,'-R/--revision')

  heads_cache=load_cache(options.headsfile)
  marks_cache=load_cache(options.marksfile,mangle_mark)
  state_cache=load_cache(options.statusfile)
  mapping_cache = load_cache(options.mappingfile)

  l=int(state_cache.get('tip',options.revision))
  if options.revision+1>l:
    sys.stderr.write('Revision is beyond last revision imported: %d>%d\n' % (options.revision,l))
    sys.exit(1)

  ui,repo=setup_repo(options.repourl)

  stale,changed,unchanged=get_branches(ui,repo,heads_cache,marks_cache,mapping_cache,options.revision+1)
  good,bad=get_tags(ui,repo,marks_cache,mapping_cache,options.revision+1)

  print "Possibly stale branches:"
  map(lambda b: sys.stdout.write('\t%s\n' % b),stale.keys())

  print "Possibly stale tags:"
  map(lambda b: sys.stdout.write('\t%s on %s (r%s)\n' % (b[0],b[1],b[3])),bad)

  print "Unchanged branches:"
  map(lambda b: sys.stdout.write('\t%s (r%s)\n' % (b[0],b[2])),unchanged)

  print "Unchanged tags:"
  map(lambda b: sys.stdout.write('\t%s on %s (r%s)\n' % (b[0],b[1],b[3])),good)

  print "Reset branches in '%s' to:" % options.headsfile
  map(lambda b: sys.stdout.write('\t:%s %s\n\t\t(r%s: %s: %s)\n' % (b[0],b[1],b[2],b[4],b[3])),changed)

  print "Reset ':tip' in '%s' to '%d'" % (options.statusfile,options.revision)

########NEW FILE########
__FILENAME__ = hg2git
#!/usr/bin/env python

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import hg,util,ui,templatefilters
import re
import os
import sys

# default git branch name
cfg_master='master'
# default origin name
origin_name=''
# silly regex to see if user field has email address
user_re=re.compile('([^<]+) (<[^>]*>)$')
# silly regex to clean out user names
user_clean_re=re.compile('^["]([^"]+)["]$')

def set_default_branch(name):
  global cfg_master
  cfg_master = name

def set_origin_name(name):
  global origin_name
  origin_name = name

def setup_repo(url):
  try:
    myui=ui.ui(interactive=False)
  except TypeError:
    myui=ui.ui()
    myui.setconfig('ui', 'interactive', 'off')
  return myui,hg.repository(myui,url)

def fixup_user(user,authors):
  user=user.strip("\"")
  if authors!=None:
    # if we have an authors table, try to get mapping
    # by defaulting to the current value of 'user'
    user=authors.get(user,user)
  name,mail,m='','',user_re.match(user)
  if m==None:
    # if we don't have 'Name <mail>' syntax, extract name
    # and mail from hg helpers. this seems to work pretty well.
    # if email doesn't contain @, replace it with devnull@localhost
    name=templatefilters.person(user)
    mail='<%s>' % util.email(user)
    if '@' not in mail:
      mail = '<devnull@localhost>'
  else:
    # if we have 'Name <mail>' syntax, everything is fine :)
    name,mail=m.group(1),m.group(2)

  # remove any silly quoting from username
  m2=user_clean_re.match(name)
  if m2!=None:
    name=m2.group(1)
  return '%s %s' % (name,mail)

def get_branch(name):
  # 'HEAD' is the result of a bug in mutt's cvs->hg conversion,
  # other CVS imports may need it, too
  if name=='HEAD' or name=='default' or name=='':
    name=cfg_master
  if origin_name:
    return origin_name + '/' + name
  return name

def get_changeset(ui,repo,revision,authors={}):
  node=repo.lookup(revision)
  (manifest,user,(time,timezone),files,desc,extra)=repo.changelog.read(node)
  tz="%+03d%02d" % (-timezone / 3600, ((-timezone % 3600) / 60))
  branch=get_branch(extra.get('branch','master'))
  return (node,manifest,fixup_user(user,authors),(time,tz),files,desc,branch,extra)

def mangle_key(key):
  return key

def load_cache(filename,get_key=mangle_key):
  cache={}
  if not os.path.exists(filename):
    return cache
  f=open(filename,'r')
  l=0
  for line in f.readlines():
    l+=1
    fields=line.split(' ')
    if fields==None or not len(fields)==2 or fields[0][0]!=':':
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[get_key(fields[0][1:])]=fields[1].split('\n')[0]
  f.close()
  return cache

def save_cache(filename,cache):
  f=open(filename,'w+')
  map(lambda x: f.write(':%s %s\n' % (str(x),str(cache.get(x)))),cache.keys())
  f.close()

def get_git_sha1(name,type='heads'):
  try:
    # use git-rev-parse to support packed refs
    cmd="git rev-parse --verify refs/%s/%s 2>%s" % (type,name,os.devnull)
    p=os.popen(cmd)
    l=p.readline()
    p.close()
    if l == None or len(l) == 0:
      return None
    return l[0:40]
  except IOError:
    return None

########NEW FILE########
__FILENAME__ = svn-fast-export
#!/usr/bin/python
#
# svn-fast-export.py
# ----------
#  Walk through each revision of a local Subversion repository and export it
#  in a stream that git-fast-import can consume.
#
# Author: Chris Lee <clee@kde.org>
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

trunk_path = '/trunk/'
branches_path = '/branches/'
tags_path = '/tags/'

first_rev = 1
final_rev = 0

import sys, os.path
from optparse import OptionParser
from time import mktime, strptime
from svn.fs import svn_fs_file_length, svn_fs_file_contents, svn_fs_is_dir, svn_fs_revision_root, svn_fs_youngest_rev, svn_fs_revision_proplist, svn_fs_paths_changed
from svn.core import svn_pool_create, svn_pool_clear, svn_pool_destroy, svn_stream_for_stdout, svn_stream_copy, svn_stream_close, run_app
from svn.repos import svn_repos_open, svn_repos_fs

ct_short = ['M', 'A', 'D', 'R', 'X']

def dump_file_blob(root, full_path, pool):
    stream_length = svn_fs_file_length(root, full_path, pool)
    stream = svn_fs_file_contents(root, full_path, pool)
    sys.stdout.write("data %s\n" % stream_length)
    sys.stdout.flush()
    ostream = svn_stream_for_stdout(pool)
    svn_stream_copy(stream, ostream, pool)
    svn_stream_close(ostream)
    sys.stdout.write("\n")


def export_revision(rev, repo, fs, pool):
    sys.stderr.write("Exporting revision %s... " % rev)

    revpool = svn_pool_create(pool)
    svn_pool_clear(revpool)

    # Open a root object representing the youngest (HEAD) revision.
    root = svn_fs_revision_root(fs, rev, revpool)

    # And the list of what changed in this revision.
    changes = svn_fs_paths_changed(root, revpool)

    i = 1
    marks = {}
    file_changes = []

    for path, change_type in changes.iteritems():
        c_t = ct_short[change_type.change_kind]
        if svn_fs_is_dir(root, path, revpool):
            continue

        if not path.startswith(trunk_path):
            # We don't handle branches. Or tags. Yet.
            pass
        else:
            if c_t == 'D':
                file_changes.append("D %s" % path.replace(trunk_path, ''))
            else:
                marks[i] = path.replace(trunk_path, '')
                file_changes.append("M 644 :%s %s" % (i, marks[i]))
                sys.stdout.write("blob\nmark :%s\n" % i)
                dump_file_blob(root, path, revpool)
                i += 1

    # Get the commit author and message
    props = svn_fs_revision_proplist(fs, rev, revpool)

    # Do the recursive crawl.
    if props.has_key('svn:author'):
        author = "%s <%s@localhost>" % (props['svn:author'], props['svn:author'])
    else:
        author = 'nobody <nobody@localhost>'

    if len(file_changes) == 0:
        svn_pool_destroy(revpool)
        sys.stderr.write("skipping.\n")
        return

    svndate = props['svn:date'][0:-8]
    commit_time = mktime(strptime(svndate, '%Y-%m-%dT%H:%M:%S'))
    sys.stdout.write("commit refs/heads/master\n")
    sys.stdout.write("committer %s %s -0000\n" % (author, int(commit_time)))
    sys.stdout.write("data %s\n" % len(props['svn:log']))
    sys.stdout.write(props['svn:log'])
    sys.stdout.write("\n")
    sys.stdout.write('\n'.join(file_changes))
    sys.stdout.write("\n\n")

    svn_pool_destroy(revpool)

    sys.stderr.write("done!\n")

    #if rev % 1000 == 0:
    #    sys.stderr.write("gc: %s objects\n" % len(gc.get_objects()))
    #    sleep(5)


def crawl_revisions(pool, repos_path):
    """Open the repository at REPOS_PATH, and recursively crawl all its
    revisions."""
    global final_rev

    # Open the repository at REPOS_PATH, and get a reference to its
    # versioning filesystem.
    repos_obj = svn_repos_open(repos_path, pool)
    fs_obj = svn_repos_fs(repos_obj)

    # Query the current youngest revision.
    youngest_rev = svn_fs_youngest_rev(fs_obj, pool)


    first_rev = 1
    if final_rev == 0:
        final_rev = youngest_rev
    for rev in xrange(first_rev, final_rev + 1):
        export_revision(rev, repos_obj, fs_obj, pool)


if __name__ == '__main__':
    usage = '%prog [options] REPOS_PATH'
    parser = OptionParser()
    parser.set_usage(usage)
    parser.add_option('-f', '--final-rev', help='Final revision to import', 
                      dest='final_rev', metavar='FINAL_REV', type='int')
    parser.add_option('-t', '--trunk-path', help='Path in repo to /trunk',
                      dest='trunk_path', metavar='TRUNK_PATH')
    parser.add_option('-b', '--branches-path', help='Path in repo to /branches',
                      dest='branches_path', metavar='BRANCHES_PATH')
    parser.add_option('-T', '--tags-path', help='Path in repo to /tags',
                      dest='tags_path', metavar='TAGS_PATH')
    (options, args) = parser.parse_args()

    if options.trunk_path != None:
        trunk_path = options.trunk_path
    if options.branches_path != None:
        branches_path = options.branches_path
    if options.tags_path != None:
        tags_path = options.tags_path
    if options.final_rev != None:
        final_rev = options.final_rev

    if len(args) != 1:
        parser.print_help()
        sys.exit(2)

    # Canonicalize (enough for Subversion, at least) the repository path.
    repos_path = os.path.normpath(args[0])
    if repos_path == '.': 
        repos_path = ''

    # Call the app-wrapper, which takes care of APR initialization/shutdown
    # and the creation and cleanup of our top-level memory pool.
    run_app(crawl_revisions, repos_path)

########NEW FILE########
