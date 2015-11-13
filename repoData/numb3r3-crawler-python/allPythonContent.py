__FILENAME__ = amazon_crawler
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.contrib.amazon import *

from optparse import OptionParser
import os
import time
import pprint
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


usage = "usage %prog [options] arg"
parser = OptionParser(usage=usage)
parser.add_option('-s', "--seed", dest="initial search url",
                  help="the initial search url")
parser.add_option("-o", "--output", dest="output_dir",
              help="write out to DIR")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

(options, args) = parser.parse_args()

def main():

    proxies = {'http': 'http://23.244.180.162:8089', 'https': 'http://23.244.180.162:8089'}

    socket_proxies = {'http': 'socket5://1.ss.shadowsocks.net:65535', 'https': 'http://23.244.180.162:8089'}

    # laptop seed url
    #seed_url = "http://www.amazon.com/s/ref=sr_nr_p_n_feature_eighteen_0?rh=n%3A172282%2Cn%3A%21493964%2Cn%3A541966%2Cn%3A565108%2Cp_n_feature_eighteen_browse-bin%3A6819965011&bbn=565108&ie=UTF8&qid=1381818929&rnid=6819964011"
    
    #for prd_id in amazon_prd_ids(seed_url, proxies):
    #    print prd_id

    #print amazon_camera("B00EFILPHA", proxies)

    print amazon_reviews("B00EFILPHA")
    # amazon_prd_img("B00EFILPHA", "images")

    #for dirname, dirnames, filenames in os.walk('D:\workspace\camera\small'):
    #    for filename in filenames:
    #        file_path = os.path.join(dirname, filename)
            
    #        pid = filename[:-5]
    #        if not os.path.isfile(os.path.join("D:\workspace\camera\images", pid) + ".jpg"):
    #            amazon_prd_img(pid, "D:\workspace\camera\images")

     #       print pid
   
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = amazon
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.core.base import *

import time
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def amazon_prd_ids(search_url, proxies=None):
    logger.info('fetching product ids from %s' % search_url)
    soup = get_soup(search_url, proxies)

    prds_div = soup.findAll("div", {"class": "productTitle"})

    if not prds_div:
        prds_div = soup.findAll("div", {"class": "image imageContainer"})

    prds_ids = map(lambda x: x.find('a')['href'].split('/')[5], prds_div)


    for prd_id in prds_ids:
        yield prd_id

    time.sleep(5)

    pagnNextLink = soup.find("a", {"id": "pagnNextLink"})
    while pagnNextLink:
        next_link = pagnNextLink['href']
        logger.info('fetching product ids from %s' % next_link)
        
        soup = get_soup(next_link, proxies)
        prds_div = soup.findAll("div", {"class": "productTitle"})

        if not prds_div:
            prds_div = soup.findAll("div", {"class": "image imageContainer"})

        prds_ids = map(lambda x: x.find('a')['href'].split('/')[5], prds_div)
        
        for prd_id in prds_ids:
            yield prd_id

def amazon_camera(prd_id, proxies=None):
    brands = ['canon', 'sony', 'nikon', 'fuji', 'fujifilm', 'olympus',
              'oympus', 'panasonic', 'samsung', 'pentax', 'leica',
              'ricoh', 'casio', 'vivitar', 'benq', 'kodak', 'minox',
              'pen']

    prd_url = "http://www.amazon.com/dp/" + prd_id

    prd = {}
    prd['amazon_id'] = prd_id
    prd['amazon_url'] = prd_url

    logger.info('fetching the product info from %s' % prd_url)

    prd_soup = get_soup(prd_url, proxies)

    prd_title = prd_soup.find("h1", {"id": "title"}).text
    prd['amazon_raw_title'] = prd_title

    prd_title = prd_title.split()

    end = 0
    for index, item in enumerate(prd_title):
        if 'MP' == item:
            end = index
            break
        elif item.endswith('MP') and len(item) > 2:
            end = index + 1
            break

    size = len(prd_title)
    if end > 0:
        size = end + 1
    if prd_title[0].lower() in brands:
        if end > 0:
            prd_title = ' '.join(prd_title[:end-1])
        else:  prd_title = ' '.join(prd_title[:4])
    elif size > 1 and prd_title[1].lower() in brands:
        if end > 0:
            prd_title = ' '.join(prd_title[1:end-1])
        else: prd_title = ' '.join(prd_title[1:5])
    elif size > 2 and prd_title[2].lower() in brands:
        if end > 0:
            prd_title = ' '.join(prd_title[2:end-1])
        else: prd_title = ' '.join(prd_title[2:6])
    elif size > 3 and prd_title[3].lower() in brands:
        if end > 0:
            prd_title = ' '.join(prd_title[3:end-1])
    else:
        prd_title = '###' + ' '.join(prd_title)
        print prd_title

    if '/' in prd_title:
        index = prd_title.index('/')
        prd_title = prd_title[:index-1]

    prd['amazon_title'] = prd_title


    # TODO: fetch the technical details

    
    return prd

