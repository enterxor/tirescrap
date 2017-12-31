# -*- coding: utf-8 -*-
import scrapy

from scrapy.spiders import Spider

from tirescrap.items import TirescrapItem 
from pathlib import Path 
from csv import DictReader
from urllib.parse import urlparse, parse_qs
from scrapy.utils.response import open_in_browser
#MPC	RTCPC	Brand	Product URL	Zipcode
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
			self.logger.info("File not found:%s",self.tsv_file)

   

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
			pass

	def parse_cartDetails(self, response):
		#we got kookies for cart tracking
		#now we need to set ZIP code and fetch shipping cost
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
		#we got kookies for cart tracking
		#now we need to set ZIP code and fetch shipping cost
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
		self.logger.info("SetZip completed. Executing")
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
		#open_in_browser(response)
		self.logger.info(" item added ")
		nexturl = 'https://www.tirerack.com/shippingquote/SetZip.jsp?zip='+response.meta["zipcode"]+"&goodyearMap=y"
		# if response.meta["only_cart"]=="Yes":
		# 	nexturl = nexturl+""
		print(float(response.selector.xpath('//*[@class="cell total"]/text()').extract()[2]))
		return scrapy.FormRequest.from_response(
						response,
						url="https://www.tirerack.com/cart/FreightCheckServlet",
						formname = "freightCheck",
						formdata={'zip':response.meta['zipcode']},
						dont_click=True,
						meta =dict(response.meta,**{"listprice":float(response.selector.xpath('//*[@class="cell total"]/text()').extract()[2]),
							"discount":float(response.selector.xpath("//*[@name='discountTotal']/@value").extract_first()) }),
						callback = self.parse_GetFreight
					)
		# self.logger.info("got response for AddItem. Executing %s",nexturl)
		# return scrapy.Request(
		# 		url=nexturl,
		# 		callback=self.parse_SetZipToCartFromForm,
		# 		method="GET",
		# 		dont_filter=True,
		# 		meta=response.meta
		# 	)
		#pass

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


	# def parse_cart(self,response):
	# 	open_in_browser(response)
	# 	# self.logger.info("Cart: %s",response.body)
	# 	self.logger.info("Cart:")
	# 	item = TirescrapItem() 
	# 	item["mpc"] = response.meta["mpc"] 
	# 	item["rtcpc"] = response.meta["rtcpc"] 
	# 	item["brand"] = response.meta["brand"] 
	# 	item["product_url"] = response.meta["product_url"] 
	# 	item["zipcode"] = response.meta["zipcode"] 	
	# 	item["rawprice"] = response.meta["rawprice"] 
	# 	item["listprice"] = response.meta["listprice"] 
	# 	item["qty"] = response.meta["qty"] 
	# 	item["shipping"] = response.selector.xpath('//*[@class="SQcol4"]/text()').extract()
	# 	item["addtocart"] = response.meta["only_cart"] 
	# 	return item

	# def parse_shipQuote(self,response):
	# 	self.logger.info("shipQuote completed. %s",response)
	# 	self.logger.info("shipQuote completed. %s",response.body)

	# 	item = TirescrapItem() 
	# 	item["mpc"] = response.meta["mpc"] 
	# 	item["rtcpc"] = response.meta["rtcpc"] 
	# 	item["brand"] = response.meta["brand"] 
	# 	item["product_url"] = response.meta["product_url"] 
	# 	item["zipcode"] = response.meta["zipcode"] 	
	# 	item["rawprice"] = response.meta["rawprice"] 
	# 	item["listprice"] = response.meta["listprice"] 
	# 	item["qty"] = response.meta["qty"] 
	# 	item["shipping"] = response.selector.xpath('//*[@class="SQcol4"]/text()').extract()
	# 	return item





#Select price:
#response.xpath('//*[@itemprop="price"]/text()').extract()
#Select qty
#response.xpath('//*[@class="qty left"]/.//*[@selected]/text()').extract()
#Select rawprice
#response.xpath('//*[@class="dPriceStrike"]/span[2]/text()'').extract()

#get session Cookies
#https://www.tirerack.com/rest/v1/cartService/getCartDetails
#set Zip
#https://www.tirerack.com/shippingquote/SetZip.jsp?zip=10044
#get shipping quotes:
#https://www.tirerack.com/shippingquote/shipQuote.jsp?
#Select shipping price
#response.xpath('//*[@class="SQcol4"]/text()'').extract()

#алгоритм такой:
#запрос1 загружаем страницу из URL
#обработка1 парсим цену, скидку и qty, собираем все в meta
#копируем setkookie и meta из ответа в запрос2, делаем запрос2 
#запрос2 - getCartDetails
#обработка2 берем сеткукис и meta из ответа, копируем в запрос3
#Запрос3 - setZip
#Обработка3 - делаем запрос4 к ShipQuote
#Запрос4 - ShipQuote
#Обработка4 - парсим цену доставки, возвращаем заполненный item


