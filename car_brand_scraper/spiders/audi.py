import scrapy
import json
from selenium import webdriver
import pandas
from datetime import datetime
import pdb
import pymongo
from bson import json_util
import json
from scrapy.utils.project import get_project_settings


class AudiSpider(scrapy.Spider):
    """ Spider for scraping Audi cars. """


    name = "audi"


    def init_data(self):
        """ Initiates global settings. """

        settings=get_project_settings()
        MONGODB_CONNECTION = settings.get('MONGODB_CONNECTION')
        self.mongo_client = pymongo.MongoClient(MONGODB_CONNECTION)

        self.db = self.mongo_client.cardealer709

        MONGODB_COLLECTION = settings.get('MONGODB_COLLECTION')
        self.collection = self.db[MONGODB_COLLECTION]
        self.make = "Audi"
        self.details_mapping = {
            "VEHICLE": "TITLE", "COLOUR": "EXTERIOR COLOUR", "STOCK #": "STOCK NO",
            "BODY": "BODY TYPE", "CO²": "CO2 EMISSIONS", "KMS": "ODOMETER",
            "MODEL YEAR": "YEAR", "FUEL EFFICIENCY": "FUEL ECONOMY", "DRIVE": "DRIVE TYPE",
            "REG PLATE": "REGO", "SEAT CAPACITY": "SEATS", "INDUCTION": "INDUCTION TYPE"}
        self.models_badges = dict([
            ("A1", []),

            ("A3", ["30 Tfsi", "35 Tfsi S Line Plus", "35 Tfsi", "40 Tfsi S Line Plus", "40 Tfsi", "Ambition", "Attraction",
            "S Line", "Sport Black Edition", "Sport Limited Edition", "Sport"]),

            ("A4", ["35 Tfsi", "40 Tfsi", "45 Tfsi", "Allroad 45 Tfsi", "Allroad", "Ambition", "Black Edition", "S Line", "Sport"]),

            ("A5", ["40 Tfsi Sport", "45 Tfsi Sport", "S Line Plus", "Sport"]),

            ("A6", ["45 Tfsi S Line", "45 Tfsi", "55 Tfsi S Line", "Allroad", "Bi-turbo", "Black Edition", "S Line"]),

            ("A7", ["45 Tfsi", "55 Tfsi", "Bi-turbo", "S Line"]),

            ("A8", ["50 Tdi L", "50 Tdi", "55 Tfsi", "L"]),

            ("Q2", ["35 Tfsi Design", "40 Tfsi Sport", "Design", "Sport"]),

            ("Q3", ["Tdi Sport", "Tdi",  "Tfsi Sport", "Tfsi"]),
            
            ("Q5", ["40 Tdi Design", "40 Tdi Sport", "45 Tfsi Design", "45 Tfsi Sport Black Edition", "45 Tfsi Sport", 
            "50 Tdi Sport Black Edition", "50 Tdi Sport", "Tdi Sport Edition", "Tdi Design", "Tdi Sport",  "Tdi",  "Tfsi Sport",
            "Tfsi"]),
            ("Q7", ["160kw", "45 Tdi", "50 Tdi Black Edition", "50 Tdi", "Tdi"]),
            ("Q8", ["55 Tfsi"]),
            ("R8", ["Aspp First Edition", "Plus"]),
            ("RS3", []),
            ("RS4", []),
            ("RS5", []),
            ("RS6", ["Performance"]),
            ("RS7", ["Performance"]),
            ("S3", ["213kw"]),
            ("S4", []),
            ("S5", []),
            ("SQ5", ["Black Edition", "Tdi"]),
            ("SQ7", ["Tdi Black Edition", "Tdi Special Edition", "Tdi"]),
            ("TT", ["45 Tfsi", "S Line", "Sport"]),
            ("TTS", []),
        ])


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """
    
        base_url = "https://audisearch.com.au/listing"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)
    

    def parse_all_pages_urls(self, response):
        """ Extracts URLs of all pages. """
        
        self.models = response.css("#refine-search")[0].css(".form-group")[2].css(
            ".select-container")[0].css("option::text").extract()[1:]
        ss_page = response.css(".ss-page")[0]
        pagination_text = ss_page.css("option::text").extract_first()
        max_pagination = int(pagination_text.split(" ")[-1])
        for current_pagination in range(max_pagination):
            base_url = "https://audisearch.com.au/listing?page={}".format(str(current_pagination+1))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        cars_blocks = response.css(".car-list")
        cars_urls = [
            car_block.css("a::attr(href)").extract_first() for car_block in cars_blocks]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car)


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.url
        title = response.css(".cl-heading")[1].css("h1::text").extract_first()
        subtitle = response.css(".cl-heading")[1].css(".subtitle::text").extract_first()
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())) , "LINK": link, "MAKE": self.make, "TITLE": title}
        car_model = [item for item in self.models if item in title]
        if len(car_model)>=1:
            initial_details["MODEL"] = car_model[0]
            car_badge = self.parse_car_badge(subtitle, car_model[0])
            if car_badge is not None:
                initial_details["BADGE"] = car_badge
        price = response.css(".car-price")[0].css(".overall-price")[0].css("span::text").extract_first()
        if price is not None:
            initial_details["PRICE"] = price
        vehicle_details_features_and_comments = response.css(".vehicle-details")[0]
        comments = vehicle_details_features_and_comments.xpath("./div")[1].xpath("./div")[0]
        comments_paragraphs = comments.css("p::text").extract()
        if comments_paragraphs is not None and len(comments_paragraphs)>=1:
            initial_details["COMMENTS"] = " ".join(comments_paragraphs)
        dealer_info = response.css(".dealer-info")
        dealer_name = dealer_info.css("h3::text").extract_first()
        if dealer_name is not None:
            initial_details["DEALER NAME"] = dealer_name
        location = dealer_info.css("a *::text").extract()
        if location is not None:
            location = " ".join(location[:2])
            initial_details["LOCATION"] = location
        features_list = vehicle_details_features_and_comments.css(".standard-features")[0].css(
            "li::text").extract()
        if features_list is not None and len(features_list)>=1:
            initial_details["VEHICLE FEATURES"] = ",".join(features_list)
        details = vehicle_details_features_and_comments.xpath("./div")[0].css(".tab-content").css("li")
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
            parsed_details[detail.css("span::text").extract_first()] = detail.xpath(
                "./text()").extract_first()
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
        parsed_details_df["value"] =  parsed_details_df["value"].apply(
            lambda value: value.strip() if isinstance(value, str) else value)
        return parsed_details_df


    def parse_car_badge(self, title, car_model):
        """ Recognizes car badge from its title and according to its title. """

        car_badge = None
        for badge in self.models_badges[car_model]:
            if badge.lower() in title.lower():
                car_badge = badge
                break
        return car_badge