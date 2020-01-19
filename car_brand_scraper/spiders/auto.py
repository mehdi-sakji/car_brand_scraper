import scrapy
import json
import pandas
import re
from datetime import datetime
import pdb


class AutoSpider(scrapy.Spider):
    """ Spider for scraping Auto Auctions cars. """


    name = "auto"


    def init_data(self):
        """ Initiates global settings. """

        self.details_mapping = {
            "BUILD MONTH/YEAR": "YEAR",
            "VARIANT": "BADGE",
            "ENGINE SIZE": "ENGINE SIZE (CC)",
            "COLOUR": "EXTERIOR COLOUR",
            "ENGINE NO.": "ENGINE NUMBER"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "http://www.auto-auctions.com.au/search_results.aspx?sitekey=AAV&make=All%20Makes&model=All%20Models&keyword=&fromyear%20=From%20Any&toyear=To%20Any&body=All%20Body%20Types"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        car_blocks = response.css("table")[0].css("tbody")[0].css("tr")
        cars_urls = [
            "http://www.auto-auctions.com.au/" + car_block.css("td")[0].css("a::attr(href)").extract_first() for car_block in car_blocks]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        details_box = response.css(".details-box")[0]
        title = details_box.css(".title::text").extract_first()
        year = title.split(" ")[0]
        if "ALFA ROMEO" in title:
            make = " ".join([title.split(" ")[1], title.split(" ")[2]])
            model = title.split(" ")[3]
        else:
            make = title.split(" ")[1]
            model = title.split(" ")[2]
        fuel_type = details_box.css("#lblFuelType::text").extract_first()
        body_type = details_box.css("#lblBody::text").extract_first()
        transmission = details_box.css("#lblTransmission::text").extract_first()
        odometer = details_box.css("#lblOdometer::text").extract_first()
        rego = details_box.css("#lblRego::text").extract_first()
        rego_expiry = details_box.css("#lblRegExpiry::text").extract_first()
        stock_no = details_box.css("#lblMTA::text").extract_first()
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())),
            "TITLE": title, "LINK": link, "MAKE": make, "MODEL": model, "YEAR": year, "FUEL TYPE": fuel_type,
            "BODY TYPE": body_type, "TRANSMISSION": transmission, "ODOMETER": odometer, "REGO": rego,
            "REGO EXPIRY": rego_expiry, "STOCK NO": stock_no, "DEALER NAME": "Auto Auctions Sydney",
            "LOCATION": "682 Woodville Road, Guildford NSW 2161"}
        features_block = response.css("#features")[0]
        features = features_block.css("li::text").extract()
        if len(features)>=1:
            features = [item.strip() for item in features]
            initial_details["VEHICLE FEATURES"] = ",".join(features)
        comments = response.css("#lblComments *::text").extract()
        if len(comments)>=1:
            comments = [item.strip() for item in comments]
            initial_details["COMMENTS"] = " ".join(comments)
        details = response.css(".specifications")[0].css(".item")
        parsed_details_df = self.parse_details(details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        yield parsed_details


    def parse_details(self, details, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            parsed_details[detail.css(".option::text").extract_first()] = detail.xpath("./div/span/text()").extract_first()
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
