import scrapy
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from datetime import datetime
import pandas
import pymongo
from bson import json_util
import re
import time
from scrapy.utils.project import get_project_settings


class NissanSpider(scrapy.Spider):
    """ Spider for scraping Nissan cars. """


    name = "nissan"


    def init_data(self):
        """ Initiates global settings. """

        settings=get_project_settings()
        MONGODB_CONNECTION = settings.get('MONGODB_CONNECTION')
        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)

        self.db = self.mongo_client.cardealer709

        MONGODB_COLLECTION = settings.get('MONGODB_COLLECTION')
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Nissan"
        self.details_mapping = {
            "COLOUR": "EXTERIOR COLOUR",
            "REG": "REGO"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """
    
        base_url = "https://pre-owned.nissan.com.au/listing"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_cars_urls)


    def parse_all_cars_urls(self, response):
        """ Extracts URLs of all pages. """
        
        cars_found_text = response.css(".cars-found::text").extract_first()
        num_results_regex = re.compile(r'\d+')
        num_results = int(num_results_regex.search(cars_found_text).group())
        options = Options()
        options.add_argument('--headless')
        executable_path = "/home/saronida/lib/geckodriver"
        driver = webdriver.Firefox(executable_path=executable_path, options=options)
        driver.get(response.url)
        n_iterations = int((num_results - 30)/30) + 1
        for i in range(n_iterations):
            try:
                print("pagination {}".format(str(i)))
                driver.find_element_by_id("load-more").click()
                time.sleep(10)
            except:
                break
        car_blocks = driver.find_elements_by_class_name("car-list")
        cars_urls = [
            car_block.find_element_by_tag_name("a").get_attribute("href") for car_block in car_blocks]
        driver.close()
        for url in cars_urls:
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
