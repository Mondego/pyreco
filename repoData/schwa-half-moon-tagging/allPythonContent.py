__FILENAME__ = tag
"""tag - Command line tool for tagging files

Usage:
  tag --list <path>
  tag <path>
  tag --add=<tags> <paths>...
  tag --set=<tags> <paths>...
  tag --remove=<tags> <paths>...
  tag --find=<tag>
  tag (-h | --help)
  tag --version

Options:
  -l --list           List all tags in path
  -a --add=<tags>     Add one or more (comma separated) tags to paths
  -s --set=<tags>     Set one or more (comma separated) tags on paths
  -r --remove=<tags>  Remove one or more (comma separated) tags from paths
  --find=<tag>        Find all items containing <tag>
  -h --help           Show this screen.
  --version           Show version.
"""

__author__ = 'schwa'

from docopt import docopt
import fnmatch
import Foundation
import subprocess

NSURLTagNamesKey = 'NSURLTagNamesKey'

def get_tags(path):
    url = Foundation.NSURL.fileURLWithPath_(path)
    metadata, error = url.resourceValuesForKeys_error_([ NSURLTagNamesKey ], None)
    if not metadata:
        return set()
    elif NSURLTagNamesKey not in metadata:
        return set()
    else:
        return set(metadata[NSURLTagNamesKey])

def set_tags(path, tags):
    tags = list(tags)
    url = Foundation.NSURL.fileURLWithPath_(path)
    result, error = url.setResourceValue_forKey_error_(tags, NSURLTagNamesKey, None)
    if not result:
        raise Exception('Could not set tags', unicode(error).encode('ascii', 'ignore'))

def add_tag(path, tag):
    tags = get_tags(path)
    if tag in tags:
        return
    tags.append(tag)
    set_tags(path, tags)

def add_tags(path, new_tags):
    if not new_tags:
        return
    tags = get_tags(path)
    tags.update(new_tags)
    set_tags(path, tags)

def remove_tag(path, tag):
    tags = get_tags(path)
    if tag in tags:
        tags.remove(tag)
        set_tags(path, tags)

def remove_tags(path, tags):
    old_tags = get_tags(path)
    new_tags = [tag for tag in old_tags if tag not in tags]
    set_tags(path, new_tags)

def remove_tags_glob(path, patterns):
    tags = get_tags(path)
    found_tags = set()
    for pattern in patterns:
        for tag in tags:
            if fnmatch.fnmatch(tag, pattern):
                found_tags.add(tag)
    remove_tags(path, found_tags)

def split_tags(s):
    tags = s.split(',')
    tags = [tag.strip() for tag in tags]
    return tags

def main(argv = None):
    #argv = shlex.split(raw_input('$ tag '))
    arguments = docopt(__doc__, argv = argv, version='tag 1.0.1')
    if arguments['--add']:
        tags = split_tags(arguments['--add'])
        for path in arguments['<paths>']:
            add_tags(path, tags)
    elif arguments['--set']:
        tags = split_tags(arguments['--set'])
        for path in arguments['<paths>']:
            set_tags(path, tags)
    elif arguments['--remove']:
        tags = split_tags(arguments['--remove'])
        for path in arguments['<paths>']:
            remove_tags_glob(path, tags)
    elif arguments['--list']:
        for tag in get_tags(arguments['<path>']):
            print tag
    elif arguments['--find']:
        s = subprocess.check_output(['mdfind', 'kMDItemUserTags == "%s"' % arguments['--find']])
        print s
    else:
        for tag in get_tags(arguments['<path>']):
            print tag

if __name__ == '__main__':
    main()

########NEW FILE########