#Четверг. Ничего не заработало вчера. Запрос SetZip редиректит на ~SelectWarhouse а тот в свою очередь на cookiesexpired
#Что я намерен предпринять?
#Во первых нужно убедиться что куки работают и просмотреть их перед вызовом SetZip
#Во вторых. Я видел что перед отправкой Зипа, выпалняется большой сложный запрос
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&wtpackage=false&shipZip=&i1_ServDesc=99H&i1_LoadIndex=99&i1_Lbs=1709&i1_Kg=775&i1_ServSpeedRating=H&i1_Mph=130&i1_Kph=210&wishlist=false&shipquote=Y&shipZip=&shipZipFromModal=&ProductPage=%2Ftires%2Ftires.jsp%3FtireMake%3DBridgestone%26tireModel%3DDueler%2BH%252FL%2B422%2BEcopia%26partnum%3D17HR6HL422&i1_prefWarehouseStock=&i1_prefDueDate=&i1_altDate=&i1_limitedStockAmt=0&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&URL=null&Sidewall=Blackwall&SidewallShown=&PerfCat=CSTAS&Sumrating=4&HasSpec=Y&HasWarranty=Y&HasComments=Y&HasTests=Y&HasSurveys=Y&Type=T&i1_PartNumber=17HR6HL422&i1_Clarifier=&i1_Price=140.25&i1_Width=215%2F&i1_Ratio=70&i1_Diameter=16&i1_SortCode=45500&i1_SpeedRating=R&i1_SpeedRank=H&i1_StockMessage=In%20Stock&i1_RestrictedQty=0&i1_MaxQty=8&i1_LargeTire=false&i1_SBDueDate=Fewer%20Than%2007&i1_DEDueDate=Fewer%20Than%2008&i1_GADueDate=&i1_SLDueDate=Fewer%20Than%2009&i1_CTDueDate=&i1_NVDueDate=FEW04%2012%2F29%2F17&i1_CODueDate=Fewer%20Than%2009&i1_MNDueDate=Fewer%20Than%2009&i1_ATDueDate=Fewer%20Than%2006&i1_FreightCost=&i1_LoadRating=&i1_RHPprice=10.92&i1_Prevprice=140.25&i1_DiscountPrice=0&i1_HasMfrRHP=N&i1_Pre=&i1_SpecCode=0&i1_MarkdownPrice=0&i1_MapPrice=0&i1_LTL=N&i1_LRR=Ecopia&i1_LRRURL=%2Ftires%2Ftiretech%2Ftechpage.jsp%3Ftechid%3D181&i1_SSSR=&i1_RunFlat=&i1_Weight=23&i1_EstSrp=0.0&i1_PromoValue=&i1_PromoToUse=&i1_Promo1Addtl=&i1_Promo2Addtl=&i1_Promo3Addtl=&AddToUser=true&WantRHP=Y&i1_Qty=4
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&wtpackage=false&shipZip=&wishlist=false&shipquote=Y&shipZip=&shipZipFromModal=&ProductPage=%2Ftires%2Ftires.jsp%3FtireMake%3DBridgestone%26tireModel%3DDueler%2BH%252FL%2B422%2BEcopia%26partnum%3D17HR6HL422&i1_prefWarehouseStock=&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&URL=null&Sidewall=Blackwall&SidewallShown=&PerfCat=CSTAS&Sumrating=4&HasSpec=Y&HasWarranty=Y&HasComments=Y&HasTests=Y&HasSurveys=Y&Type=T&i1_PartNumber=17HR6HL422&i1_Clarifier=&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&i1_DiscountPrice=0&i1_LRR=Ecopia&i1_LRRURL=%2Ftires%2Ftiretech%2Ftechpage.jsp%3Ftechid%3D181&AddToUser=true&WantRHP=Y&i1_Qty=4
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&wtpackage=false&shipZip=&wishlist=false&shipquote=Y&shipZip=&shipZipFromModal=&i1_prefWarehouseStock=&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&URL=null&Sidewall=Blackwall&SidewallShown=&PerfCat=CSTAS&Sumrating=4&HasSpec=Y&HasWarranty=Y&HasComments=Y&HasTests=Y&HasSurveys=Y&Type=T&i1_PartNumber=17HR6HL422&i1_Clarifier=&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&i1_DiscountPrice=0&i1_LRR=Ecopia&i1_LRRURL=%2Ftires%2Ftiretech%2Ftechpage.jsp%3Ftechid%3D181&AddToUser=true&WantRHP=Y&i1_Qty=4'		
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&shipquote=Y&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&URL=null&Sidewall=Blackwall&SidewallShown=&PerfCat=CSTAS&Sumrating=4&HasSpec=Y&HasWarranty=Y&HasComments=Y&HasTests=Y&HasSurveys=Y&Type=T&i1_PartNumber=17HR6HL422&i1_Clarifier=&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&i1_DiscountPrice=0&i1_LRR=Ecopia&AddToUser=true&WantRHP=Y&i1_Qty=4
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&shipquote=Y&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&URL=null&Sidewall=Blackwall&PerfCat=CSTAS&Type=T&i1_PartNumber=17HR6HL422&i1_Clarifier=&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&i1_DiscountPrice=0&i1_LRR=Ecopia&AddToUser=true&WantRHP=Y&i1_Qty=4
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&shipquote=Y&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&PerfCat=CSTAS&Type=T&i1_PartNumber=17HR6HL422&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&AddToUser=true&WantRHP=Y&i1_Qty=4
#https://www.tirerack.com/cart/AddItemServlet?newDesktop=true&shipquote=Y&common=true&Make=Bridgestone&Model=Dueler%20H%2FL%20422%20Ecopia&Type=T&i1_PartNumber=17HR6HL422&i1_Price=140.25&i1_RHPprice=10.92&i1_Prevprice=140.25&AddToUser=true&i1_Qty=4

#url
#cartInfo
#additem
#setZip
#https://www.tirerack.com/shippingquote/AddToCart.jsp?RHP=Y&=&qty0=4&=&=