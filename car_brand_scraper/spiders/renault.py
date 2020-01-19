import scrapy
import json
from selenium import webdriver
import pandas
from datetime import datetime
import pdb


class RenaultSpider(scrapy.Spider):
    """ Spider for scraping Renault cars. """


    name = "renault"


    def init_data(self):
        """ Initiates global settings. """

        self.make = "Renault"
        self.models = [
            "CAPTUR", "Captur", "Kadjar", "KOLEOS", "MEGANE", "TRAFIC", "CLIO", "KANGOO"]
        self.details_mapping = {
            "KILOMETRES": "ODOMETER", "BODY": "BODY TYPE", "COLOUR": "EXTERIOR COLOUR",
            "KMS": "ODOMETER", "REGISTRATION": "REGO", "DRIVE": "DRIVE TYPE", "BODY STYLE": "BODY TYPE",
            "SEAT CAPACITY": "SEATS", "REG PLATE": "REGO", "GENERIC GEAR TYPE": "TRANSMISSION",
            "FUEL CONSUMPTION COMBINED": "FUEL ECONOMY (COMBINED)", "ENGINE SIZE (L)": "ENGINE SIZE (CC)"}
        self.models_badges = [
            ("captur", ["dynamique", "intens", "s-edition", "zen"]),
            ("clio", ["dynamique", "intens", "life", "r.s. 200 cup", "r.s. 200 sport", "zen"]),
            ("kadjar", ["dynamique", "intens"]), 
            ("kangoo", ["maxi", "maxi z.e"]),
            ("koleos", ["bose", "formula edition", "intens", "life", "privilege", "zen"]),
            ("master", []),
            ("megane", ["gt", "gt-line", "r.s. 280", "r.s. cup", "zen"]),
            ("trafic", ["103kw", "85kw", "crew lifestyle", "formula edition", "trader life"]),
            ("zoe", ["intens"]),
        ]


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """
    
        base_url = "http://approvedused.renault.com.au/search/all/all"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_pages_urls)


    def parse_all_pages_urls(self, response):
        """ Browse to the base url the scraper starts from. """

        num_results_text = response.css(".results-heading")[0].css("span::text").extract_first()
        num_results = int(num_results_text) 
        num_pages = int(num_results/15) + 1
        for current_pagination in range(num_pages):
            car_range = current_pagination*15
            base_url = "http://approvedused.renault.com.au/search/all/all?s={}".format(str(car_range))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ TODO """

        cars_search = response.css(".results")
        cars_urls = cars_search.css("a::attr(href)").extract()
        cars_urls = ['http://approvedused.renault.com.au' + url for url in cars_urls if url != '#pop-up']
        cars_urls = list(set(cars_urls))
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ TODO """
    
        link = response.meta.get("url")
        title = response.css("h1::text").extract()[1]
        year = title.split(" ")[0]
        car_model, car_badge = self.parse_car_model_badge(title)
        initial_details = {
            "TIMESTAMP": int(datetime.timestamp(datetime.now())), "LINK": link,
            "MAKE": self.make, "MODEL": car_model, "BADGE": car_badge, "YEAR": year}
        header_details = response.css(".feature-list").css("li")
        vehicle_details_and_comments = response.css(".tab-content")[0]
        comments = vehicle_details_and_comments.css("#tab1 *::text").extract()
        initial_details["COMMENTS"] = " ".join(comments).strip("\r").strip("\n").strip(" ").strip("\n").strip("\r")
        details = vehicle_details_and_comments.css("#tab2")[0].css("tr")
        parsed_details_df = self.parse_details(header_details, details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        yield parsed_details


    def parse_details(self, header_details, details, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in header_details:
            parsed_details[detail.xpath("./div/div/label/text()").extract_first()] = detail.css(
                ".col-md-7::text").extract_first().strip()
        for detail in details:
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


    def parse_car_model_badge(self, title):
        """ Recognizes car model and badge from its title. """

        car_model = None
        car_badge = None
        for model_badges in self.models_badges:
            if model_badges[0] in title.lower():
                car_model = model_badges[0]
                for badge in model_badges[1]:
                    if badge in title.lower():
                        car_badge = badge
                break
        return car_model, car_badge
