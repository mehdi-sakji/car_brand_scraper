import scrapy
import json
import pandas
from datetime import datetime
import pdb


class F3MotorSpider(scrapy.Spider):
    """ Spider for scraping F3 Motor cars. """


    name = "f3_motor"


    def init_data(self):
        """ Initiates global settings. """

        self.details_mapping = {
            "VARIANT": "BADGE",
            "BODY STYLE": "BODY TYPE",
            "ENGINE SIZE": "ENGINE SIZE (CC)",
            "COLOUR": "EXTERIOR COLOUR",
            "REGISTRATION NO.": "REGO",
            "REG EXPIRY": "REGO EXPIRY",
            "ENGINE NO.": "ENGINE NUMBER",
            "STOCK NO.": "STOCK NO"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.f3motorauctions.com.au/search_results.aspx?sitekey=F3A&make=All%20Makes&model=All%20Models&keyword=&fromyear%20=From%20Any&toyear=To%20Any&body=All%20Body%20Types"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        car_blocks = response.css(".result-item")
        cars_urls = [
            "https://www.f3motorauctions.com.au/" + car_block.css("a::attr(href)").extract_first() for car_block in car_blocks]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".post-title::text").extract_first()
        initial_details = {
            "TITLE": title, "LINK": link, "TIMESTAMP": int(datetime.timestamp(datetime.now()))}
        initial_details["DEALER NAME"] = "F3 Motor Auctions"
        initial_details["LOCATION"] = "F3 Motor Auctions Pty Ltd Lic. MD 39894 1a Yangan Drive Beresfield NSW 2322"
        features_block = response.css("#vehicle-add-features")[0]
        features = features_block.css("li::text").extract()
        if len(features)>=1:
            features = [item.strip() for item in features]
            initial_details["VEHICLE FEATURES"] = ",".join(features)
        comments = response.css("#lblComments *::text").extract()
        if len(comments)>=1:
            comments = [item.strip() for item in comments]
            initial_details["COMMENTS"] = " ".join(comments)
        details = response.css(".sidebar-widget")[0].css(".list-group-item")
        parsed_details_df = self.parse_details(details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        yield parsed_details


    def parse_details(self, details, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            parsed_details[detail.css("span::text").extract()[0]] = detail.css("span::text").extract()[1]
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
