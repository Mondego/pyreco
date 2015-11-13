__FILENAME__ = gitmmd2pdf
import getopt, os, sys
"""
This script processes an opencompute multimarkdown file and converts it into a multipage pdf

(c) Copyright Facebook, Inc. 2011. All rights reserved.

"""

repos=["",""]

def sync(path, url, repo_name):
    p = os.path.join(path, repo_name) + ".git"
    print("Synching %s -> %s" % (repo_name, p))
    if not os.path.exists(p):
          subprocess.call(['git','clone',url,p])

if __name__ == "__main__":
  try:
    opts, args = getopt.getopt(sys.argv[1:],"f:hg",["file","help","git"])
  except getopt.GetoptError, err:
    print str(err)
    usage()
    sys.exit(2)

  mmdcmd='mmd2tex '
  pdfcmd='xelatex ' #-interaction=batchmode '

  for o, a in opts:
    if o in ("-f","--file"):
      fname=a
    elif o in ("-h","--help"):
      usage()
      sys.exit()

  # make sure images are present as symlinks in the image directory
  lnames = ['OCPlogo_horiz.png','OCPlogo_vert.png']
  for l in lnames:
      if os.access('../images/'+l,os.F_OK) is False:
          os.symlink('../../alpha/images/'+l,'../images/'+l)

  # first convert mmd to latex
  print(mmdcmd+fname)
  os.system(mmdcmd+fname)

  # second, convert latex to pdf
  file, ext = os.path.splitext(fname)
  print(pdfcmd+file+'.tex')
  os.system(pdfcmd+file+'.tex')

########NEW FILE########
__FILENAME__ = CADtozip
#(c) Copyright Facebook, Inc. 2011. All rights reserved.

import zipfile
from os import mkdir,rmdir
from os.path import splitext, join
import glob
import shutil

def createZip(fname,addStep=True):
    basename = splitext(fname)[0]
    ext = splitext(fname)[1]
    print basename,ext
    print ext=='.dxf'
    try:
        mkdir(basename)
    except OSError:
        pass
    file = zipfile.ZipFile(basename+'.zip',"w")
    shutil.copy('License.html',basename)
    file.write(join(basename,'License.html'),compress_type=zipfile.ZIP_DEFLATED)
    shutil.copy(fname,basename)
    file.write(join(basename,fname),compress_type=zipfile.ZIP_DEFLATED)
    if addStep is True:
        if (ext != '.dxf'):
            shutil.copy(basename+'.step',basename)
            file.write(join(basename,basename+'.step'),compress_type=zipfile.ZIP_DEFLATED)
    file.close()
    shutil.rmtree(basename)

for name in glob.glob('*.dxf'):
    createZip(name)
for name in glob.glob('*.sldasm'):
    createZip(name)

########NEW FILE########
