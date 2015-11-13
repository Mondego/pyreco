__FILENAME__ = install
#!/usr/bin/env python
import os
import stat

try:
    import config
except ImportError:
    print('Created personal config.py for your customizations')
    import shutil
    shutil.copyfile('config.py.dist', 'config.py')
    import config

TEMPLATE_FILE = 'powerline-shell.py.template'
OUTPUT_FILE = 'powerline-shell.py'
SEGMENTS_DIR = 'segments'
THEMES_DIR = 'themes'

def load_source(srcfile):
    try:
        return ''.join(open(srcfile).readlines()) + '\n\n'
    except IOError:
        print 'Could not open', srcfile
        return ''

if __name__ == "__main__":
    source = load_source(TEMPLATE_FILE)
    source += load_source(os.path.join(THEMES_DIR, 'default.py'))
    source += load_source(os.path.join(THEMES_DIR, config.THEME + '.py'))
    for segment in config.SEGMENTS:
        source += load_source(os.path.join(SEGMENTS_DIR, segment + '.py'))
    source += 'sys.stdout.write(powerline.draw())\n'

    try:
        open(OUTPUT_FILE, 'w').write(source)
        st = os.stat(OUTPUT_FILE)
        os.chmod(OUTPUT_FILE, st.st_mode | stat.S_IEXEC)
        print OUTPUT_FILE, 'saved successfully'
    except IOError:
        print 'ERROR: Could not write to powerline-shell.py. Make sure it is writable'
        exit(1)

########NEW FILE########
__FILENAME__ = colortrans
#! /usr/bin/env python

"""
Code is modified (fairly heavily) by hryanjones@gmail.com from
https://gist.github.com/MicahElliott/719710

Convert values between RGB tuples and xterm-256 color codes.

Nice long listing of all 256 colors and their codes. Useful for
developing console color themes, or even script output schemes.

Resources:
* http://en.wikipedia.org/wiki/8-bit_color
* http://en.wikipedia.org/wiki/ANSI_escape_code
* /usr/share/X11/rgb.txt

I'm not sure where this script was inspired from. I think I must have
written it from scratch, though it's been several years now.
"""

__author__    = 'Micah Elliott http://MicahElliott.com'
__version__   = '0.1'
__copyright__ = 'Copyright (C) 2011 Micah Elliott.  All rights reserved.'
__license__   = 'WTFPL http://sam.zoy.org/wtfpl/'

#---------------------------------------------------------------------


def hexstr2num(hexstr):
    return int(hexstr, 16)

def rgbstring2tuple(s):
    return tuple([hexstr2num(h) for h in (s[:2], s[2:4], s[4:])])