def amazon_prd_img(prd_id, target_dir=".", proxies=None):
    prd_url = "http://www.amazon.com/dp/" + prd_id
    logger.info("fetch picture from %s" % prd_url)
    prd_soup = get_soup(prd_url, proxies)

    img_container = prd_soup.find("div", {"id": "main-image-container"})

    img_container = img_container.find('div', {"id": "imgTagWrapperId"})

    image = img_container.find('img')

    data = get_response(image['src'], proxies)
    save = open(os.path.join(target_dir, prd_id) + '.jpg', 'wb')
    save.write(data)
    save.close()

def amazon_reviews(prd_id, proxies=None):
    prd_reviews = []
    base_review_url = "http://www.amazon.com/product-reviews/" + prd_id + "/?ie=UTF8&showViewpoints=0&pageNumber=" + "%s" + "&sortBy=bySubmissionDateDescending"

    pagn = "1"
    while True:
        prd_review_url = base_review_url % pagn
        logger.info('fetch reviews from %s' % prd_review_url)

        revs_html = get_response(prd_review_url, proxies)

        revs_soup = parse_soup(revs_html)

        reviews = extract_reviews(unicode(str(revs_html),
                                          errors="ignore"), prd_id)

        if reviews:
            prd_reviews.extend(reviews)

        pagn_bar = revs_soup.find("span", {"class": "paging"})
        pagn_bar_str = str(pagn_bar)
        #print pagn_bar_str
        # before: Oct, 2013
        #mch = re.search(r"cm_cr_pr_top_link_next_([0-9]+)", pagn_bar_str)

        # modified on: 24th, Feb 2014
        mch = re.search(r"pageNumber=([0-9]+)\">Next", pagn_bar_str)

        if mch is None:
            break
        
        if len(mch.groups()) > 0:
            pagn = mch.group(1)
            print pagn
            revs_soup.decompose()
        else:
            revs_soup.decompose()
            break
    return prd_reviews

