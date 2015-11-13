__FILENAME__ = fabfile
# To use this script you must have the following environment variables set:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
# as explained in: http://boto.s3.amazonaws.com/s3_tut.html

import os
import webbrowser

from boto import connect_s3
from boto.s3.key import Key
from fabric.api import abort, task
from fabric.contrib.console import confirm
from render import render
from scrape import scrape

BUCKET_NAME = 'www.ec2instances.info'

abspath = lambda filename: os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                        filename)

@task
def build():
    """Scrape AWS sources for data and build the site"""
    data_file = 'www/instances.json'
    try:
        scrape(data_file)
    except Exception, e:
        print "ERROR: Unable to scrape site data: %s" % e
    render(data_file, 'in/index.html.mako', 'www/index.html')

@task
def preview():
    url = 'file://localhost/%s' % (abspath('www/index.html'))
    webbrowser.open(url, new=2)

@task
def bucket_create():
    """Creates the S3 bucket used to host the site"""
    conn = connect_s3()
    bucket = conn.create_bucket(BUCKET_NAME, policy='public-read')
    bucket.configure_website('index.html', 'error.html')
    print 'Bucket %r created.' % BUCKET_NAME

@task
def bucket_delete():
    """Deletes the S3 bucket used to host the site"""
    if not confirm("Are you sure you want to delete the bucket %r?" % BUCKET_NAME):
        abort('Aborting at user request.')
    conn = connect_s3()
    conn.delete_bucket(BUCKET_NAME)
    print 'Bucket %r deleted.' % BUCKET_NAME

@task
def deploy(root_dir='www'):
    """Deploy current content"""
    conn = connect_s3()
    bucket = conn.get_bucket(BUCKET_NAME)

    for root, dirs, files in os.walk(root_dir):
        for name in files:
            if name.startswith('.'):
                continue
            local_path = os.path.join(root, name)
            remote_path = local_path[len(root_dir)+1:]
            print '%s -> %s/%s' % (local_path, BUCKET_NAME, remote_path)
            k = Key(bucket)
            k.key = remote_path
            headers = {
                "Cache-Control": "max-age=86400, must-revalidate"}
            k.set_contents_from_filename(local_path, headers=headers,
                                         policy='public-read')

@task(default=True)
def update():
    """Build and deploy the site"""
    build()
    deploy()

########NEW FILE########
__FILENAME__ = render
import mako.template
import mako.exceptions
import json
import datetime


def pretty_name(inst):
    pieces = inst['instance_type'].split('.')
    family = pieces[0]
    short  = pieces[1]
    family_names = {
        't1': '',
        'm2': 'High-Memory',
        'c1': 'High-CPU',
        'cc1': 'Cluster Compute',
        'cg1': 'Cluster GPU',
        'cc2': 'Cluster Compute',
        'hi1': 'High I/O',
        'cr1': 'High Memory Cluster',
        'hs1': 'High Storage'
        }
    prefix = family_names.get(family, family.upper())
    extra = None
    if short.startswith('8x'):
        extra = 'Eight'
    elif short.startswith('4x'):
        extra = 'Quadruple'
    elif short.startswith('2x'):
        extra = 'Double'
    elif short.startswith('x'):
        extra = ''
    bits = [prefix]
    if extra is not None:
        bits.extend([extra, 'Extra'])
        short = 'Large'

    bits.append(short.capitalize())

    return ' '.join([b for b in bits if b])

def network_sort(inst):
    perf = inst['network_performance']
    if perf == 'Very Low':
        sort = 0
    elif perf == 'Low':
        sort = 1
    elif perf == 'Moderate':
        sort = 2
    elif perf == 'High':
        sort = 3
    elif perf == '10 Gigabit':
        sort = 4
    sort *= 2
    if inst['ebs_optimized']:
        sort += 1
    return sort

def add_cpu_detail(i):
    if i['instance_type'] in ('cc1.4xlarge', 'cg1.4xlarge'):
        i['cpu_details'] = {
            'cpus': 2,
            'type': 'Xeon X5570',
            'note': 'Quad-core Nehalem architecture'
            }
    elif i['instance_type'] in ('hi1.4xlarge', 'hs1.8xlarge'):
        i['cpu_details'] = {
            'cpus': 2,
            'type': 'Xeon E5-2650',
            'note': 'Eight-core Sandy Bridge architecture'
            }
    elif i['instance_type'] in ('cc2.8xlarge', 'cr1.8xlarge'):
        i['cpu_details'] = {
            'cpus': 2,
            'type': 'Xeon E5-2670',
            'note': 'Eight-core Sandy Bridge architecture'
            }

def add_render_info(i):
    i['network_sort'] = network_sort(i)
    i['pretty_name'] = pretty_name(i)
    add_cpu_detail(i)

def render(data_file, template_file, destination_file):
    """Build the HTML content from scraped data"""
    template = mako.template.Template(filename=template_file)
    print "Loading data from %s..." % data_file
    with open(data_file) as f:
        instances = json.load(f)
    for i in instances:
        add_render_info(i)
    print "Rendering to %s..." % destination_file
    generated_at = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    with open(destination_file, 'w') as fh:
        try:
            fh.write(template.render(instances=instances, generated_at=generated_at))
        except:
            print mako.exceptions.text_error_template().render()

if __name__ == '__main__':
    render('www/instances.json', 'in/index.html.mako', 'www/index.html')

########NEW FILE########
__FILENAME__ = scrape
from lxml import etree
import urllib2
import re
import json