RGB2SHORT_DICT = {
    (0, 0, 0):     16,
    (0, 0, 95):    17,
    (0, 0, 128):   4,
    (0, 0, 135):   18,
    (0, 0, 175):   19,
    (0, 0, 215):   20,
    (0, 0, 255):   12,
    (0, 95, 0):    22,
    (0, 95, 95):   23,
    (0, 95, 135):  24,
    (0, 95, 175):  25,
    (0, 95, 215):  26,
    (0, 95, 255):  27,
    (0, 128, 0):   2,
    (0, 128, 128): 6,
    (0, 135, 0):   28,
    (0, 135, 95):  29,
    (0, 135, 135): 30,
    (0, 135, 175): 31,
    (0, 135, 215): 32,
    (0, 135, 255): 33,
    (0, 175, 0):   34,
    (0, 175, 95):  35,
    (0, 175, 135): 36,
    (0, 175, 175): 37,
    (0, 175, 215): 38,
    (0, 175, 255): 39,
    (0, 215, 0):   40,
    (0, 215, 95):  41,
    (0, 215, 135): 42,
    (0, 215, 175): 43,
    (0, 215, 215): 44,
    (0, 215, 255): 45,
    (0, 255, 0):   46,
    (0, 255, 95):  47,
    (0, 255, 135): 48,
    (0, 255, 175): 49,
    (0, 255, 215): 50,
    (0, 255, 255): 14,
    (8, 8, 8):    232,
    (18, 18, 18): 233,
    (28, 28, 28): 234,
    (38, 38, 38): 235,
    (48, 48, 48): 236,
    (58, 58, 58): 237,
    (68, 68, 68): 238,
    (78, 78, 78): 239,
    (88, 88, 88): 240,
    (95, 0, 0):   52,
    (95, 0, 95):  53,
    (95, 0, 135): 54,
    (95, 0, 175): 55,
    (95, 0, 215): 56,
    (95, 0, 255): 57,
    (95, 95, 0):  58,
    (95, 95, 95):  59,
    (95, 95, 135): 60,
    (95, 95, 175): 61,
    (95, 95, 215): 62,
    (95, 95, 255): 63,
    (95, 135, 0):  64,
    (95, 135, 95): 65,
    (95, 135, 135): 66,
    (95, 135, 175): 67,
    (95, 135, 215): 68,
    (95, 135, 255): 69,
    (95, 175, 0):   70,
    (95, 175, 95) : 71,
    (95, 175, 135): 72,
    (95, 175, 175): 73,
    (95, 175, 215): 74,
    (95, 175, 255): 75,
    (95, 215, 0):   76,
    (95, 215, 95) : 77,
    (95, 215, 135): 78,
    (95, 215, 175): 79,
    (95, 215, 215): 80,
    (95, 215, 255): 81,
    (95, 255, 0):   82,
    (95, 255, 95) : 83,
    (95, 255, 135): 84,
    (95, 255, 175): 85,
    (95, 255, 215): 86,
    (95, 255, 255): 87,
    (98, 98, 98):    241,
    (108, 108, 108): 242,
    (118, 118, 118): 243,
    (128, 0, 0):      1,
    (128, 0, 128):    5,
    (128, 128, 0):    3,
    (128, 128, 128): 244,
    (135, 0, 0):      88,
    (135, 0, 95):     89,
    (135, 0, 135):    90,
    (135, 0, 175):    91,
    (135, 0, 215):    92,
    (135, 0, 255):    93,
    (135, 95, 0):     94,
    (135, 95, 95):    95,
    (135, 95, 135):   96,
    (135, 95, 175):   97,
    (135, 95, 215):   98,
    (135, 95, 255):   99,
    (135, 135, 0):   100,
    (135, 135, 95):  101,
    (135, 135, 135): 102,
    (135, 135, 175): 103,
    (135, 135, 215): 104,
    (135, 135, 255): 105,
    (135, 175, 0):   106,
    (135, 175, 95):  107,
    (135, 175, 135): 108,
    (135, 175, 175): 109,
    (135, 175, 215): 110,
    (135, 175, 255): 111,
    (135, 215, 0):   112,
    (135, 215, 95):  113,
    (135, 215, 135): 114,
    (135, 215, 175): 115,
    (135, 215, 215): 116,
    (135, 215, 255): 117,
    (135, 255, 0):   118,
    (135, 255, 95):  119,
    (135, 255, 135): 120,
    (135, 255, 175): 121,
    (135, 255, 215): 122,
    (135, 255, 255): 123,
    (138, 138, 138): 245,
    (148, 148, 148): 246,
    (158, 158, 158): 247,
    (168, 168, 168): 248,
    (175, 0, 0): 124,
    (175, 0, 95): 125,
    (175, 0, 135): 126,
    (175, 0, 175): 127,
    (175, 0, 215): 128,
    (175, 0, 255): 129,
    (175, 95, 0): 130,
    (175, 95, 95): 131,
    (175, 95, 135): 132,
    (175, 95, 175): 133,
    (175, 95, 215): 134,
    (175, 95, 255): 135,
    (175, 135, 0): 136,
    (175, 135, 95): 137,
    (175, 135, 135): 138,
    (175, 135, 175): 139,
    (175, 135, 215): 140,
    (175, 135, 255): 141,
    (175, 175, 0): 142,
    (175, 175, 95): 143,
    (175, 175, 135): 144,
    (175, 175, 175): 145,
    (175, 175, 215): 146,
    (175, 175, 255): 147,
    (175, 215, 0): 148,
    (175, 215, 95): 149,
    (175, 215, 135): 150,
    (175, 215, 175): 151,
    (175, 215, 215): 152,
    (175, 215, 255): 153,
    (175, 255, 0): 154,
    (175, 255, 95): 155,
    (175, 255, 135): 156,
    (175, 255, 175): 157,
    (175, 255, 215): 158,
    (175, 255, 255): 159,
    (178, 178, 178): 249,
    (188, 188, 188): 250,
    (192, 192, 192): 7,
    (198, 198, 198): 251,
    (208, 208, 208): 252,
    (215, 0, 0): 160,
    (215, 0, 95): 161,
    (215, 0, 135): 162,
    (215, 0, 175): 163,
    (215, 0, 215): 164,
    (215, 0, 255): 165,
    (215, 95, 0): 166,
    (215, 95, 95): 167,
    (215, 95, 135): 168,
    (215, 95, 175): 169,
    (215, 95, 215): 170,
    (215, 95, 255): 171,
    (215, 135, 0): 172,
    (215, 135, 95): 173,
    (215, 135, 135): 174,
    (215, 135, 175): 175,
    (215, 135, 215): 176,
    (215, 135, 255): 177,
    (215, 175, 0): 178,
    (215, 175, 95): 179,
    (215, 175, 135): 180,
    (215, 175, 175): 181,
    (215, 175, 215): 182,
    (215, 175, 255): 183,
    (215, 215, 0): 184,
    (215, 215, 95): 185,
    (215, 215, 135): 186,
    (215, 215, 175): 187,
    (215, 215, 215): 188,
    (215, 215, 255): 189,
    (215, 255, 0): 190,
    (215, 255, 95): 191,
    (215, 255, 135): 192,
    (215, 255, 175): 193,
    (215, 255, 215): 194,
    (215, 255, 255): 195,
    (218, 218, 218): 253,
    (228, 228, 228): 254,
    (238, 238, 238): 255,
    (255, 0, 0): 196,
    (255, 0, 95): 197,
    (255, 0, 135): 198,
    (255, 0, 175): 199,
    (255, 0, 215): 200,
    (255, 0, 255): 13,
    (255, 95, 0): 202,
    (255, 95, 95): 203,
    (255, 95, 135): 204,
    (255, 95, 175): 205,
    (255, 95, 215): 206,
    (255, 95, 255): 207,
    (255, 135, 0): 208,
    (255, 135, 95): 209,
    (255, 135, 135): 210,
    (255, 135, 175): 211,
    (255, 135, 215): 212,
    (255, 135, 255): 213,
    (255, 175, 0): 214,
    (255, 175, 95): 215,
    (255, 175, 135): 216,
    (255, 175, 175): 217,
    (255, 175, 215): 218,
    (255, 175, 255): 219,
    (255, 215, 0): 220,
    (255, 215, 95): 221,
    (255, 215, 135): 222,
    (255, 215, 175): 223,
    (255, 215, 215): 224,
    (255, 215, 255): 225,
    (255, 255, 0): 11,
    (255, 255, 95): 227,
    (255, 255, 135): 228,
    (255, 255, 175): 229,
    (255, 255, 215): 230,
    (255, 255, 255): 231}


