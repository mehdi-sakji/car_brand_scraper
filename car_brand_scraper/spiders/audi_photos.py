"""
import scrapy
import json
from selenium import webdriver
import pandas
import pdb
from car_brand_scraper.items import CarBrandScraperItem
import pdb



class AudiSpider(scrapy.Spider):


    name = "audi_photos"


    def start_requests(self):

        base_url = "https://audisearch.com.au/listing"
        self.make = "Audi"
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)


    def parse_all_pages_urls(self, response):
        
        ss_page = response.css(".ss-page")[0]
        pagination_text = ss_page.css("option::text").extract_first()
        max_pagination = int(pagination_text.split(" ")[-1])
        #for current_pagination in range(max_pagination):
        for current_pagination in range(2):
            base_url = "https://audisearch.com.au/listing?page={}".format(str(current_pagination+1))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):

        cars_blocks = response.css(".car-list")
        cars_urls = [
            car_block.css("a::attr(href)").extract_first() for car_block in cars_blocks]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car)


    def parse_car(self, response):

        #car_item = CarBrandScraperItem()
        #link = response.url
        #make = self.make
        #title = response.css(".cl-heading")[1].css("h1::text").extract_first()
        image_urls = response.css("#car-gallery")[0].css("img::attr(src)").extract()
        image_urls = [item.split("?")[0] for item in image_urls]
        #car_item["image_urls"] = [item.split("?")[0] for item in image_urls]
        #yield car_item
        #yield {"image_urls": [item.split("?")[0] for item in image_urls] }
        #return CarBrandScraperItem(image_urls=image_urls)
        yield {'image_urls': image_urls}
"""