def extract_reviews(data, pid):
    reviews = []
    #model_match = re.search(r'product\-reviews/([A-Z0-9]+)/ref\=cm_cr_pr', str)
    data = remove_extra_spaces(data)
    data = remove_script(data)
    data = remove_style(data)

    table_reg = re.compile(r"<table id=\"productReviews.*?>(.*)</table>")
    table_match = table_reg.search(data)

    if table_match:
        table_cont = table_match.group(1)
        # before Oct 2013
        #review_reg = re.compile(r"-->(.*?)(!--|$)")

        # modified on 24th, Feb 2014
        review_reg = re.compile(r"<div style=\"margin-left:0.5em;\">(.*?)</div> <!-- ")
        review_matches = review_reg.findall(table_cont)
        if len(review_matches) > 0:
            #print "Review Number: ", len(review_matches)
            review_num = 0
            for index, block in enumerate(review_matches):
                review = {}

                help_reg = re.compile(
                    r"<div style=\"margin-bottom:0.5em;\"> ([\d]+) of ([\d]+) people found the following review helpful </div>")
                help_match = help_reg.search(block)

                if help_match:
                    #print "HELP: " + help_match.group(1) + " of " + help_match.group(2)
                    review["helpful_votes"] = int(help_match.group(1))
                    review["total_votes"] = int(help_match.group(2))

                block_reg = re.compile(
                    r"\<div.*?star_([1-5])_([05]).*?\<b\>(.*?)\<\/b\>.*?nobr\>(.*?)\<\/nobr")
                block_match = block_reg.search(block)
                if block_match:
                    review_num += 1
                    rating = block_match.group(1) + block_match.group(2)
                    print "Rating:\t" + rating
                    review["overall_rating"] = float(rating)/10.0

                    title = block_match.group(3)
                    # print "Title:\t" + title
                    review["title"] = title

                    date = block_match.group(4)
                    date_reg = re.compile(r"([a-zA-Z]+) ([0-9]+), ([0-9]+)")
                    date_match = date_reg.search(date)
                    if date_match:
                        month = date_match.group(1)
                        if(month == "January"):
                            month = "01"
                        elif(month == "February"):
                            month = "02"
                        elif(month == "March"):
                            month = "03"
                        elif(month == "April"):
                            month = "04"
                        elif(month == "May"):
                            month = "05"
                        elif(month == "June"):
                            month = "06"
                        elif(month == "July"):
                            month = "07"
                        elif(month == "August"):
                            month = "08"
                        elif(month == "September"):
                            month = "09"
                        elif(month == "October"):
                            month = "10"
                        elif(month == "November"):
                            month = "11"
                        elif(month == "December"):
                            month = "12"
                        else:
                            month = "NULL"

                        new_date = month + " " + \
                            date_match.group(2) + ", " + date_match.group(3)
                        # print "Date:\t" + new_date
                        review["date"] = new_date

                        date_time = time.mktime(time.strptime(new_date, '%m %d, %Y'))
                        review['date_time'] = date_time

                        user_reg = re.compile(
                            r"\>By.*?\<\/div\>.*?\<a href=\"(.*?)\".*?\<span style =.*?\>(.*?)\<\/span\>\<\/a\>(.*?) - \<a href=\"(.*?)\"?\>See all my reviews\<\/a\>")
                        user_match = user_reg.search(block)

                        if user_match:
                            review["user"] = {}
                            # print "User:\t" + user_match.group(2)
                            review["user"]["name"] = user_match.group(2)
                            # print "User URL:\t" + user_match.group(1)
                            review["user"]["link"] = user_match.group(1)
                            # print "User Location:\t" + user_match.group(3)
                            review["user"]["location"] = user_match.group(3)
                            # print "User's Reviews:\t" + user_match.group(4)
                            review["user"]["others"] = user_match.group(4)

                            review["user_id"] = review["user"]["link"]
                        else:
                            #user_reg = re.compile(r"\>By.*?\<\/div\>.*?<a href=\"(.*?)\".*?\<span style = .*?\>(.*?)\<\/span\>\<\/a\>")
                            print "Oops 5 - Cannot match with user profile!"
                        purchase_reg = re.compile(
                            r"\<b class=.*?\>Amazon Verified Purchase\<\/b\>\<span")
                        purchase_match = purchase_reg.search(block)
                        if purchase_match:
                            # print "Purchased: " + "True"
                            review["purchased"] = 1
                        else:
                            review["purchased"] = 0

                        #text = remove_cont_withtags(block)
                        cont_reg = re.compile(r"<div class=\"reviewText\">(.*?)</div>")
                        content = cont_reg.search(block).group(1)

                        #print "Text:\t" + content
                        review["content"] = content.strip(' \t\n\r')
                        # print
                    else:
                        print "Oops 4: " + date

                else:
                    print "Oops 3: " + str(index)
                    
                #print "Oops 3.0: " + str(index)
                #print review

                review["product_id"] = pid

                if not "content" in review or len(review["content"]) == 0:
                    continue
                
                reviews.append(review)
        else:
            print "Oops2"
    else:
        print "Oops"

    return reviews



########NEW FILE########
__FILENAME__ = dpreviews
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.core.base import *

import time
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def dp_specs(spec_url, proxies=None):
    soup = get_soup(spec_url, proxies)

    specs_div = soup.find('div', {"class": "specificationsPage"})
    if specs_div is None:
        return None
    hds_items = specs_div.findAll('thead')
    specs_items = specs_div.findAll('tbody')

    techs = []
    for i, item in enumerate(hds_items):
        inner_item = specs_items[i]
        key = ""
        if item.find('th'):
            key = item.find('th').getText()
            
        else:
            continue
        tech_items = []
        for spec in inner_item.findAll('tr'):
            if spec.find('th'):
                title = spec.find('th', {"class": "label"}).getText()
                value = unicode(spec.find('td', {"class": "value"})).encode('ascii', 'ignore')

                tech = (title, value)
                tech_items.append(tech)
        techs.append((key, tech_items))

    return techs