def hexstr2num(hexstr):
    return int(hexstr, 16)

def rgb2short(r, g, b):
    """ Find the closest xterm-256 approximation to the given RGB value.
    @param r,g,b: each is a number between 0-255 for the Red, Green, and Blue values
    @returns: integer between 0 and 255, compatible with xterm.
    >>> rgb2short(18, 52, 86)
    23
    >>> rgb2short(255, 255, 255)
    231
    >>> rgb2short(13, 173, 214) # vimeo logo
    38
    """
    incs = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)
    # Break 6-char RGB code into 3 integer vals.
    parts = [ r, g, b] 
    res = []
    for part in parts:
        i = 0
        while i < len(incs)-1:
            s, b = incs[i], incs[i+1]  # smaller, bigger
            if s <= part <= b:
                s1 = abs(s - part)
                b1 = abs(b - part)
                if s1 < b1: closest = s
                else: closest = b
                res.append(closest)
                break
            i += 1
    #print '***', res
    return RGB2SHORT_DICT[tuple(res)]

#---------------------------------------------------------------------

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = color_compliment
#! /usr/bin/env python

from colortrans import *
from colorsys import hls_to_rgb, rgb_to_hls
from md5 import md5
from sys import argv


def getOppositeColor(r,g,b):
    hls = rgb_to_hls(r,g,b)
    #print "hls is"
    #print hls
    opp = list(hls[:])
    #opp[0] = (opp[0]+0.5)%1 # reverse hue (a.k.a. color), reversing tends to be jarring
    opp[0] = (opp[0]+0.2)%1 # shift hue (a.k.a. color)
    if opp[1] > 255/2:   # for level you want to make sure they
        opp[1] -= 255/2  # are quite different so easily readable
    else:
        opp[1] += 255/2
    if opp[2] > -0.5: # if saturation is low on first color increase second's
        opp[2] -= 0.5
    #print opp
    opp = hls_to_rgb(*opp)
    m = max(opp)
    if m > 255: #colorsys module doesn't give caps to their conversions
        opp = [ x*254/m for x in opp]
    return tuple([ int(x) for x in opp])

