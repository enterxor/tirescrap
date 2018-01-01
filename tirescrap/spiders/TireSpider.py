# -*- coding: utf-8 -*-
import scrapy

from scrapy.spiders import Spider

from tirescrap.items import TirescrapItem 
from pathlib import Path 
from csv import DictReader
from urllib.parse import urlparse, parse_qs
from scrapy.utils.response import open_in_browser

class TirespiderSpider(scrapy.Spider): 
	name = "TireSpider" 
	tsv_file = None
	def __init__(self, input_tsv="", *args, **kwargs):
		super(TirespiderSpider, self).__init__(*args, **kwargs)
		self.tsv_file = Path(input_tsv)

	def start_requests(self):
		if self.tsv_file.is_file():
			with open(self.tsv_file.resolve()) as rows:
				for cookie_jar,row in enumerate(DictReader(rows, dialect='excel-tab')):
					link = row["Product URL"]
					self.logger.info("Creating reequest %s",link)
					yield scrapy.Request(url = link, callback = self.parse, method = "GET", dont_filter=True,
						meta={'mpc':row["MPC"], 'rtcpc':row["RTCPC"], 'brand':row["Brand"],
						'product_url':row["Product URL"],"zipcode":row["Zipcode"],'cookiejar':cookie_jar})
		else:
			self.logger.info("Input file not found:%s",self.tsv_file)
  

	def parse(self, response): 
		qty = response.selector.xpath('//*[@class="qty left"]/.//*[@selected]/text()').extract()
		if qty:
			#list price was found on the page. Continue parsing and making request for get the shipping cost
			in_cart="No"
			listprice = response.selector.xpath('//*[@itemprop="price"]/text()').extract()

			if listprice:
				listprice=listprice[0]
			else:
				listprice="0";
				in_cart="Yes"
			rawprice = response.selector.xpath('//*[@class="dPriceStrike"]/span[2]/text()').extract()
			if rawprice:
				rawprice = rawprice[0]
			else:
				rawprice = "0"
			print("qty %s, listprice %s, rawprice %s",qty,listprice,rawprice)
			self.logger.info("got response for URL ")
			if in_cart=="Yes":
				self.logger.info("Making request AddItem from tireForm0")
				return scrapy.FormRequest.from_response(
						response,
						url="https://www.tirerack.com/cart/AddItemServlet",
						formname = "tireForm0",
						formdata={'shipZip':response.meta['zipcode']},
						dont_click=True,
						dont_filter=True,
						meta =dict(response.meta,**{"rawprice":rawprice,"listprice":listprice,"qty":qty[0],"only_cart":in_cart}),
						callback = self.parse_AddItemToCartFromForm
					)

			return scrapy.Request(url='https://www.tirerack.com/rest/v1/cartService/getCartDetails',
				callback=self.parse_cartDetails, 
				method="GET",
				dont_filter=True,
				meta=dict(response.meta,**{"rawprice":rawprice,"listprice":listprice,"qty":qty[0],"only_cart":in_cart}))
		else:
			#we need to add item to cart first
			return

	def parse_cartDetails(self, response):
		o = urlparse(response.meta['product_url'])
		query = parse_qs(o.query)
		nexturl = 'https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&shipquote=Y&common=true&Make='+query['tireMake'][0]+'&Model='+query['tireModel'][0]+'&Type=T&i1_PartNumber='+query['partnum'][0]+'&i1_Price='+response.meta['listprice']+'&AddToUser=true&i1_Qty='+response.meta['qty'][0]
		self.logger.info("got response for CartDetails. Executing %s",nexturl)
		return scrapy.Request(
				url=nexturl,
				callback=self.parse_addItemServlet,
				method="GET",
				dont_filter=True,
				meta=response.meta
			)

	def parse_addItemServlet(self, response):
		nexturl = 'https://www.tirerack.com/shippingquote/SetZip.jsp?zip='+response.meta["zipcode"]
		self.logger.info("got response for CartDetails. Executing %s",nexturl)
		return scrapy.Request(
				url=nexturl,
				callback=self.parse_setZip,
				method="GET",
				dont_filter=True,
				meta=response.meta
			)

	def parse_setZip(self, response):
		self.logger.info("SetZip completed.")
		item = TirescrapItem() 
		item["mpc"] = response.meta["mpc"] 
		item["rtcpc"] = response.meta["rtcpc"] 
		item["brand"] = response.meta["brand"] 
		item["product_url"] = response.meta["product_url"] 
		item["zipcode"] = response.meta["zipcode"] 	
		item["rawprice"] = response.meta["rawprice"] 
		item["listprice"] = response.meta["listprice"]
		item["qty"] = response.meta["qty"] 
		item["addtocart"] = response.meta["only_cart"]
		item["shipping"] = response.selector.xpath('//*[@class="SQcol4"]/text()').extract_first()
		return item


	def parse_AddItemToCartFromForm(self, response):
		self.logger.info("Item added to cart")
		nexturl = 'https://www.tirerack.com/shippingquote/SetZip.jsp?zip='+response.meta["zipcode"]+"&goodyearMap=y"
		print(float(response.selector.xpath('//*[@class="cell total"]/text()').extract()[2]))
		return scrapy.FormRequest.from_response(
						response,
						url="https://www.tirerack.com/cart/FreightCheckServlet",
						formname = "freightCheck",
						formdata={'zip':response.meta['zipcode']},
						dont_click=True,
						dont_filter=True,
						meta =dict(response.meta,**{"listprice":float(response.selector.xpath('//*[@class="cell total"]/text()').extract()[2]),
							"discount":float(response.selector.xpath("//*[@name='discountTotal']/@value").extract_first()) }),
						callback = self.parse_GetFreight
					)


	def parse_GetFreight(self, response):
		#open_in_browser(response)
		self.logger.info("Shipping info recieved")
		item = TirescrapItem() 
		item["mpc"] = response.meta["mpc"] 
		item["rtcpc"] = response.meta["rtcpc"] 
		item["brand"] = response.meta["brand"] 
		item["product_url"] = response.meta["product_url"] 
		item["zipcode"] = response.meta["zipcode"] 	
		item["rawprice"] = response.meta["rawprice"] 
		item["listprice"] = response.meta["listprice"] /float(response.meta["qty"])
		item["qty"] = response.meta["qty"] 
		item["shipping"] =  response.selector.xpath('//*/freight/text()').extract_first()
		item["addtocart"] = response.meta["only_cart"] 
		item["discount"] = response.meta["discount"] 
		return item