########NEW FILE########
__FILENAME__ = engadget
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.core.base import *

import time
import logging

try:
    import simplejson as json
except Exception, e:
    import json

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

base_url = 'http://www.engadget.com/'

def gdgt_prds(category_id, proxies=None):
    """
    category_id : 2 for camera
    36 for laptop
    """
    url = base_url + 'a/category_filter/?category_id=%d&sort=score&offset=%d'
    offset = 0
    while True:
        print 'begin with %d ...' % offset
        search_url = url % (category_id, offset)
        #print 'fetching %s' % search_url
        html = get_response(search_url, proxies)
        json_doc = json.loads(html)

        if json_doc['success']:
            for prd in json_doc['products']:
                if prd['availability'] == 1:
                    yield prd 
                # pid = prd['product_id']
                # json_file = open(os.path.join('engadget_prd', pid), 'w')
                # json_file.write(
                #     json.dumps(prd, sort_keys=True, indent=4, separators=(',', ': ')))
                # json_file.close()
        else:
            break
        offset += 40

def _get_amazon_product(gdgt_url):
    """ Check the relevant amazon url

    @param gdgt_url - the gdgt product url
    """
    soup = get_soup(gdgt_url)
    price_compare_divs = soup.findAll(
        'div', {'class': 'price-comparison-retailer'})
    if price_compare_divs:
        print 'HAS COMPARE'
        for div in price_compare_divs:
            link = div.find('a')
            if link:
                if link.find('img') and link.find('img')['alt'] == 'Amazon.com':
                    print link['href']
                    return _get_amazon_pid(link['href'])
    else:
        print 'WARNING: None amazon related'
    print None


def _get_amazon_pid(url):
    #header = get_header(mech, url)
    soup = get_soup(url)
    amazon_url = soup.head.find('link', {'rel': 'canonical'})['href']
    amazon_pid = amazon_url.split('/')[-1]
    return (amazon_url, amazon_pid)

def get_amazon_ids(logfile):
    logs = open(logfile, 'r')
    

    outamazon = open('outamazon.txt', 'w')

    for line in logs:
        pid, name, url, picture = line.strip().split('\t')
        item = _get_amazon_product(url)
        if item is None:
            continue
        amz_url, amz_pid = item
        if amz_url is not None:
            outamazon.write("%s\t%s\t%s\t%s\t%s\n" % (amz_pid, name, amz_url, url, picture))
            outamazon.flush()
    outamazon.close()


########NEW FILE########
__FILENAME__ = yelp
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.core.base import *

import time
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def yelp_biz_ids(cate, loc, proxies=None):
    start = 0
    step = 10
    while True:
        url = "http://www.yelp.com/search?cflt=%s&start=%d&find_loc=%s" % (cate, start, loc)

        logger.info('fetching from %s' % url)

        html = get_response(url, proxies)
        if not html:
            logger.info('canot fetch %s' % url)
            return
        soup = parse_soup(html)
        
        bussiness_divs = soup.findAll('div', {'class': "search-result natural-search-result biz-listing-large"})
        for div in bussiness_divs:
            bussiness_story = div.find('div', {'class': "media-story"})
            title_div = bussiness_story.find('h3', {"class": "search-result-title"}).find('a')
            url = 'http://www.yelp.com%s' % title_div['href']
            #title = title_div.text
            #print '%s -> %s' % (title, url)
            yield url
        start += step
        time.sleep(5)