def stringToHashToColorAndOpposite(string):
    string = md5(string).hexdigest()[:6] # get a random color
    color1 = rgbstring2tuple(string)
    color2 = getOppositeColor(*color1)
    return color1, color2

########NEW FILE########
__FILENAME__ = cwd
import os

def get_short_path(cwd):
    home = os.getenv('HOME')
    names = cwd.split(os.sep)
    if names[0] == '': names = names[1:]
    path = ''
    for i in range(len(names)):
        path += os.sep + names[i]
        if os.path.samefile(path, home):
            return ['~'] + names[i+1:]
    if not names[0]:
        return ['/']
    return names

def add_cwd_segment():
    cwd = powerline.cwd or os.getenv('PWD')
    names = get_short_path(cwd.decode('utf-8'))

    max_depth = powerline.args.cwd_max_depth
    if len(names) > max_depth:
        names = names[:2] + [u'\u2026'] + names[2 - max_depth:]

    if not powerline.args.cwd_only:
        for n in names[:-1]:
            if n == '~' and Color.HOME_SPECIAL_DISPLAY:
                powerline.append(' %s ' % n, Color.HOME_FG, Color.HOME_BG)
            else:
                powerline.append(' %s ' % n, Color.PATH_FG, Color.PATH_BG,
                    powerline.separator_thin, Color.SEPARATOR_FG)

    if names[-1] == '~' and Color.HOME_SPECIAL_DISPLAY:
        powerline.append(' %s ' % names[-1], Color.HOME_FG, Color.HOME_BG)
    else:
        powerline.append(' %s ' % names[-1], Color.CWD_FG, Color.PATH_BG)

add_cwd_segment()

########NEW FILE########
__FILENAME__ = fossil
import os
import subprocess

def get_fossil_status():
    has_modified_files = False
    has_untracked_files = False
    has_missing_files = False
    output = os.popen('fossil changes 2>/dev/null').read().strip()
    has_untracked_files = True if os.popen("fossil extras 2>/dev/null").read().strip() else False
    has_missing_files = 'MISSING' in output
    has_modified_files = 'EDITED' in output

    return has_modified_files, has_untracked_files, has_missing_files

