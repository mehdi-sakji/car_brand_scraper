import scrapy
import json
from selenium import webdriver
from datetime import datetime
import pandas
import pymongo
from env import MONGODB_CONNECTION, MONGODB_COLLECTION
from bson import json_util
import json


class NissanSpider(scrapy.Spider):
    """ Spider for scraping Nissan cars. """


    name = "nissan"


    def init_data(self):
        """ Initiates global settings. """

        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)
        self.db = self.mongo_client.cardealer709
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Nissan"
        self.details_mapping = {
            "COLOUR": "EXTERIOR COLOUR",
            "REG": "REGO"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://pre-owned.nissan.com.au/listing"
        self.init_data()
        """
        driver = webdriver.PhantomJS()
        driver.get(base_url) 
        self.extract_max_pagination(driver)
        driver.close()
        print(self.max_pagination)
        """
        self.max_pagination = 1
        for current_pagination in range(self.max_pagination):
            #base_url = "http://approvedused.renault.com.au/search/all/all?s={}".format(str(current_pagination))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def extract_max_pagination(self, driver):
        """ Extracts the number of max paginations. """

        ss_page = driver.find_element_by_class_name("ss-page")
        pagination_text = ss_page.find_element_by_tag_name("option").text
        self.max_pagination = int(pagination_text.split(" ")[-1])
        return 1


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        cars_blocks = response.css(".car-list")
        cars_urls = [
            car_block.css("a::attr(href)").extract_first() for car_block in cars_blocks]
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "https://pre-owned.nissan.com.au/details/2016-nissan-juke/OAG-AD-18177267"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".cl-columns")[0].css("h1::text").extract_first()
        badge = title.split(" ")[-1]
        year = title.split(" ")[0]
        price = response.css(".overall-price")[0].css("span::text").extract_first()
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())),
            "LINK": link, "MAKE": self.make, "YEAR": year, "PRICE": price, "BADGE": badge}
        dealer_info = response.css(".dealer-details").css("p *::text").extract()
        if len(dealer_info)>=3:
            dealer_name = dealer_info[0]
            initial_details["DEALER NAME"] = dealer_name
            dealer_location = " ".join(dealer_info[1:3])
            initial_details["LOCATION"] = dealer_location
        comments_paragraphs = response.css(".dealer-comments *::text").extract()
        initial_details["COMMENTS"] = " ".join(comments_paragraphs).strip()
        features_groups = response.css(".standard-features")
        features = []
        for group in features_groups:
            features += group.css("li::text").extract()
        if len(features)>=1:
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
            parsed_details[detail.css("b::text").extract_first()] = " ".join(detail.css(
                "span *::text").extract())
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
        parsed_details_df.drop_duplicates(subset ="key", inplace = True)
        return parsed_details_df
