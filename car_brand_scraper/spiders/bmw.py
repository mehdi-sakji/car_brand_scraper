import scrapy
import json
from selenium import webdriver
from datetime import datetime
import pandas
import re
import pdb
import pymongo
from env import MONGODB_CONNECTION, MONGODB_COLLECTION
from bson import json_util
import json


class BmwSpider(scrapy.Spider):
    """ Spider for scraping BMW website. """


    name = "bmw"


    def init_data(self):
        """ TODO """

        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)
        self.db = self.mongo_client.cardealer709
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "BMW"
        self.details_mapping = {
            "CLASS": "SERIES", "COLOUR": "EXTERIOR COLOUR", "REG": "REGO", 
            "REG EXPIRY": "REGO EXPIRY"}

    """
    def start_requests(self):

        base_url = "https://usedcars.bmw.com.au/listing"
        self.init_data()
    
        driver = webdriver.PhantomJS()
        driver.get(base_url) 
        self.extract_max_pagination(driver)
        driver.close()
        
        self.max_pagination = 1
        for current_pagination in range(self.max_pagination):
            base_url = "https://usedcars.bmw.com.au/listing?page={}".format(
                str(current_pagination))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)
    """

    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

    
        base_url = "https://usedcars.bmw.com.au/listing"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)


    def parse_all_pages_urls(self, response):
        """ Extracts URLs of all pages. """
        
        cars_found_text = response.css(".cars-found::text").extract_first()
        num_results_regex = re.compile(r'\d+')
        num_results = int(num_results_regex.search(cars_found_text).group())
        num_pages = int(num_results/12) + 1
        for current_pagination in range(num_pages):
            base_url = "https://usedcars.bmw.com.au/listing?page={}".format(str(current_pagination+1))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        cars_blocks = response.css(".car-details")
        cars_urls = [
            car_block.css("a::attr(href)").extract_first() for car_block in cars_blocks]
        for url in cars_urls:
            yield scrapy.Request(url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".head-2::text").extract_first()
        price = response.css(".overall-price")[0].css("span::text").extract_first()
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())),
            "TITLE": title, "LINK": link, "MAKE": self.make, "PRICE": price}
        dealer_name = response.css(".dealer-details")[0].xpath("./p/b/text()").extract_first()
        if dealer_name is not None:
            initial_details["DEALER NAME"] = dealer_name
        location =  response.css(".dealer-details")[0].xpath("./p/text()").extract()
        if len(location)>=2:
            initial_details["LOCATION"] = "".join(location[0:2])
        comments_text = response.css(".dealer-comments *::text").extract()
        if len(comments_text)>=1:
            initial_details["COMMENTS"] = " ".join(comments_text)
        feature_types = response.css(".standard-features")
        features = []
        for feature_type in feature_types:
            features += feature_type.css("li *::text").extract()
        initial_details["VEHICLE FEATURES"] = ",".join(features)
        details = response.css(".vehicle-details")[0].css("li")
        parsed_details_df = self.parse_details(details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        parsed_details = json.loads(json_util.dumps(parsed_details))
        parsed_details["_id"] = parsed_details["LINK"]
        query = {"_id": parsed_details["_id"]}
        self.collection.update(query, parsed_details, upsert=True)
        yield parsed_details
    

    def parse_details(self, details, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            parsed_details[detail.css("b::text").extract_first()] = detail.css("span::text").extract_first()
        parsed_details_df = pandas.DataFrame.from_dict(parsed_details, orient="index", columns=["value"])
        parsed_details_df["key"] = parsed_details_df.index
        parsed_details_df.reset_index(inplace=True, drop=True)
        return parsed_details_df


    def alter_details(self, parsed_details_df):
        """ Alters details to match mapping format. """

        parsed_details_df = parsed_details_df[~pandas.isnull(parsed_details_df.key)]
        parsed_details_df["key"] = parsed_details_df["key"].apply(lambda key: key.replace(":", "").strip().upper())
        parsed_details_df["key"] = parsed_details_df["key"].apply(
            lambda key: self.details_mapping[key] if key in self.details_mapping.keys() else key)
        return parsed_details_df