def add_fossil_segment():
    subprocess.Popen(['fossil'], stdout=subprocess.PIPE).communicate()[0]
    branch = ''.join([i.replace('*','').strip() for i in os.popen("fossil branch 2> /dev/null").read().strip().split("\n") if i.startswith('*')])
    if len(branch) == 0:
        return

    bg = Color.REPO_CLEAN_BG
    fg = Color.REPO_CLEAN_FG
    has_modified_files, has_untracked_files, has_missing_files = get_fossil_status()
    if has_modified_files or has_untracked_files or has_missing_files:
        bg = Color.REPO_DIRTY_BG
        fg = Color.REPO_DIRTY_FG
        extra = ''
        if has_untracked_files:
            extra += '+'
        if has_missing_files:
            extra += '!'
        branch += (' ' + extra if extra != '' else '')
    powerline.append(' %s ' % branch, fg, bg)

try:
    add_fossil_segment()
except OSError:
    pass
except subprocess.CalledProcessError:
    pass

########NEW FILE########
__FILENAME__ = git
import re
import subprocess

def get_git_status():
    has_pending_commits = True
    has_untracked_files = False
    origin_position = ""
    output = subprocess.Popen(['git', 'status', '--ignore-submodules'],
            env={"LANG": "C", "HOME": os.getenv("HOME")}, stdout=subprocess.PIPE).communicate()[0]
    for line in output.split('\n'):
        origin_status = re.findall(
            r"Your branch is (ahead|behind).*?(\d+) comm", line)
        if origin_status:
            origin_position = " %d" % int(origin_status[0][1])
            if origin_status[0][0] == 'behind':
                origin_position += u'\u21E3'
            if origin_status[0][0] == 'ahead':
                origin_position += u'\u21E1'

        if line.find('nothing to commit') >= 0:
            has_pending_commits = False
        if line.find('Untracked files') >= 0:
            has_untracked_files = True
    return has_pending_commits, has_untracked_files, origin_position


