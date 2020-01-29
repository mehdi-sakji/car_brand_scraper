import scrapy
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
import pandas
from datetime import datetime
import re
import pymongo
from bson import json_util
import json
from scrapy.utils.project import get_project_settings


class SubaruSpider(scrapy.Spider):
    """ Spider for scraping Subaru cars. """


    name = "subaru"


    def init_data(self):
        """ Initiates global settings. """

        settings=get_project_settings()
        MONGODB_CONNECTION = settings.get('MONGODB_CONNECTION')
        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)

        self.db = self.mongo_client.cardealer709

        MONGODB_COLLECTION = settings.get('MONGODB_COLLECTION')
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Subaru"
        self.details_mapping = {
            "COLOUR": "EXTERIOR COLOUR",
            "YEAR OF MANUFACTURE": "YEAR",
            "REG": "REGO",
            "INDUCTION": "INDUCTION TYPE",
            "VALVES/PORTS PER CYLINDER": "VALVES PER CYLINDER",
            "DRIVE": "DRIVE TYPE",
            "FUEL CONSUMPTION COMBINED": "FUEL ECONOMY (COMBINED)",
            "FUEL CONSUMPTION EXTRA URBAN": "FUEL ECONOMY (HIGHWAY)",
            "FUEL CONSUMPTION URBAN": "FUEL ECONOMY (CITY)",
            "CO2 EMISSION COMBINED": "CO2 EMISSIONS",
            "CO2 EXTRA URBAN": "CO2 EXTRA URBAN",
            "CO2 URBAN": "CO2 URBAN",
            "RIM MATERIAL": "RIMS",
            "WHEELBASE": "WHEEL BASE",
            "SEAT CAPACITY": "SEATS",
            "BODY STYLE": "BODY TYPE"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.subaru.com.au/used/cars/subaru"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)


    def parse_all_pages_urls(self, response):
        """ Extracts URLs of all pages. """
        
        num_pages = 37
        for current_pagination in range(num_pages):
            print(current_pagination)
            car_range = current_pagination*9
            base_url = "https://www.subaru.com.au/used/cars?query=Make.subaru.&sort=year&limit=9&skip={}".format(
                str(car_range))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        link = response.url
        options = Options()
        options.add_argument('--headless')
        executable_path = "/home/saronida/lib/geckodriver"
        driver = webdriver.Firefox(executable_path=executable_path, options=options)
        driver.get(link)
        cars_blocks = driver.find_elements_by_class_name("csnsl__card")
        cars_urls = [
            car_block.find_element_by_tag_name("a").get_attribute(
                "href") for car_block in cars_blocks]
        driver.close()
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """
        link = response.meta.get("url")
        stock_details = response.css(".stock-details__aside")
        title = stock_details.css(".csnsl__vehicle-heading::text").extract_first()
        price = " ".join(stock_details.css(".csnsl__price *::text").extract()).replace(
            "\r\n", "").strip()
        price = re.sub(r'\s+', ' ', price)
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())),
            "TITLE": title, "LINK": link, "MAKE": self.make, "PRICE": price}
        dealer_info = response.css(".csnsl__dealer")[0].css("dd::text").extract()
        if len(dealer_info)>=2:
            dealer_name = dealer_info[0]
            initial_details["DEALER NAME"] = dealer_name
            dealer_location = dealer_info[1]
            initial_details["LOCATION"] = dealer_location
        comments_block = response.css(".csnsl__toggle-content")[1]
        comments_paragraphs = comments_block.css("p *::text").extract()
        initial_details["COMMENTS"] = " ".join(comments_paragraphs).strip()
        features_block = response.css(".csnsl__toggle-content")[2]
        features_groups = features_block.css(".csnsl__accordion-item")
        features = []
        for group in features_groups:
            features += group.css(".csnsl__listing-text::text").extract()
        if len(features)>=1:
            features = [feature.strip() for feature in features]
            initial_details["VEHICLE FEATURES"] = ",".join(features)
        details = response.css(".csnsl__toggle-content")[0].css("li")
        specs = response.css(".csnsl__toggle-content")[3].css("li")
        parsed_details_df = self.parse_details(details, specs, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        parsed_details = json.loads(json_util.dumps(parsed_details))
        parsed_details["_id"] = parsed_details["LINK"]
        query = {"_id": parsed_details["_id"]}
        self.collection.update(query, parsed_details, upsert=True)
        yield parsed_details


    def parse_details(self, details, specs, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            parsed_details[detail.css("span::text").extract()[0]] = detail.css("span::text").extract()[1]
        for detail in specs:
            parsed_details[detail.css("span::text").extract()[0]] = detail.css("span::text").extract()[1]
        title = parsed_details["TITLE"]
        parsed_details["BADGE"] = title.replace(
            parsed_details["Year of manufacture"], "").replace(parsed_details["MAKE"], "").replace(
                parsed_details["Model"], "").strip()
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
