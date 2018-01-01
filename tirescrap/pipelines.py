# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import csv
class TirescrapPipeline(object):
    def process_item(self, item, spider):
        return item

class TSVWriterPipeline(object):

	def open_spider(self, spider):
		self.file = open('output.tsv', 'w', newline='')
		self.writer = csv.writer(self.file,
								quotechar='\'',dialect='excel-tab')

		self.writer.writerow(["MPC",
			"RTCPC",
			"Brand",
			"Product URL",
			"Zipcode",
			"Quantity",
			"RawPrice",
			"ListPrice",
			"Shipping",
			"Discount",
			"AddtoCart"])

	def close_spider(self, spider):
		self.file.close()

	def process_item(self, item, spider):
		if not "rawprice" in item:
			item["rawprice"] = 0.0
		if not "listprice" in item:
			item["listprice"] = 0.0
		if not "rawprice" in item :
			item["rawprice"] = 0.0
		if not "qty" in item:
			item["qty"] = 0.0
		if not "shipping" in item:
			item["shipping"] = 0.0
		if not "discount" in  item:
			item["discount"] = 0.0
		if not "addtocart" in item:
			item["addtocart"] = "No"

		self.writer.writerow([
			item["mpc"] ,
			item["rtcpc"],
			item["brand"] , 
			item["product_url"],
			item["zipcode"],	
			item["qty"],
			item["rawprice"],
			item["listprice"],
			item["shipping"],
			item["discount"],
			item["addtocart"]
		])
		self.file.flush()
		return item