class Instance(object):
    def __init__(self):
        self.vpc = None

    def to_dict(self):
        d = dict(family=self.family,
                 instance_type=self.instance_type,
                 arch=self.arch,
                 vCPU=self.vCPU,
                 ECU=self.ECU,
                 memory=self.memory,
                 ebs_optimized=self.ebs_optimized,
                 network_performance=self.network_performance,
                 pricing=self.pricing,
                 vpc=self.vpc)
        if self.ebs_only:
            d['storage'] = None
        else:
            d['storage'] = dict(ssd=self.ssd,
                                devices=self.num_drives,
                                size=self.drive_size)
        return d


def totext(elt):
    s = etree.tostring(elt, method='text', encoding='unicode').strip()
    return re.sub(r'\*\d$', '', s)


def parse_instance(tr):
    i = Instance()
    cols = tr.xpath('td')
    assert len(cols) == 9, "Expected 9 columns in the table!"
    i.family = totext(cols[0])
    i.instance_type = totext(cols[1])
    archs = totext(cols[2])
    i.arch = []
    if '32-bit' in archs:
        i.arch.append('i386')
    if '64-bit' in archs:
        i.arch.append('x86_64')
    assert i.arch, "No archs detected: %s" % (archs,)
    i.vCPU = int(totext(cols[3]))
    ecu = totext(cols[4])
    if ecu == 'Variable':
        i.ECU = None
    else:
        i.ECU = float(ecu)
    i.memory = float(totext(cols[5]))
    storage = totext(cols[6])
    m = re.search(r'(\d+)\s*x\s*([0-9,]+)?', storage)
    i.ssd = False
    if m:
        i.ebs_only = False
        i.num_drives = int(m.group(1))
        i.drive_size = int(m.group(2).replace(',', ''))
        i.ssd = 'SSD' in totext(cols[6])
    else:
        assert storage == 'EBS only', "Unrecognized storage spec: %s" % (storage,)
        i.ebs_only = True
    i.ebs_optimized = totext(cols[7]).lower() == 'yes'
    i.network_performance = totext(cols[8])
    print "Parsed %s..." % (i.instance_type)
    return i


def scrape_instances():
    tree = etree.parse(urllib2.urlopen("http://aws.amazon.com/ec2/instance-types/"), etree.HTMLParser())
    details = tree.xpath('//table')[0]
    rows = details.xpath('tbody/tr')[1:]
    assert len(rows) > 0, "Didn't find any table rows."
    return [parse_instance(r) for r in rows]


def transform_size(size):
    if size == 'u':
        return 'micro'
    if size == 'sm':
        return 'small'
    if size == 'med':
        return 'medium'
    m = re.search('^(x+)l$', size)
    if m:
        xs = len(m.group(1))
        if xs == 1:
            return 'xlarge'
        else:
            return str(xs) + 'xlarge'
    assert size == 'lg', "Unable to parse size: %s" % (size,)
    return 'large'


def convert_to_type(typ, size):
    return size


def transform_region(reg):
    region_map = {
        'eu-ireland': 'eu-west-1',
        'apac-sin': 'ap-southeast-1',
        'apac-syd': 'ap-southeast-2',
        'apac-tokyo': 'ap-northeast-1'}
    if reg in region_map:
        return region_map[reg]
    m = re.search(r'^([^0-9]*)(-(\d))?$', reg)
    assert m, "Can't parse region: %s" % (reg,)
    base = m.group(1)
    num = m.group(3) or '1'
    return base + "-" + num


def add_pricing(imap, data):
    for region_spec in data['config']['regions']:
        region = transform_region(region_spec['region'])
        for t_spec in region_spec['instanceTypes']:
            typename = t_spec['type']
            for i_spec in t_spec['sizes']:
                i_type = convert_to_type(typename, i_spec['size'])
                # As best I can tell, this type doesn't exist, but is
                # in the pricing charts anyways.
                if i_type == 'cc2.4xlarge':
                    continue
                assert i_type in imap, "Unknown instance size: %s" % (i_type, )
                inst = imap[i_type]
                inst.pricing.setdefault(region, {})
                print "%s/%s" % (region, i_type)
                for col in i_spec['valueColumns']:
                    inst.pricing[region][col['name']] = col['prices']['USD']


def add_pricing_data(instances):
    for i in instances:
        i.pricing = {}
    by_type = {i.instance_type: i for i in instances}

    for platform in ['linux', 'mswin']:
        pricing_url = 'http://aws.amazon.com/ec2/pricing/json/%s-od.json' % (platform,)
        pricing = json.loads(urllib2.urlopen(pricing_url).read())

        add_pricing(by_type, pricing)


def add_eni_info(instances):
    eni_url = "http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html"
    tree = etree.parse(urllib2.urlopen(eni_url), etree.HTMLParser())
    table = tree.xpath('//div[@id="divContent"]/div[@class="section"]//table[.//code[contains(., "cc2.8xlarge")]]')[0]
    rows = table.xpath('.//tr[./td]')
    by_type = {i.instance_type: i for i in instances}

    for r in rows:
        instance_type = etree.tostring(r[0], method='text').strip()
        max_enis = int(etree.tostring(r[1], method='text').strip())
        ip_per_eni = int(etree.tostring(r[2], method='text').strip())
        if instance_type not in by_type:
            print "Unknown instance type: " + instance_type
            continue
        by_type[instance_type].vpc = {
            'max_enis': max_enis,
            'ips_per_eni': ip_per_eni}


def scrape(data_file):
    """Scrape AWS to get instance data"""
    print "Parsing instance types..."
    all_instances = scrape_instances()
    print "Parsing pricing info..."
    add_pricing_data(all_instances)
    add_eni_info(all_instances)
    with open(data_file, 'w') as f:
        json.dump([i.to_dict() for i in all_instances],
                  f,
                  indent=2,
                  separators=(',', ': '))

if __name__ == '__main__':
    scrape('www/instances.json')

########NEW FILE########