def add_git_segment():
    # See http://git-blame.blogspot.com/2013/06/checking-current-branch-programatically.html
    p = subprocess.Popen(['git', 'symbolic-ref', '-q', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if 'Not a git repo' in err:
        return

    if out:
        branch = out[len('refs/heads/'):].rstrip()
    else:
        branch = '(Detached)'

    has_pending_commits, has_untracked_files, origin_position = get_git_status()
    branch += origin_position
    if has_untracked_files:
        branch += ' +'

    bg = Color.REPO_CLEAN_BG
    fg = Color.REPO_CLEAN_FG
    if has_pending_commits:
        bg = Color.REPO_DIRTY_BG
        fg = Color.REPO_DIRTY_FG

    powerline.append(' %s ' % branch, fg, bg)

try:
    add_git_segment()
except OSError:
    pass
except subprocess.CalledProcessError:
    pass

########NEW FILE########
__FILENAME__ = hg
import os
import subprocess

def get_hg_status():
    has_modified_files = False
    has_untracked_files = False
    has_missing_files = False
    output = subprocess.Popen(['hg', 'status'],
            stdout=subprocess.PIPE).communicate()[0]
    for line in output.split('\n'):
        if line == '':
            continue
        elif line[0] == '?':
            has_untracked_files = True
        elif line[0] == '!':
            has_missing_files = True
        else:
            has_modified_files = True
    return has_modified_files, has_untracked_files, has_missing_files

def add_hg_segment():
    branch = os.popen('hg branch 2> /dev/null').read().rstrip()
    if len(branch) == 0:
        return False
    bg = Color.REPO_CLEAN_BG
    fg = Color.REPO_CLEAN_FG
    has_modified_files, has_untracked_files, has_missing_files = get_hg_status()
    if has_modified_files or has_untracked_files or has_missing_files:
        bg = Color.REPO_DIRTY_BG
        fg = Color.REPO_DIRTY_FG
        extra = ''
        if has_untracked_files:
            extra += '+'
        if has_missing_files:
            extra += '!'
        branch += (' ' + extra if extra != '' else '')
    return powerline.append(' %s ' % branch, fg, bg)

add_hg_segment()

########NEW FILE########
__FILENAME__ = hostname
def add_hostname_segment():
    if powerline.args.colorize_hostname:
        from lib.color_compliment import stringToHashToColorAndOpposite
        from lib.colortrans import rgb2short
        from socket import gethostname
        hostname = gethostname()
        FG, BG = stringToHashToColorAndOpposite(hostname)
        FG, BG = (rgb2short(*color) for color in [FG, BG])
        host_prompt = ' %s ' % hostname.split('.')[0]

        powerline.append(host_prompt, FG, BG)
    else:
        if powerline.args.shell == 'bash':
            host_prompt = ' \\h '
        elif powerline.args.shell == 'zsh':
            host_prompt = ' %m '
        else:
            import socket
            host_prompt = ' %s ' % socket.gethostname().split('.')[0]

        powerline.append(host_prompt, Color.HOSTNAME_FG, Color.HOSTNAME_BG)


add_hostname_segment()

########NEW FILE########
__FILENAME__ = jobs
import os
import re
import subprocess

def add_jobs_segment():
    pppid = subprocess.Popen(['ps', '-p', str(os.getppid()), '-oppid='], stdout=subprocess.PIPE).communicate()[0].strip()
    output = subprocess.Popen(['ps', '-a', '-o', 'ppid'], stdout=subprocess.PIPE).communicate()[0]
    num_jobs = len(re.findall(str(pppid), output)) - 1

    if num_jobs > 0:
        powerline.append(' %d ' % num_jobs, Color.JOBS_FG, Color.JOBS_BG)

add_jobs_segment()

########NEW FILE########
__FILENAME__ = php_version
import subprocess


def add_php_version_segment():
    try:
        output = subprocess.check_output(['php', '-r', 'echo PHP_VERSION;'], stderr=subprocess.STDOUT)
        if '-' in output:
            version = ' %s ' % output.split('-')[0]
        else:
            version = ' %s ' % output

        powerline.append(version, 15, 4)
    except OSError:
        return

add_php_version_segment()

########NEW FILE########
__FILENAME__ = read_only
import os

def add_read_only_segment():
    cwd = powerline.cwd or os.getenv('PWD')

    if not os.access(cwd, os.W_OK):
        powerline.append(' %s ' % powerline.lock, Color.READONLY_FG, Color.READONLY_BG)

add_read_only_segment()

########NEW FILE########
__FILENAME__ = root
def add_root_indicator_segment():
    root_indicators = {
        'bash': ' \\$ ',
        'zsh': ' \\$ ',
        'bare': ' $ ',
    }
    bg = Color.CMD_PASSED_BG
    fg = Color.CMD_PASSED_FG
    if powerline.args.prev_error != 0:
        fg = Color.CMD_FAILED_FG
        bg = Color.CMD_FAILED_BG
    powerline.append(root_indicators[powerline.args.shell], fg, bg)

add_root_indicator_segment()

########NEW FILE########
__FILENAME__ = ruby_version
import subprocess


def add_ruby_version_segment():
    try:
        p1 = subprocess.Popen(["ruby", "-v"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["sed", "s/ (.*//"], stdin=p1.stdout, stdout=subprocess.PIPE)
        version = p2.communicate()[0].rstrip()
        if os.environ.has_key("GEM_HOME"):
          gem = os.environ["GEM_HOME"].split("@")
          if len(gem) > 1:
            version += " " + gem[1]
        powerline.append(version, 15, 1)
    except OSError:
        return

add_ruby_version_segment()

########NEW FILE########
__FILENAME__ = ssh
import os

def add_ssh_segment():

    if os.getenv('SSH_CLIENT'):
        powerline.append(' %s ' % powerline.network, Color.SSH_FG, Color.SSH_BG)

add_ssh_segment()

########NEW FILE########
__FILENAME__ = svn
import subprocess

def add_svn_segment():
    is_svn = subprocess.Popen(['svn', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    is_svn_output = is_svn.communicate()[1].strip()
    if len(is_svn_output) != 0:
        return

    #"svn status | grep -c "^[ACDIMRX\\!\\~]"
    p1 = subprocess.Popen(['svn', 'status'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    p2 = subprocess.Popen(['grep', '-c', '^[ACDIMR\\!\\~]'],
            stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0].strip()
    if len(output) > 0 and int(output) > 0:
        changes = output.strip()
        powerline.append(' %s ' % changes, Color.SVN_CHANGES_FG, Color.SVN_CHANGES_BG)

try:
    add_svn_segment()
except OSError:
    pass
except subprocess.CalledProcessError:
    pass

########NEW FILE########
__FILENAME__ = username

def add_username_segment():
    import os
    if powerline.args.shell == 'bash':
        user_prompt = ' \\u '
    elif powerline.args.shell == 'zsh':
        user_prompt = ' %n '
    else:
        user_prompt = ' %s ' % os.getenv('USER')

    if os.getenv('USER') == 'root':
        bgcolor = Color.USERNAME_ROOT_BG
    else:
        bgcolor = Color.USERNAME_BG

    powerline.append(user_prompt, Color.USERNAME_FG, bgcolor)

add_username_segment()

########NEW FILE########
__FILENAME__ = virtual_env
import os

def add_virtual_env_segment():
    env = os.getenv('VIRTUAL_ENV')
    if env is None:
        return

    env_name = os.path.basename(env)
    bg = Color.VIRTUAL_ENV_BG
    fg = Color.VIRTUAL_ENV_FG
    powerline.append(' %s ' % env_name, fg, bg)

add_virtual_env_segment()

########NEW FILE########
__FILENAME__ = basic
# Basic theme which only uses colors in 0-15 range

class Color(DefaultColor):
    USERNAME_FG = 8
    USERNAME_BG = 15
    USERNAME_ROOT_BG = 1

    HOSTNAME_FG = 8
    HOSTNAME_BG = 7

    HOME_SPECIAL_DISPLAY = False
    PATH_BG = 8 # dark grey
    PATH_FG = 7 # light grey
    CWD_FG = 15 # white
    SEPARATOR_FG = 7

    READONLY_BG = 1
    READONLY_FG = 15

    REPO_CLEAN_BG = 2  # green
    REPO_CLEAN_FG = 0  # black
    REPO_DIRTY_BG = 1  # red
    REPO_DIRTY_FG = 15 # white

    JOBS_FG = 14
    JOBS_BG = 8

    CMD_PASSED_BG = 8
    CMD_PASSED_FG = 15
    CMD_FAILED_BG = 11
    CMD_FAILED_FG = 0

    SVN_CHANGES_BG = REPO_DIRTY_BG
    SVN_CHANGES_FG = REPO_DIRTY_FG

    VIRTUAL_ENV_BG = 2
    VIRTUAL_ENV_FG = 0

########NEW FILE########
__FILENAME__ = colortest
#!/usr/bin/env python
import sys

ESCAPE = chr(27)

def fg(color):
    return ESCAPE + '[38;5;{0}m'.format(color)

def bg(color):
    return ESCAPE + '[48;5;{0}m'.format(color)

def reset():
    return ESCAPE + '[48;0m'

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print 'Usage: colortest.py fg_start fg_end bg_start bg_end test_string'
        sys.exit(1)

    fg_start, fg_end, bg_start, bg_end = map(int, sys.argv[1:5])
    test_string = sys.argv[5]

    print ' ' * len(str(bg_start)),
    for fg_color in range(fg_start, fg_end + 1):
        print ' ' * (len(test_string) - len(str(fg_color))), fg_color,
    print

    for bg_color in range(bg_start, bg_end + 1):
        print bg_color, bg(bg_color),
        for fg_color in range(fg_start, fg_end + 1):
            print fg(fg_color), test_string,
        print reset()

########NEW FILE########
__FILENAME__ = default
class DefaultColor:
    """
    This class should have the default colors for every segment.
    Please test every new segment with this theme first.
    """
    USERNAME_FG = 250
    USERNAME_BG = 240
    USERNAME_ROOT_BG = 124

    HOSTNAME_FG = 250
    HOSTNAME_BG = 238

    HOME_SPECIAL_DISPLAY = True
    HOME_BG = 31  # blueish
    HOME_FG = 15  # white
    PATH_BG = 237  # dark grey
    PATH_FG = 250  # light grey
    CWD_FG = 254  # nearly-white grey
    SEPARATOR_FG = 244

    READONLY_BG = 124
    READONLY_FG = 254

    SSH_BG = 166 # medium orange
    SSH_FG = 254

    REPO_CLEAN_BG = 148  # a light green color
    REPO_CLEAN_FG = 0  # black
    REPO_DIRTY_BG = 161  # pink/red
    REPO_DIRTY_FG = 15  # white

    JOBS_FG = 39
    JOBS_BG = 238

    CMD_PASSED_BG = 236
    CMD_PASSED_FG = 15
    CMD_FAILED_BG = 161
    CMD_FAILED_FG = 15

    SVN_CHANGES_BG = 148
    SVN_CHANGES_FG = 22  # dark green

    VIRTUAL_ENV_BG = 35  # a mid-tone green
    VIRTUAL_ENV_FG = 00

class Color(DefaultColor):
    """
    This subclass is required when the user chooses to use 'default' theme.
    Because the segments require a 'Color' class for every theme.
    """
    pass

########NEW FILE########
__FILENAME__ = solarized-dark
class Color(DefaultColor):
    USERNAME_FG = 15
    USERNAME_BG = 4
    USERNAME_ROOT_BG = 1

    HOSTNAME_FG = 15
    HOSTNAME_BG = 10

    HOME_SPECIAL_DISPLAY = False
    PATH_FG = 7
    PATH_BG = 10
    CWD_FG = 15
    SEPARATOR_FG = 14

    READONLY_BG = 1
    READONLY_FG = 7

    REPO_CLEAN_FG = 14
    REPO_CLEAN_BG = 0
    REPO_DIRTY_FG = 3
    REPO_DIRTY_BG = 0

    JOBS_FG = 4
    JOBS_BG = 8

    CMD_PASSED_FG = 15
    CMD_PASSED_BG = 2
    CMD_FAILED_FG = 15
    CMD_FAILED_BG = 1

    SVN_CHANGES_FG = REPO_DIRTY_FG
    SVN_CHANGES_BG = REPO_DIRTY_BG

    VIRTUAL_ENV_BG = 15
    VIRTUAL_ENV_FG = 2

########NEW FILE########
__FILENAME__ = washed
class Color(DefaultColor):
    USERNAME_FG = 8
    USERNAME_BG = 251
    USERNAME_ROOT_BG = 209

    HOSTNAME_FG = 8
    HOSTNAME_BG = 7

    HOME_SPECIAL_DISPLAY = False
    PATH_BG = 15
    PATH_FG = 8
    CWD_FG = 8
    SEPARATOR_FG = 251

    READONLY_BG = 209
    READONLY_FG = 15

    REPO_CLEAN_BG = 150  # pale green
    REPO_CLEAN_FG = 235
    REPO_DIRTY_BG = 203  # pale red
    REPO_DIRTY_FG = 15

    JOBS_FG = 14
    JOBS_BG = 8

    CMD_PASSED_BG = 7
    CMD_PASSED_FG = 8
    CMD_FAILED_BG = 9
    CMD_FAILED_FG = 15

    SVN_CHANGES_BG = REPO_DIRTY_BG
    SVN_CHANGES_FG = REPO_DIRTY_FG

    VIRTUAL_ENV_BG = 150
    VIRTUAL_ENV_FG = 0

########NEW FILE########
