__FILENAME__ = items
from scrapy.item import Item, Field

class CocktailItem(Item):
	title = Field()
	picture = Field()
	url = Field()
	source = Field()
	ingredients = Field()

	# will be indexed too, but not shown in the list. Primary for
	# ingredients of ingredients like infusions on seriouseats.com
	extra_ingredients = Field()

########NEW FILE########
__FILENAME__ = pipelines
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html

class CocktailsPipeline(object):
    def process_item(self, item, spider):
        return item

########NEW FILE########
__FILENAME__ = settings
# Scrapy settings for cocktails project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'cocktails'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['cocktails.spiders']
NEWSPIDER_MODULE = 'cocktails.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

#DEPTH_LIMIT = 2

########NEW FILE########
__FILENAME__ = cocktaildb
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = css_to_xpath('.recipeMeasure')

class CocktailDbSpider(CrawlSpider):
	name = 'cocktaildb'
	allowed_domains = ['www.cocktaildb.com']
	start_urls = ['http://www.cocktaildb.com']

	rules = (
		Rule(SgmlLinkExtractor(allow=r'/recipe_detail\b'), callback='parse_recipe'),
		Rule(SgmlLinkExtractor(allow=r'.*')),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select('//h2').extract():
			break
		else:
			return []

		ingredients = hxs.select(xp_ingredients).extract()

		return [CocktailItem(
			title=html_to_text(title),
			picture=None,
			url=response.url,
			source='CocktailDB',
			ingredients=map(html_to_text, ingredients),
		)]

########NEW FILE########
__FILENAME__ = cocktailtimes
from urlparse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_header = css_to_xpath('.header') + '/text()'
xp_ingredients = css_to_xpath('.story') + ("[1]//text()["
	"preceding::text()["
		"normalize-space(self::text()) = 'Ingredients:'"
	"]"
"]["
	"starts-with(normalize-space(self::text()), '-')"
"]")
xp_picture = ("//img["
	"preceding::comment()["
		"contains(self::comment(), ' COCKTAIL PHOTO ')"
	"]"
"]/@src")

class CocktailTimesSpider(CrawlSpider):
	name = 'cocktailtimes'
	allowed_domains = ['www.cocktailtimes.com']
	start_urls = ['http://www.cocktailtimes.com']

	rules = (
		Rule(
			SgmlLinkExtractor(
				allow=(
					r'/whiskey/.+',
					r'/bourbon/.+',
					r'/scotch/.+',
					r'/vodka/.+',
					r'/gin/.+',
					r'/rum/.+',
					r'/tequila/.+',
					r'/brandy/.+',
					r'/hot/.+',
					r'/blend/.+',
					r'/tropical/.+',
					r'/shooter/.+',
					r'/original/.+')
			),
			callback='parse_recipe',
			follow=True
		),
		Rule(SgmlLinkExtractor(allow=r'.*')),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		ingredients = [html_to_text(s).split('-', 1)[1].strip() for s in hxs.select(xp_ingredients).extract()]
		if not ingredients:
			return []

		for title in hxs.select(xp_header).extract():
			break
		else:
			return []

		for picture in hxs.select(xp_picture).extract():
			picture = urljoin(response.url, picture)
		else:
			picture = None

		return [CocktailItem(
			title=html_to_text(title),
			picture=picture,
			url=response.url,
			source='Cocktail Times',
			ingredients=ingredients,
		)]

########NEW FILE########
__FILENAME__ = dradamsbitters
import re
from urlparse import urljoin
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

class DrAdamsBittersSpider(BaseSpider):
	name = 'dradamsbitters'
	start_urls = ['http://bokersbitters.co.uk/']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		urls = hxs.select("//a[text() = 'Bitters']/following-sibling::ul//a/@href").extract()
		scraped_recipes = set()

		for url in urls:
			yield Request(urljoin(response.url, url), partial(
				self.parse_recipe,
				num_recipes=len(urls),
			 	scraped_recipes=scraped_recipes
			))

	def parse_recipe(self, response, num_recipes, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		ingredients = []
		for paragraph in hxs.select('//p'):
			l = []

			for line in split_at_br(paragraph, include_blank=True) + ['']:
				line = html_to_text(line).strip()

				if line:
					l.append(line)
					continue

				if len(l) >= len(ingredients):
					ingredients = l
					paragraph_with_ingredients = paragraph

				l = []

		title = hxs.select("//text()[contains(self::text(), ' such as the ')]")
		if title:
			title = html_to_text(title[0].extract())
			title = re.search(r'(?<= such as the ).+?(?=,|;| created )', title).group(0)
		else:
			title = paragraph_with_ingredients.select('./preceding-sibling::p')[-1]
			title = html_to_text(title.extract()).rstrip(';')

		yield CocktailItem(
			title=title,
			picture=None,
			url=response.url,
			source="Dr. Adam Elmegirab's",
			ingredients=ingredients
		)

		scraped_recipes.add(title.lower())
		if len(scraped_recipes) == num_recipes:
			yield Request(
				urljoin(
					response.url,
					hxs.select("//a[text() = 'Archives']/@href")[0].extract()
				),
				partial(
					self.parse_archive,
					scraped_recipes=scraped_recipes
				)
			)

	def parse_archive(self, response, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select("//a[contains(text(), 'Recipes')]/@href").extract():
			yield Request(urljoin(response.url, url), partial(
				self.parse_archive_recipes,
				scraped_recipes=scraped_recipes
			))

	def parse_archive_recipes(self, response, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		for i, title_node in enumerate(hxs.select('//u[b][not(parent::div)] | //div[u[b]]')):
			title = html_to_text(title_node.extract()).strip().strip('.').title()
			if title.lower() in scraped_recipes:
				continue

			ingredients = []
			for line in split_at_br(title_node.select('./following-sibling::node()[not(preceding::u[b][%d])]' % (i + 2)), include_blank=True, newline_elements=['br', 'div', 'b']) + ['']:
				line = html_to_text(line).strip()

				if not line:
					if len(ingredients) == 1:
						ingredients = []
					if ingredients:
						break
					continue

				ingredients.append(line)

			if not ingredients:
				continue

			yield CocktailItem(
				title=title,
				picture=None,
				url=response.url,
				source="Dr. Adam Elmegirab's",
				ingredients=ingredients
			)

########NEW FILE########
__FILENAME__ = drinkboy
from urlparse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = css_to_xpath('.ingredient')

class DrinkBoySpider(CrawlSpider):
	name = 'drinkboy'
	allowed_domains = ['www.drinkboy.com']
	start_urls = ['http://www.drinkboy.com/Cocktails/']

	rules = (
		Rule(SgmlLinkExtractor(allow=r'/Cocktails/Recipe.aspx'), callback='parse_recipe'),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select("//*[@itemprop='name']").extract():
			break
		else:
			return []

		for picture in hxs.select("//img[@itemprop='image']/@src").extract():
			picture = urljoin(response.url, picture)
			break
		else:
			picture = None

		ingredients = hxs.select(xp_ingredients).extract()

		return [CocktailItem(
			title=html_to_text(title),
			picture=picture,
			url=response.url,
			source='DrinkBoy',
			ingredients=map(html_to_text, ingredients),
		)]

########NEW FILE########
__FILENAME__ = drinksmixer
import re

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_title = css_to_xpath('.recipe_title')
xp_ingredients = css_to_xpath('.ingredient')

class DrinksMixerSpider(CrawlSpider):
	name = 'drinksmixer'
	allowed_domains = ['www.drinksmixer.com']
	start_urls = ['http://www.drinksmixer.com/']

	rules = (
		Rule(SgmlLinkExtractor(allow=r'/drink[^/]+.html$'), callback='parse_recipe'),
		Rule(SgmlLinkExtractor(allow=r'/cat/')),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select(xp_title).extract():
			break
		else:
			return []

		ingredients = hxs.select(xp_ingredients).extract()

		return [CocktailItem(
			title=re.sub(r'\s+recipe$', '', html_to_text(title)),
			picture=None,
			url=response.url,
			source='Drinks Mixer',
			ingredients=map(html_to_text, ingredients),
		)]

########NEW FILE########
__FILENAME__ = esquire
from urlparse import urljoin

from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, unescape

xp_ingredient = css_to_xpath('.ingredient')

class EsquireSpider(SitemapSpider):
	name = 'esquire'
	sitemap_urls = ['http://www.esquire.com/robots.txt']
	sitemap_rules = [('/drinks/.*-recipe$', 'parse_recipe')]

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select("//meta[@property='og:title']/@content").extract():
			break
		else:
			return []

		for picture in hxs.select("//*[@id='drink_infopicvid']/img/@src").extract():
			picture = urljoin(response.url, picture)
			break
		else:
			picture = None

		ingredients = []
		for node in hxs.select("//ul[@id='ingredients']/li"):
			parts = []

			for child in node.select('* | text()'):
				text = html_to_text(child.extract())

				if 'ingredient' in (child.xmlNode.prop('class') or '').split():
					text = text.split('--')[-1]

				text = text.strip()

				if not text:
					continue

				parts.append(text)

			ingredients.append(' '.join(parts))

		# don't crawl recipes like 'American Whiskey & Canadian Whisky',
		# that only consist of pouring a single spirit into a glass.
		if len(ingredients) <= 1:
			return []

		return [CocktailItem(
			title=unescape(title),
			picture=picture,
			url=response.url,
			source='Esquire',
			ingredients=ingredients
		)]

########NEW FILE########
__FILENAME__ = kindredcocktails
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = css_to_xpath('.cocktail-ingredients tr')

class KindredCocktails(CrawlSpider):
    name = 'kindredcocktails'
    allowed_domains = ['www.kindredcocktails.com']
    start_urls = ['http://www.kindredcocktails.com']

    rules = (
        Rule(SgmlLinkExtractor(allow=r'/cocktail/[^/?]+$'), callback='parse_recipe'),
        Rule(SgmlLinkExtractor(allow=r'.*')),
    )

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        for title in hxs.select('//h1').extract():
            break
        else:
            return []

        ingredients = hxs.select(xp_ingredients).extract()

        return [CocktailItem(
            title=html_to_text(title),
            picture=None,
            url=response.url,
            source='Kindred Cocktails',
            ingredients=map(html_to_text, ingredients),
        )]

########NEW FILE########
__FILENAME__ = kingcocktail
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

class kingCocktailSpider(BaseSpider):
	name = 'kingcocktail'
	start_urls = [
		'http://www.kingcocktail.com/bitters-recipes.html',
		'http://www.kingcocktail.com/bitters-recipes2.html',
	]

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select("//strong[normalize-space(text()) != '']"):
			lines = split_at_br(title.select("ancestor-or-self::node()/following-sibling::node()[not(self::span[starts-with(text(), 'Stir')])]"), include_blank=True)
			ingredients = []

			for line in lines[1 + (not lines[1][:1].isdigit()):]:
				line = html_to_text(line).strip()

				if not line:
					break

				if re.search(r'\b(?:shaken?|stir(?:red)?|fill glass|preparation)\b', line, re.I):
					break

				ingredients.append(line)

			yield CocktailItem(
				title=html_to_text(title.extract()).strip().rstrip('*').title(),
				picture=None,
				url=response.url,
				source="Dale DeGroff's",
				ingredients=ingredients
			)

########NEW FILE########
__FILENAME__ = liquor
from urlparse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

class LiqourSpider(CrawlSpider):
	name = 'liquor'
	allowed_domains = ['liquor.com']
	start_urls = ['http://liquor.com/recipes/']

	rules = (
		Rule(SgmlLinkExtractor(allow=(r'/recipes/page/',))),
		Rule(SgmlLinkExtractor(allow=(r'/recipes/.+')), callback='parse_recipe'),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select('//h1').extract():
			break
		else:
			return []

		for picture in hxs.select("//img[@itemprop='photo']/@src").extract():
			picture = urljoin(response.url, picture)
			break
		else:
			picture = None

		ingredients = hxs.select("//*[@itemprop='ingredient']").extract()

		return [CocktailItem(
			title=html_to_text(title),
			picture=picture,
			url=response.url,
			source='Liquor.com',
			ingredients=map(html_to_text, ingredients),
		)]

########NEW FILE########
__FILENAME__ = monkey47
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

xp_title = css_to_xpath('.entry-title')
xp_ingredients = css_to_xpath('.entry-content p') + '[1]'
xp_previous_link = css_to_xpath('.nav-previous a') + '/@href'

class Monkey47Spider(BaseSpider):
	name = 'monkey47'
	start_urls = ['http://www.monkey47.com/wordpress/tag/gin_cocktail_rezepte/']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select(xp_title + '//a/@href').extract():
			yield Request(urljoin(response.url, url), self.parse_recipe)

		for url in hxs.select(xp_previous_link).extract():
			yield Request(urljoin(response.url, url), self.parse)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select(xp_title).extract():
			break
		else:
			return []

		ingredients = []
		for ingredient in split_at_br(hxs.select(xp_ingredients)):
			if not ingredient.endswith(':'):
				ingredients.append(html_to_text(ingredient))

		return [CocktailItem(
			title=html_to_text(title).split(':')[-1].split(u'\u2013')[-1].strip(),
			picture=None,
			url=response.url,
			source='Monkey 47 Blog',
			ingredients=ingredients
		)]

########NEW FILE########
__FILENAME__ = ohgosh
from urlparse import urljoin, urlparse
from itertools import groupby
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_recipe_links = css_to_xpath('.cocktail') + '//a[1]/@href'

class OhGoshSpider(BaseSpider):
	name = 'ohgosh'
	start_urls = ['http://ohgo.sh/cocktail-recipes/']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		links = hxs.select(xp_recipe_links).extract()
		links = [urljoin(response.url, url) for url in links]
		links.sort()

		for page_url, recipe_urls in groupby(links, lambda url: url.split('#')[0]):
			yield Request(page_url, partial(
				self.parse_recipes,
				recipe_urls=list(recipe_urls)
			))

	def parse_recipes(self, response, recipe_urls):
		hxs = HtmlXPathSelector(response)

		for url in recipe_urls:
			node = hxs.select("//*[@id='%s']" % urlparse(url).fragment)[0]

			for picture in node.select('./preceding-sibling::*[1]/img/@src').extract():
				picture = urljoin(url, picture)
				break
			else:
				picture=None

			ingredients = node.select('./following-sibling::*[position()<=2]/li').extract()

			yield CocktailItem(
				title=html_to_text(node.extract()),
				picture=picture,
				url=url,
				source='Oh Gosh!',
				ingredients=map(html_to_text, ingredients),
			)

########NEW FILE########
__FILENAME__ = saveur
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br, extract_extra_ingredients

xp_recipe_links = css_to_xpath('.SolrResultTitle a') + '/@href'
xp_next_link = css_to_xpath('.SolrPageNext a') + '/@href'

class SaveurSpider(BaseSpider):
	name = 'saveur'
	start_urls = ['http://www.saveur.com/solrSearchResults.jsp?fq=Course:Beverages']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select(xp_recipe_links).extract():
			yield Request(urljoin(response.url, url), self.parse_recipe)

		for url in hxs.select(xp_next_link).extract():
			yield Request(urljoin(response.url, url), self.parse)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select('//h1').extract():
			break
		else:
			return []

		for picture in hxs.select("//img[@itemprop='photo']/@src").extract():
			picture = urljoin(response.url, picture)
			break
		else:
			picture = None

		ingredients, extra_ingredients = extract_extra_ingredients(
			(
				split_at_br(hxs.select(
					"//node()"
						"[preceding::h4["
							"starts-with(text(),'INGREDIENTS') or "
							"starts-with(text(),'Ingredients') or "
							"starts-with(text(),'ingredients')"
						"]]"
						"[following::h4["
							"starts-with(text(),'INSTRUCTIONS') or "
							"starts-with(text(),'Instructions') or "
							"starts-with(text(),'instructions') or"
							"starts-with(text(),'DIRECTIONS') or "
							"starts-with(text(),'Directions') or "
							"starts-with(text(),'directions')"
						"]]"
				)) or
				hxs.select('//div[count(*)=1]/b').extract() or
				split_at_br(hxs.select('//b//node()')) or
				hxs.select("//span[@style='font-weight: bold;']").extract()
			),
			lambda s: s.isupper()
		)

		if not ingredients:
			return []

		return [CocktailItem(
			title=html_to_text(title).strip(),
			picture=picture,
			url=response.url,
			source='Saveur',
			ingredients=ingredients,
			extra_ingredients=extra_ingredients
		)]

########NEW FILE########
__FILENAME__ = seriouseats
import json
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import extract_extra_ingredients

URL = 'http://www.seriouseats.com/topics/search?index=recipe&count=200&term=c|cocktails'

xp_ingredients = css_to_xpath('.ingredient')

class SeriouseatsSpider(BaseSpider):
	name = 'seriouseats'
	start_urls = [URL]

	def parse(self, response):
		recipes = json.loads(response.body)['entries']

		for recipe in recipes:
			picture = None

			for size in sorted(int(k[10:]) for k in recipe if k.startswith('thumbnail_')):
				picture = recipe['thumbnail_%d' % size]

				if picture:
					if 'strainerprimary' not in picture and 'cocktailChroniclesBug' not in picture:
						break

					picture = None
				
			yield Request(recipe['permalink'], partial(
				self.parse_recipe,
				title=recipe['title'].split(':')[-1].strip(),
				picture=picture
			))

		if recipes:
			yield Request('%s&before=%s' % (URL, recipe['id']), self.parse)

	def parse_recipe(self, response, title, picture):
		hxs = HtmlXPathSelector(response)

		ingredients, extra_ingredients = extract_extra_ingredients(
			hxs.select(xp_ingredients),
			lambda node: node.select('strong')
		)

		yield CocktailItem(
			title=title,
			picture=picture,
			url=response.url,
			source='Serious Eats',
			ingredients=ingredients,
			extra_ingredients=extra_ingredients
		)

########NEW FILE########
__FILENAME__ = wikipedia
from urlparse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_recipes = css_to_xpath('.hrecipe')
xp_ingredients = css_to_xpath('.ingredient li')

class WikipediaSpider(CrawlSpider):
	name = 'wikipedia'
	allowed_domains = ['en.wikipedia.org']
	start_urls = ['http://en.wikipedia.org/wiki/List_of_cocktails']

	rules = (
		Rule(SgmlLinkExtractor(allow=(r'/wiki/Category:Cocktails(\b|_)'))),
		Rule(SgmlLinkExtractor(allow=(r'/wiki/Category:.+(\b|_)drinks?(\b|_)'))),
		Rule(SgmlLinkExtractor(allow=(r'/wiki/[^:]+$')), callback='parse_recipes'),
	)

	def parse_recipes(self, response):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select("//link[@rel='canonical']/@href").extract():
			url = urljoin(response.url, url)

			if url != response.url:
				yield Request(url, callback=self.parse_recipes)
				raise StopIteration

		for recipe in hxs.select(xp_recipes):
			for title in recipe.select('caption').extract():
				break
			else:
				continue

			ingredients = recipe.select(xp_ingredients).extract()
			if not ingredients:
				continue

			for picture in recipe.select("tr/td[@colspan='2']//img/@src | preceding-sibling::*[contains(concat(' ', normalize-space(@class), ' '), ' thumb ')]//img/@src").extract():
				picture = urljoin(response.url, picture)
				break
			else:
				picture = None

			yield CocktailItem(
				title=html_to_text(title),
				picture=picture,
				url=response.url,
				source='Wikipedia',
				ingredients=map(html_to_text, ingredients)
			)

########NEW FILE########
__FILENAME__ = utils
import re
from HTMLParser import HTMLParser
from collections import OrderedDict

from scrapy.selector import XPathSelector

unescape = HTMLParser().unescape

def html_to_text(s):
	# strip tags
	s = re.sub(r'<\W*(?:b|big|i|small|tt|abbr|acronym|cite|code|dfn|em|kbd|strong|samp|var|a|bdo|q|span|sub|sup)\b[^>]*?>', '', s, flags=re.I)
	s = re.sub(r'<[^>]*?>', ' ', s)
	# replace entities
	s = unescape(s)
	# strip leading and trailing spaces
	s = s.strip()
	# replace all sequences of subsequent whitespaces with a single space
	s = re.sub(r'\s+', ' ', s)
	return s

def split_at_br(hxs, include_blank=False, newline_elements=['br']):
	nodes = hxs.select('|'.join('descendant-or-self::' + el for el in newline_elements + ['text()']))
	snippets = []
	rv = []

	while True:
		node = nodes.pop(0) if nodes else None

		if node and node.xmlNode.name not in newline_elements:
			snippets.append(node.extract())
			continue

		s = ''.join(snippets).strip()
		snippets = []

		if s or include_blank:
			rv.append(s)

		if not node:
			return rv

def extract_extra_ingredients(nodes, is_section_header):
	section = None
	sections = OrderedDict()

	for node in nodes:
		text = node.extract() if isinstance(node, XPathSelector) else node
		text = html_to_text(text).strip()

		if not text:
			continue

		if is_section_header(node):
			section = text
			continue

		sections.setdefault(section, []).append(text)

	if None in sections:
		ingredients = sections.pop(None)
	elif sections:
		ingredients = sections.pop(sections.keys()[-1])
	else:
		ingredients = []

	extra_ingredients = [x for y in sections.values() for x in y]

	return (ingredients, extra_ingredients)

########NEW FILE########
__FILENAME__ = xmlpipe
#!/usr/bin/env python

import sys
import os
import json
import re
from unicodedata import normalize
from itertools import imap, groupby
from difflib import SequenceMatcher

from werkzeug.utils import escape

try:
	# https://pypi.python.org/pypi/snowballstemmer
	from snowballstemmer import stemmer
except ImportError:
	# http://snowball.tartarus.org/wrappers/guide.html
	from Stemmer import Stemmer as stemmer

ee = lambda s: escape(s).encode('utf-8')
stemmer_en = stemmer('english')

def normalize_title(s):
	s = re.sub(r'[^\w\s]', '', normalize('NFKD', s)).lower()
	s = ' '.join(stemmer_en.stemWords(s.split()))
	s = re.match('(?:the )?(?:dri )?(?:rye (?=sazerac))?(.*?)(?: cocktail)?(?: for a crowd)?(?: dri)?(?: the)?$', s).group(1)
	s = s.replace(' ', '')

	return s

def drop_duplicates(items):
	key = lambda item: normalize_title(item['title'])
	items = sorted(items, key=key)

	for title, items in groupby(items, key):
		yield max(items, key=lambda item: SequenceMatcher(None, title, item['url'].lower()).ratio())

def load_synonyms():
	synonyms = {}

	with open(os.path.join(os.path.dirname(__file__), 'synonyms.txt')) as f:
		for line in f:
			a, b = line.decode('utf-8').split('>')

			a = a.strip().lower()
			b = b.strip()

			synonyms.setdefault(a, []).append(b)

	return synonyms

def compile_synonyms():
	synonyms = load_synonyms()
	regex = re.compile(r'\b(?:%s)\b' % '|'.join(imap(re.escape, synonyms)), re.I)

	def expand(s):
		yield s

		for x in synonyms.get(s.lower(), []):
			for y in expand(x):
				yield y

	return (lambda s: regex.sub(lambda m : ' '.join(expand(m.group(0))), s))

expand_synonyms = compile_synonyms()

def xmlpipe():
	print '<?xml version="1.0" encoding="utf-8"?>'
	print '<sphinx:docset>'

	print '<sphinx:schema>'
	print '<sphinx:field name="title" attr="string"/>'
	print '<sphinx:field name="title_normalized" attr="string"/>'
	print '<sphinx:field name="ingredients"/>'
	print '<sphinx:attr name="url" type="string"/>'
	print '<sphinx:attr name="source" type="string"/>'
	print '<sphinx:attr name="picture" type="string"/>'
	print '<sphinx:attr name="ingredients_text" type="string"/>'
	print '</sphinx:schema>'

	unique = False
	i = 1

	for arg in sys.argv[1:]:
		if arg == '-i':
			unique = False
			continue

		if arg == '-u':
			unique = True
			continue

		with open(arg) as file:
			items = imap(json.loads, file)

			if unique:
				items = drop_duplicates(items)

			for item in items:
				print '<sphinx:document id="%d">' % i
				print '<title>%s</title>' % ee(item['title'])
				print '<url>%s</url>' % ee(item['url'])
				print '<source>%s</source>' % ee(item['source'])

				if item['picture']:
					print '<picture>%s</picture>' % ee(item['picture'])

				print '<title_normalized>%s</title_normalized>' % ee(
					normalize_title(item['title'])
				)

				print '<ingredients>%s</ingredients>' % ee('!'.join(
					re.sub(r'[.!?\s]+', ' ', expand_synonyms(x))
						for y in (item['ingredients'], item.get('extra_ingredients', []))
						for x in y
				))

				print '<ingredients_text>%s</ingredients_text>' % ee('\n'.join(
					item['ingredients']
				))

				print '</sphinx:document>'

				i += 1

	print '</sphinx:docset>'

xmlpipe()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python

import os
import re
import json
import posixpath
import mimetypes
import subprocess
from urllib import urlencode
import sphinxapi

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.routing import Map, Rule
from werkzeug.urls import url_decode
from werkzeug.utils import escape

try:
	import settings
except ImportError:
	settings = None

MAX_COCKTAILS_PER_PAGE = 20
MAX_RECIPES_PER_COCKTAIL = 10

SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000/')
SPHINX_HOST = getattr(settings, 'SPHINX_HOST', 'localhost')
SPHINX_PORT = getattr(settings, 'SPHINX_PORT', 9312)
LESSC_OPTIONS = getattr(settings, 'LESSC_OPTIONS', [])

STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), 'static')
INDEX_FILE = os.path.join(os.path.dirname(__file__), os.path.pardir, 'sphinx', 'idx_recipes.spd')

OPENSEARCH_TEMPLATE = '''\
<?xml version="1.0"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>Cocktail Search</ShortName>
    <Url type="text/html" template="%(site_url)s#{searchTerms}"/>
</OpenSearchDescription>
'''

JSLICENSE_TEMPLATE = '''\
<!DOCTYPE html>
<html>
<head>
<title>Cocktail search | JavaScript License Information</title>
</head>
<body>
<table id="jslicense-labels1">
<tr>
<td><a href="http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js">jquery.min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jquery/jquery/archive/1.9.1.zip">jquery-1.9.1.zip</a></td>
</tr>
<tr>
<td><a href="http://cdnjs.cloudflare.com/ajax/libs/underscore.js/1.4.4/underscore-min.js">underscore-min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jashkenas/underscore/archive/1.4.4.zip">underscore-1.4.4.zip</a></td>
</tr>
<tr>
<td><a href="http://cdnjs.cloudflare.com/ajax/libs/backbone.js/1.0.0/backbone-min.js">backbone-min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jashkenas/backbone/archive/1.0.0.zip">backbone-1.0.0.zip</a></td>
</tr>
<tr>
<td><a href="%(site_url)sstatic/script.js">script.js</a></td>
<td><a href="http://www.gnu.org/licenses/agpl-3.0.html">GNU-AGPL-3.0</a></td>
<td><a href="%(site_url)sstatic/script.js">script.js</a></td>
</tr>
</table>
</body>
</html>
'''

class CocktailsApp(object):
	urls = Map([
		Rule('/recipes', endpoint='recipes'),
	])

	generated_files = {
		'all.css': 'css',
		'opensearch.xml': 'open_search_description',
		'jslicense.html': 'jslicense',
	}

	def make_query(self, sphinx, ingredients):
		queries = []

		for ingredient in ingredients:
			m = re.match(r'(\w+)\s*:\s*(\S.*)', ingredient)
			if m:
				field, ingredient = m.groups()
			else:
				field = 'ingredients'

			words = []
			for quoted, unquoted in re.findall(r'"(.*?)(?:"|$)|([^"]+)', ingredient):
				if quoted:
					words.extend(quoted)
				if unquoted:
					keywords = sphinx.BuildKeywords(unquoted.encode('utf-8'), 'recipes', 0)
					if keywords is None:
						return None
					for kw in keywords:
						words.append(kw['tokenized'])

			queries.append('@%s (%s)' % (
				field,
				' SENTENCE '.join(
					'"%s"' % sphinx.EscapeString(word) for word in words
				)
			))

		return ' | '.join(queries)

	def query(self, sphinx, ingredients, offset):
		query = self.make_query(sphinx, ingredients)
		if query is None:
			return None

		sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
		sphinx.SetRankingMode(sphinxapi.SPH_RANK_MATCHANY)
		sphinx.SetLimits(offset, MAX_COCKTAILS_PER_PAGE)
		sphinx.SetGroupBy('title_normalized', sphinxapi.SPH_GROUPBY_ATTR, '@relevance DESC, @count DESC, @id ASC')

		result = sphinx.Query(query)
		if not result:
			return None

		sphinx.SetLimits(0, MAX_RECIPES_PER_COCKTAIL)
		sphinx.ResetGroupBy()

		matches = result['matches']
		cocktails = []

		if matches:
			for match in matches:
				sphinx.AddQuery('(%s) & @title_normalized "^%s$"' % (
					query, sphinx.EscapeString(match['attrs']['title_normalized'])
				))

			results = sphinx.RunQueries()
			if not results:
				return None

			for result in results:
				if result['status'] == sphinxapi.SEARCHD_ERROR:
					return None

				cocktails.append(result['matches'])

		return cocktails

	def view_recipes(self, request):
		index_updated = int(os.stat(INDEX_FILE).st_mtime)
		if request.args.get('index_updated') != str(index_updated):
			return Response(status=302, headers={
				'Location': '/recipes?' + urlencode(
					[('index_updated', index_updated)] +
					[(k, v) for k, v
						in url_decode(request.query_string, cls=iter)
						if k != 'index_updated'
					],
					doseq=True
				),
			})

		ingredients = [s for s in request.args.getlist('ingredient') if s.strip()]
		cocktails = []
		if ingredients:
			try:
				offset = int(request.args['offset'])
			except (ValueError, KeyError):
				offset = 0

			sphinx = sphinxapi.SphinxClient()
			sphinx.SetServer(SPHINX_HOST, SPHINX_PORT)
			sphinx.Open()
			try:
				result = self.query(sphinx, ingredients, offset)
			finally:
				sphinx.Close()

			if result is None:
				raise InternalServerError(sphinx.GetLastError())

			for group in result:
				recipes = []
				for match in group:
					recipes.append({
						'title':       match['attrs']['title'],
						'ingredients': match['attrs']['ingredients_text'].splitlines(),
						'url':         match['attrs']['url'],
						'picture_url': match['attrs']['picture'],
						'source':      match['attrs']['source'],
					})
				cocktails.append({'recipes': recipes})

		return Response(
			json.dumps({
				'cocktails': cocktails,
				'index_updated': index_updated,
			}),
			headers={'Cache-Control': 'public, max-age=31536000'},
			mimetype='application/json'
		)

	def generate_css(self):
		lessc = subprocess.Popen([
			'lessc',
		] + LESSC_OPTIONS + [
			os.path.join(
				os.path.dirname(__file__),
				'less',
				'all.less'
			)
		], stdout=subprocess.PIPE)

		for line in lessc.stdout:
			yield line

		lessc.stdout.close()
		lessc.wait()

	def generate_open_search_description(self):
		return [OPENSEARCH_TEMPLATE % {'site_url': SITE_URL}]

	def generate_jslicense(self):
		return [JSLICENSE_TEMPLATE % {'site_url': SITE_URL}]

	def cmd_runserver(self, listen='8000'):
		from werkzeug.serving import run_simple

		def view_index(request):
			path = os.path.join(STATIC_FILES_DIR, 'index.html')
			return Response(open(path, 'rb'), mimetype='text/html')

		self.view_index = view_index
		self.urls.add(Rule('/', endpoint='index'))

		def view_generated(request, path):
			endpoint = self.generated_files.get(path)
			if endpoint is None:
				raise NotFound
			iterable = getattr(self, 'generate_' + endpoint)()
			mimetype = mimetypes.guess_type(path)[0]
			return Response(iterable, mimetype=mimetype)

		self.view_generated = view_generated
		self.urls.add(Rule('/static/<path:path>', endpoint='generated'))

		if ':' in listen:
			(address, port) = listen.rsplit(':', 1)
		else:
			(address, port) = ('localhost', listen)

		run_simple(address, int(port), app, use_reloader=True, static_files={
			'/static/': STATIC_FILES_DIR,
		})

	def cmd_deploy(self):
		for path, endpoint in self.generated_files.iteritems():
			print 'Generating ' + path

			iterable = getattr(self, 'generate_' + endpoint)()
			path = os.path.join(STATIC_FILES_DIR, *posixpath.split(path))

			with open(path, 'wb') as outfile:
				for data in iterable:
					outfile.write(data)

	def dispatch_request(self, request):
		adapter = self.urls.bind_to_environ(request.environ)
		try:
			endpoint, values = adapter.match()
			return getattr(self, 'view_' + endpoint)(request, **values)
		except NotFound, e:
			return Response(status=404)
		except HTTPException, e:
			return e

	def call_command(self, command, args):
		getattr(self, 'cmd_' + command)(*args)

	def list_commands(self):
		return [x[4:] for x in dir(self) if x.startswith('cmd_')]

	def __call__(self, environ, start_response):
		return self.dispatch_request(Request(environ))(environ, start_response)

if __name__ == '__main__':
	import argparse

	app = CocktailsApp()

	parser = argparse.ArgumentParser()
	parser.add_argument('command', choices=app.list_commands())
	parser.add_argument('arg', nargs='*')
	args = parser.parse_args()

	app.call_command(args.command, args.arg)

########NEW FILE########