def yelp_biz(biz_url, proxies=None):
    biz = {}
    biz['url'] = biz_url

    biz_url = '%s?nb=1' % biz_url # the argument 'nb=1' is required

    logger.info('fetching %s' % biz_url)

    soup = get_soup(biz_url, proxies)



    top_self_div = soup.find('div', {'class': "top-shelf"})

    title_div = top_self_div.find('h1', {'itemprop': "name"})
    title = title_div.text
    biz['title'] = title

    rating_div = top_self_div.find(
        'div', {'class': "rating-info clearfix"})
    review_span = rating_div.find('span', {"itemprop": "reviewCount"})
    review_count = int(review_span.text)
    biz['review_num'] = review_count

    price_category_div = top_self_div.find(
        'div', {'class': "price-category"})
    price_range = price_category_div.find(
        'span', {"class": "business-attribute price-range"})
    if price_range:
        biz['price_range'] = len(price_range.text.strip())

    categories = map(lambda x: (x.text, 'http://www.yelp.com%s' %
                     x['href']), price_category_div.findAll('a'))
    biz['categories'] = categories

    map_div = top_self_div.find('div', {"class": "mapbox-text"})
    address_div = map_div.find('li', {"class": "address"})
    address = {}
    for span in address_div.findAll('span'):
        if 'itemprop' not in span:
            continue
        key = span['itemprop']
        value = span.text
        address[key] = value
    biz['address'] = address

    action_url = soup.find('ul', {'class': 'iconed-list action-link-list'}).find('a')['href']

    biz_id = action_url.split('&')[0].split('=')[-1]
    
    biz['id'] = biz_id

    
    biz["longitude"] = soup.head.find("meta", {"property": "place:location:longitude"})["content"]
    biz["latitude"] = soup.head.find("meta", {"property": "place:location:latitude"})["content"]


    # reviews
    reviews_page_div = soup.find('div', {'class': "page-of-pages"})
    pages = int(reviews_page_div.text.split()[-1])

    reviews_div = soup.find('div', {'class': "review-list"})

    reviews = reviews_in_page(reviews_div)

    for page in xrange(1, pages + 1):
        start = page * 40

        rurl = '%s&start=%d' % (biz_url, start)
        print 'review url: %s' % rurl
        
        page = get_soup(rurl, proxies).find('div', {'class': "review-list"})
        for r in reviews_in_page(page):
            reviews.append(r)
    biz['reviews'] = reviews

    return biz

def reviews_in_page(soup):

    reviews = []

    for review_div in soup.findAll("div", {'class': 'review review-with-no-actions'}):
        review = {}

        passport_info_ul = review_div.find(
            'ul', {'class': 'user-passport-info'})
        author = {}
        if passport_info_ul:
            author_name_li = passport_info_ul.find(
                'li', {'class': 'user-name'}).find('a')
            if not author_name_li:
                continue
            name = author_name_li.text
            author_url = author_name_li['href']
            author_id = author_url.split('=')[-1]
            author_url = 'http://www.yelp.com%s' % author_url
            author['name'] = name
            author['id'] = author_id
            author['url'] = author_url

        author_location_li = passport_info_ul.find(
            'li', {'class': 'user-location'})
        if author_location_li:
            author['location'] = author_location_li.text
        review['author'] = author

        review_content_div = review_div.find(
            'div', {'class': 'review-content'})
        rating = float(review_content_div.find(
            "meta", itemprop="ratingValue")["content"])
        review['rating'] = rating

        date = review_content_div.find(
            'meta', itemprop='datePublished')['content']
        review['date'] = date

        checkin_div = review_div.find(
            'span', {'class': 'i-wrap ig-wrap-common i-checkin-burst-blue-small-common-wrap badge checkin checkin-irregular'})
        if checkin_div:
            checkin = int(checkin_div.text.strip().split()[0])
            review['checkin'] = checkin

        text_div = review_div.find(
            'p', {'class': 'review_comment ieSucks'})
        
        if not text_div:
            continue

        ps = []

        brs = text_div.findAll('br')
        if not brs:
            ps.append(text_div.text.encode('ascii', 'ignore'))
        else:
            for i, br in enumerate(text_div.findAll('br')):
                if i == 0:
                    prev = br.previousSibling
                    if not(prev and isinstance(prev, NavigableString)):
                        continue
                    ps.append(prev.strip().encode('ascii', 'ignore'))

                next = br.nextSibling
                
                if not (next and isinstance(next, NavigableString)):
                    continue
                ps.append(next.strip().encode('ascii', 'ignore'))

        review['content'] = '\n'.join(ps)

        useful_div = review_div.find("li", class_="useful ufc-btn")
        if useful_div:
            useful = useful_div.find(
                "span", recursive=False).text
            review['useful'] = useful

        funny_div = review_div.find("li", class_="funny ufc-btn")
        if funny_div:
            funny = funny_div.find(
                "span", recursive=False).text
            review['funny'] = funny

        cool_div = review_div.find("li", class_="cool ufc-btn")
        if cool_div:
            cool = cool_div.find(
                "span", recursive=False).text
            review['cool'] = cool

        reviews.append(review)
    return reviews

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

