# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
#MPC	RTCPC	Brand	Product URL	Zipcode
import scrapy
from scrapy.item import Item, Field  


class TirescrapItem(scrapy.Item):
	mpc = scrapy.Field()
	rtcpc = scrapy.Field()
	brand = scrapy.Field()
	product_url = scrapy.Field()
	zipcode = scrapy.Field() 
	rawprice = scrapy.Field() 
	listprice = scrapy.Field() 
	qty = scrapy.Field() 
	shipping = scrapy.Field()
	discount = scrapy.Field()
	addtocart = scrapy.Field()