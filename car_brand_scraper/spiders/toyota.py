import scrapy
import json
from selenium import webdriver
import pandas
from datetime import datetime
import re
import pymongo
from env import MONGODB_CONNECTION, MONGODB_COLLECTION
from bson import json_util
import json
import pdb


class ToyotaSpider(scrapy.Spider):
    """ Spider for scraping Toyota cars. """


    name = "toyota"


    def init_data(self):
        """ Initiates global settings. """

        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)
        self.db = self.mongo_client.cardealer709
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Toyota"
        self.details_mapping = {
            "GRADE": "BADGE",
            "BODY": "BODY TYPE",
            "REGO NO.": "REGO",
            "ENGINE DESCRIPTION": "ENGINE",
            "INDUCTION": "INDUCTION TYPE",
            "GREENHOUSE RATING": "GREEN HOUSE RATING",
            "FUEL CONSUMPTION URBAN": "FUEL ECONOMY (CITY)",
            "FUEL CONSUMPTION EXTRA URBAN": "FUEL ECONOMY (HIGHWAY)",
            "FUEL CONSUMPTION COMBINED": "FUEL ECONOMY (COMBINED)",
            "BODY STYLE": "BODY TYPE",
            "P PLATE APPROVED": "P PLATE STATUS",
            "STEERING DESCRIPTION": "STEERING"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.toyota.com.au/used-cars/for-sale"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)


    def parse_all_pages_urls(self, response):
        """ Extracts URLs of all pages. """
        
        cars_found_text = response.css("#sticky-search-results-header")[0].css("h4::text").extract_first()
        num_results_regex = re.compile(r'(\d|,)+')
        num_results = int(num_results_regex.search(cars_found_text).group().replace(",", ""))
        num_pages = int(num_results/20) + 1
        for current_pagination in range(num_pages):
            base_url = "https://www.toyota.com.au/used-cars/for-sale?itemsPerPage=20&page={}&startIndex=&make=&model=&badge=&series=&colour=&body=&odometer.Minimum=&odometer.Maximum=&price.Minimum=&price.Maximum=&year.Minimum=&year.Maximum=&keywords=&driveType=&transmission=&fuelType=&engineSize.Minimum=&engineSize.Maximum=&location=&radius=&doors.Minimum=&doors.Maximum=&seats.Minimum=&seats.Maximum=&cylinders.Minimum=&cylinders.Maximum=&agedNewerThanDays=&agedOlderThanDays=&sorting=MostRelevant|True&receiver-email=&sender-name=&sender-email=".format(str(current_pagination+1))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        car_ids = response.css(".vehicle-item::attr(id)").extract()
        car_ids = [item_id.split("listing")[1] for item_id in car_ids]
        cars_urls = ["/".join(["https://www.toyota.com.au/used-cars/for-sale", item_id]) for item_id in car_ids]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".vehicle-name")[0].css("strong::text").extract_first()
        year = title.split(" ")[0]
        initial_details = {
            "LINK": link, "MAKE": self.make, "YEAR": year, "TIMESTAMP": int(datetime.timestamp(datetime.now()))}
        odometer = response.css(".odometer-text::text").extract_first()
        initial_details["ODOMETER"] = odometer
        inline_info = response.css(".list-inline")[0]
        try:
            transmission = inline_info.css("li")[0].css("strong::text").extract_first()
            initial_details["TRANSMISSION"] = transmission
        except:
            pass
        try:
            engine = inline_info.css("li")[1].css("strong::text").extract_first()
            initial_details["ENGINE"] = engine
        except:
            pass
        comment = response.css(".expandable-text *::text").extract_first()
        if comment is not None:
            initial_details["COMMENTS"] = comment.replace("\r\n", "").strip()
        dealer_info = response.css("#seller-location")[0].css(".panel-content")[0]
        dealer_name = dealer_info.css("h4")[0].css("strong::text").extract_first()
        if dealer_name is not None:
            initial_details["DEALER NAME"] = dealer_name
        dealer_location_info = dealer_info.css("span  *::text").extract()
        if len(dealer_location_info)>=2:
            dealer_location = " ".join(dealer_location_info[0:2])
            initial_details["LOCATION"] = dealer_location

        details_features_spec_pane = response.css(".tab-content")[0]

        features_panel = response.css("#features-panel")
        features_groups = features_panel.css(".panel-group")
        features = []
        for group in features_groups:
            features += group.css("li::text").extract()
        if len(features)>=1:
            initial_details["VEHICLE FEATURES"] = ",".join(features)

        specs_panel = details_features_spec_pane.css("#specifications-panel")
        specs_groups = specs_panel.css(".panel-group")
        specs = []
        for group in specs_groups:
            specs += group.css("tr")

        details = details_features_spec_pane.css("#details-panel")[0].css("tr")
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
            if len(detail.css("td::text").extract())==2:
                parsed_details[detail.css("td::text").extract()[0]] = detail.css("td::text").extract()[1]
        for detail in specs:
            if len(detail.css("td::text").extract())==2:
                parsed_details[detail.css("td::text").extract()[0]] = detail.css("td::text").extract()[1]
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