import requests

# For supporting socks4/5 proxy;
# It is a fork of the Requests module, with additional SOCKS support
import requesocks
import lxml.etree
from urllib2 import HTTPError
from BeautifulSoup import BeautifulSoup, NavigableString, Tag
from StringIO import StringIO

import logging

from crawler.core.utils import *

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

lxml_parser = lxml.etree.HTMLParser()


session = requesocks.session()


def parse_lxml(content):
    """ from gist: https://gist.github.com/kanzure/5385691

    A possible safer way to parse HTML content with lxml. This will
    presumably not break on poorly formatted HTML.
    """

    if not isinstance(content, StringIO):
        if not isinstance(content, str) and not isinstance(content,
                                                           unicode):
            raise Exception("input content must be a str or StringIO"
                            "instead of " + str(type(content)))
        content = StringIO(content)

    lxml_tree = lxml.etree.parse(content, lxml_parser)
    return lxml_tree


def parse_soup(content):
    try:
        soup = BeautifulSoup(content, convertEntities=BeautifulSoup.HTML_ENTITIES)
        return soup
    except HTTPError, e:
        logger.error("%d: %s" % (e.code, e.msg))
        return

def get_data(url, proxies=None):
    data = requests.get(url).read()
    return data

def get_response(url, proxies=None):
    try:
        if proxies:
            if url.startswith('http:') and 'http' in proxies:
                prox = proxies['http']
                if prox.startswith('socks'):
                    session.proxies = proxies
                    r = session.get(url)
                else:  # http proxy
                    r = requests.get(url, proxies = proxies)
            elif url.startswith('https:') and 'https' in proxies:
                prox = proxies['https']
                if prox.startswith('socks'):
                    session.proxies = proxies
                    r = session.get(url)
                else:
                    r = requests.get(url, proxies = proxies)
            else:  # ohter types of requests, e.g., ftp
                r = requests.get(url, proxies = proxies)

        else:  # without proxy
            r = requests.get(url)
    except ValueError:
        logger.error('Url is invalid: %s' % url)
        return
    except requests.exceptions.ConnectionError:
        logger.error("Error connecting to %s" % url)
        return

    if r.status_code != 200:
        logger.error('Status code is %d on %s' % (r.status_code, url))
        return

    return r.content


def get_soup(url, proxies=None):
    html = get_response(url, proxies)
    return parse_soup(html)

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

import os, sys, re

from lxml.html.clean import clean_html
from lxml.html.soupparser import fromstring

import logging


logger = logging.getLogger('crawler.' + __name__)
logger.setLevel(logging.DEBUG)

def santitize_html(html):
    html = clean_html(html)
    return html

def remove_extra_spaces(data):
    p = re.compile(r'\s+')
    return p.sub(' ', data)


def remove_script(data):
    p = re.compile(r'<script .*?>.*?</script>')
    return p.sub(' ', data)

def remove_style(data):
    p = re.compile(r'<style .*?>.*?</style>')
    return p.sub(' ', data)

def remove_cont_withtags(data):
    style_reg = re.compile(r"\<style.*?\<\/style\>")
    data = style_reg.sub("", data)

    li_reg = re.compile(r"\<li.*?\<\/li\>")
    data = li_reg.sub("", data)

    table_reg = re.compile(r"\<table.*?\<\/table\>")
    data = table_reg.sub("", data)

    td_reg = re.compile(r"\<td.*?\<\/td\>")
    data = td_reg.sub("", data)
    
    div_reg = re.compile(r"\<div.*?\<\/div\>")
    data = div_reg.sub("", data)

    ul_reg = re.compile(r"\<ul.*?\<\/ul\>")
    data = ul_reg.sub("", data)

    a_reg = re.compile(r"\<a.*?\>.*?\<\/a\>")
    data = a_reg.sub("", data)


    data = re.sub(r"\<\/div\>", "", data)
    data = re.sub(r"\<div.*?\>.*?\<", "", data)
    data = re.sub(r"\<\/table\>", "", data)
    data = re.sub(r"\<\/td\>", "", data)
    data = re.sub(r"\<\/tr\>", "", data)

    data = re.sub(r"\<br \/\>", "\n", data)
    data = re.sub(r"[\s]+?\<", " ", data)
    data = re.sub(r"\n+", "\n", data)
    return data

