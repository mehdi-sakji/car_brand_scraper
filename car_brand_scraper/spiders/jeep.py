import scrapy
import json
from selenium import webdriver
import pandas as pd
from datetime import datetime
from selenium.webdriver.firefox.options import Options
import time
import re
import pymongo
from env import MONGODB_CONNECTION, MONGODB_COLLECTION
from bson import json_util
import json


class JeepSpider(scrapy.Spider):
    """ Spider for scraping Jeep cars. """


    name = "jeep"


    def init_data(self):
        """ Initiates global settings. """

        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)
        self.db = self.mongo_client.cardealer709
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Jeep"
        self.details_mapping = {
            "KILOMETRES": "ODOMETER",
            "VEHICLE": "TITLE",
            "COLOUR": "EXTERIOR COLOUR",
            "STOCK NUMBER": "STOCK NO",
            "REGISTRATION EXPIRY": "REGO EXPIRY",
            "ENGINE DESCRIPTION": "ENGINE",
            "ENGINE SIZE": "ENGINE SIZE (CC)",
            "FUEL COMBINED": "FUEL ECONOMY (COMBINED)",
            "INDUCTION DESCRIPTION": "INDUCTION TYPE"}
        

    def start_requests(self):
        """ Browse to the base iframe url the scraper starts from. """
    
        base_url = "https://fca.brand.mattaki.com/jeep"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_cars)


    def parse_all_cars(self, response):
        """ Browse to the base url the scraper starts from. """

        options = Options()
        options.add_argument('--headless')
        executable_path = "/home/saronida/lib/geckodriver"
        driver = webdriver.Firefox(executable_path=executable_path, options=options)
        driver.get(response.url)
        time.sleep(10)
        models_li = driver.find_elements_by_class_name("filter-list__listing")[1].find_elements_by_tag_name("li")
        models = [item.find_element_by_tag_name("button").text for item in models_li]
        self.models = [item.upper() for item in models]
        cars_urls = []
        max_pages = int(driver.find_element_by_class_name("pager__list").find_elements_by_class_name(
            "pager-item")[-2].find_element_by_tag_name("a").text)
        inventories = driver.find_element_by_id("content").find_elements_by_class_name("inventory-listing__item")
        cars_urls += [item.find_element_by_tag_name("a").get_attribute("href") for item in inventories]
        for page in range(max_pages - 1):
            print("scraping cars urls from page {}".format(str(page+1)))
            driver.find_element_by_class_name("pager__list").find_elements_by_class_name(
                "pager-item")[-1].find_element_by_tag_name("a").click()
            time.sleep(2)
            inventories = driver.find_element_by_id("content").find_elements_by_class_name("inventory-listing__item")
            cars_urls += [item.find_element_by_tag_name("a").get_attribute("href") for item in inventories]
        driver.close()
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car)


    def parse_car(self, response):
        """ TODO """

        link = response.url
        price = response.css(".product-price__number")[0].css("span::text").extract_first()
        left_size_info = response.css(".invDtLhs")[0]
        right_size_info = response.css(".invDtRhs")[0]
        dealer_info = right_size_info.css(".invContactBox")[0]
        dealer_name = dealer_info.css("h5::text").extract_first().strip()
        dealer_location_info = dealer_info.css("p")[1].xpath("./text()").extract()
        dealer_location_info = [item.strip() for item in dealer_location_info]
        dealer_location_info = [re.sub(r'(\r|\n|\t)+', " ", item) for item in dealer_location_info]
        dealer_location = " ".join(dealer_location_info)
        initial_details = {
            "LINK": link, "PRICE": price, "DEALER NAME": dealer_name, "MAKE": "JEEP",
            "LOCATION": dealer_location, "TIMESTAMP": int(datetime.timestamp(datetime.now()))}
        try:
            comments = left_size_info.css(".read-more")[0].css("p::text").extract_first().replace("\n", " ")
            initial_details["COMMENTS"] = comments
        except:
            print("Comments not present for {}".format(link))
            pass
        
        specifications_block = right_size_info.css(".specifications-table")[0]
        specifications_fields = specifications_block.css("dt")
        specifications_values = specifications_block.css("dd")
        parsed_details = initial_details
        for i in range(len(specifications_fields)):
            field = " ".join([item.strip() for item in specifications_fields[i].xpath("./text()").extract()]).strip()
            value = " ".join([item.strip() for item in specifications_values[i].xpath("./text()").extract()]).strip()
            value = re.sub(r'(\r|\n|\t)+', "", value)
            parsed_details[field] = value
        details_blocks = left_size_info.css(".specifications-table")
        for detail_block in details_blocks:
            details_fields = detail_block.css("dt")
            details_values = detail_block.css("dd")
            for i in range(len(details_fields)):
                field = " ".join([item.strip() for item in details_fields[i].xpath("./text()").extract()]).strip()
                value = " ".join([item.strip() for item in details_values[i].xpath("./text()").extract()]).strip()
                parsed_details[field] = value
        parsed_details_df = pd.DataFrame.from_dict(parsed_details, orient="index", columns=["value"])
        parsed_details_df["key"] = parsed_details_df.index
        parsed_details_df.reset_index(inplace=True, drop=True)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        for item in self.models:
            if item in parsed_details['TITLE'].upper():
                parsed_details['MODEL'] = item
                break
        parsed_details = json.loads(json_util.dumps(parsed_details))
        parsed_details["_id"] = parsed_details["LINK"]
        query = {"_id": parsed_details["_id"]}
        self.collection.update(query, parsed_details, upsert=True)
        yield parsed_details


    def alter_details(self, parsed_details_df):
        """ Alters details to match mapping format. """

        parsed_details_df = parsed_details_df[~pd.isnull(parsed_details_df.key)]
        parsed_details_df["key"] = parsed_details_df["key"].apply(lambda key: key.replace(":", "").strip().upper())
        parsed_details_df["key"] = parsed_details_df["key"].apply(
            lambda key: self.details_mapping[key] if key in self.details_mapping.keys() else key)
        parsed_details_df.drop_duplicates(subset ="key", inplace = True)
        return parsed_details_df
