__FILENAME__ = loginform
#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from collections import defaultdict
from lxml import html


__version__ = '1.0'  # also update setup.py


def _form_score(form):
    score = 0
    # In case of user/pass or user/pass/remember-me
    if len(form.inputs.keys()) in (2, 3):
        score += 10

    typecount = defaultdict(int)
    for x in form.inputs:
        type_ = x.type if isinstance(x, html.InputElement) else "other"
        typecount[type_] += 1

    if typecount['text'] > 1:
        score += 10
    if not typecount['text']:
        score -= 10

    if typecount['password'] == 1:
        score += 10
    if not typecount['password']:
        score -= 10

    if typecount['checkbox'] > 1:
        score -= 10
    if typecount['radio']:
        score -= 10

    return score


def _pick_form(forms):
    """Return the form most likely to be a login form"""
    return sorted(forms, key=_form_score, reverse=True)[0]


def _pick_fields(form):
    """Return the most likely field names for username and password"""
    userfield = passfield = emailfield = None
    for x in form.inputs:
        if not isinstance(x, html.InputElement):
            continue

        type_ = x.type
        if type_ == 'password' and passfield is None:
            passfield = x.name
        elif type_ == 'text' and userfield is None:
            userfield = x.name
        elif type_ == 'email' and emailfield is None:
            emailfield = x.name

    return userfield or emailfield, passfield


def submit_value(form):
    """Returns the value for the submit input, if any"""
    for x in form.inputs:
        if x.type == "submit" and x.name:
            return [(x.name, x.value)]
    else:
        return []


def fill_login_form(url, body, username, password):
    doc = html.document_fromstring(body, base_url=url)
    form = _pick_form(doc.xpath('//form'))
    userfield, passfield = _pick_fields(form)
    form.fields[userfield] = username
    form.fields[passfield] = password
    form_values = form.form_values() + submit_value(form)
    return form_values, form.action or form.base_url, form.method


def main():
    ap = ArgumentParser()
    ap.add_argument('-u', '--username', default='username')
    ap.add_argument('-p', '--password', default='secret')
    ap.add_argument('url')
    args = ap.parse_args()

    try:
        import requests
    except ImportError:
        print('requests library is required to use loginform as a tool')

    r = requests.get(args.url)
    values, action, method = fill_login_form(args.url, r.text, args.username, args.password)
    print('url: {0}\nmethod: {1}\npayload:'.format(action, method))
    for k, v in values:
        print('- {0}: {1}'.format(k, v))


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
import json
import glob
import requests
import optparse
from loginform import fill_login_form


def parse_opts():
    op = optparse.OptionParser(usage="%prog [-w NAME] url | -l")
    op.add_option("-w", dest="write", metavar="NAME", help="write new sample")
    op.add_option("-l", dest="list", action="store_true", help="list all samples")
    opts, args = op.parse_args()
    if not opts.list and len(args) != 1:
        op.error("incorrect number of args")
    return opts, args


def list_samples():
    return [fn.split('/')[1][:-5] for fn in glob.glob('samples/*.json')]


def sample_html(name):
    return 'samples/%s.html' % name


def sample_json(name):
    return 'samples/%s.json' % name


def check_sample(name):
    from nose.tools import assert_equal
    with open(sample_json(name), 'rb') as f:
        url, expected_values = json.loads(f.read().decode('utf8'))
    with open(sample_html(name), 'rb') as f:
        body = f.read().decode('utf-8')
    values = fill_login_form(url, body, "USER", "PASS")
    values = json.loads(json.dumps(values))  # normalize tuple -> list
    assert_equal(values, expected_values)


def test_samples():
    for name in list_samples():
        yield check_sample, name


def main():
    opts, args = parse_opts()
    if opts.list:
        print("\n".join(list_samples()))
    else:
        url = args[0]
        r = requests.get(url)
        values = fill_login_form(url, r.text, "USER", "PASS")
        values = (url, values)
        print(json.dumps(values, indent=3))
        if opts.write:
            with open(sample_html(opts.write), 'wb') as f:
                f.write(r.text.encode('utf-8'))
            with open(sample_json(opts.write), 'wb') as f:
                json.dump(values, f, indent=3)


if __name__ == "__main__":
    main()

########NEW FILE########
