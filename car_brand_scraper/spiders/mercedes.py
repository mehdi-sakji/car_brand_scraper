import scrapy
import json
from selenium import webdriver
import pandas
from datetime import datetime
import pdb


class MercedesSpider(scrapy.Spider):
    """ Spider for scraping Mercedes cars. """


    name = "mercedes"


    def init_data(self):
        """ Initiates global settings. """

        self.make = "Mercedes"
        self.details_mapping = {
            "CLASS": "SERIES", "YEAR OF MANUFACTURE": "YEAR", "REG": "REGO", 
            "REG EXPIRY": "REGO EXPIRY", "COLOUR": "EXTERIOR COLOUR"
            }


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.pre-owned.mercedes-benz.com.au/listing"
        self.init_data()
        """
        driver = webdriver.PhantomJS()
        driver.get(base_url) 
        self.extract_max_pagination(driver)
        driver.close()
        """
        self.max_pagination = 1
        for current_pagination in range(self.max_pagination):
            base_url = "https://www.pre-owned.mercedes-benz.com.au/listing?page={}".format(str(current_pagination))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)

    
    def extract_max_pagination(self, driver):
        """ Extracts the number of max paginations. """

        pagination_text = driver.find_element_by_class_name("cars-found").text
        self.max_pagination = int(pagination_text.split(" ")[0])/ ...
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
        url = "https://www.pre-owned.mercedes-benz.com.au/details/2013-mercedes-benz-b-180/OAG-AD-18182155"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".flex-grow")[0].css("h1::text").extract_first()
        price = response.css(".overall-price")[0].css("span::text").extract_first()
        fuel_economy = response.css(".feature-consumption *::text").extract_first()
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())),
            "TITLE": title, "LINK": link, "MAKE": self.make, "PRICE": price, "FUEL ECONOMY": fuel_economy}
        dealer_name = response.css(".right-sidebar")[0].xpath("./p/b/text()").extract_first()
        if dealer_name is not None:
            initial_details["DEALER NAME"] = dealer_name
        location =  response.css(".right-sidebar")[0].xpath("./p/text()").extract()
        if len(location)>=2:
            initial_details["LOCATION"] = "".join(location[0:2])
        comments_text = response.css(".dealer-comments *::text").extract()
        if len(comments_text)>=1:
            initial_details["COMMENTS"] = " ".join(comments_text)
        features_type_list = response.css(".standard-features")
        features_list = []
        for feature_type in features_type_list:
            features = feature_type.css("li::text").extract()
            features_list += features
        if len(features_list)>=1:
            initial_details["VEHICLE FEATURES"] = ",".join(features_list)
        details = response.css(".vehicle-details")[0].css("li")
        parsed_details_df = self.parse_details(details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
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