########NEW FILE########
__FILENAME__ = dp_crawler
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.contrib.dpreviews import *

from optparse import OptionParser
import os
import time
import pprint
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


usage = "usage %prog [options] arg"
parser = OptionParser(usage=usage)
parser.add_option('-s', "--seed", dest="initial search url",
                  help="the initial search url")
parser.add_option("-o", "--output", dest="output_dir",
              help="write out to DIR")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

(options, args) = parser.parse_args()

def main():

    proxies = {'http': 'http://23.244.180.162:8089', 'https': 'http://23.244.180.162:8089'}

    socket_proxies = {'http': 'socket5://1.ss.shadowsocks.net:65535', 'https': 'http://23.244.180.162:8089'}

    

    techs = dp_specs("http://www.dpreview.com/products/panasonic/compacts/panasonic_dmcsz3/specifications")
    print "<table>"
    for k in techs.keys():
        print "<thead><tr><th>%s<th></tr></thead>" % k
        print "<tbody>"
        for key, value in techs[k]:
            print '<tr><td>%s</td><td>%s</td></tr>' % (key, value)
        print "</tbody>"
    # for k in techs:
    #     print '<tr><td>%s</td><td>%s</td></tr>' % (k, techs[k].encode('ascii', "ignore"))
    print "</table>"
    # for dirname, dirnames, filenames in os.walk('D:\workspace\camera\small'):
    #     for filename in filenames:
    #         file_path = os.path.join(dirname, filename)
            
    #         pid = filename[:-5]
    #         if not os.path.isfile(os.path.join("D:\workspace\camera\images", pid) + ".jpg"):
    #             amazon_prd_img(pid, "D:\workspace\camera\images")

    #         print pid
   
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = engadgete_crawler
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.contrib.engadget import *

from optparse import OptionParser

import time
import pprint
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


usage = "usage %prog [options] arg"
parser = OptionParser(usage=usage)
parser.add_option('-c', "--category", dest="category",
                  help="the target bussiness category")
parser.add_option("-l", "--location", dest="location",
              help="the target location/country")
parser.add_option("-o", "--output", dest="output_dir",
              help="write out to DIR")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

(options, args) = parser.parse_args()

def main():
    # output = open('gdgt_laptops.txt', 'w')
    # for prd in gdgt_prds(36):
    #     content = "%s\t%s\t%s\t%s\n" % (prd['product_id'], prd['name'].encode("ascii", 'ignore') ,prd['url'], prd['picture'])
    #     print prd['product_id'], '\t', prd['url']
    #     output.write(content)
    # output.close()
    get_amazon_ids('gdgt_laptops.txt')

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = yelp_crawler
#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Copyright (c) 2014 Feng Wang <wffrank1987@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

from crawler.contrib.yelp import *

from optparse import OptionParser

import time
import pprint
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


usage = "usage %prog [options] arg"
parser = OptionParser(usage=usage)
parser.add_option('-c', "--category", dest="category",
                  help="the target bussiness category")
parser.add_option("-l", "--location", dest="location",
              help="the target location/country")
parser.add_option("-o", "--output", dest="output_dir",
              help="write out to DIR")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

(options, args) = parser.parse_args()

def main():
    """
    Warnining: your ip would be banned by yelp if you don't use proxy

    goagent proxy: https://code.google.com/p/goagent/
    http://www.hidemyass.com/proxy-list/

    """


    proxies = {'http': 'http://23.244.180.162:8089', 'https': 'http://23.244.180.162:8089'}
    #proxies = {'http': 'socks5://71.235.242.33:38626'}
    #yelp_biz_ids("restaurants", "new+york", proxies)
    
    for biz_url in yelp_biz_ids("restaurants", "New+York", proxies):
        biz = yelp_biz(biz_url, proxies)
        pprint.pprint(biz)

if __name__ == "__main__":
    main()

########NEW FILE########
