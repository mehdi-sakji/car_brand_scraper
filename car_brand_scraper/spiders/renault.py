import scrapy
import json
from selenium import webdriver
import pandas
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


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "http://approvedused.renault.com.au/search/all/all"
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
            base_url = "http://approvedused.renault.com.au/search/all/all?s={}".format(str(current_pagination))
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

        cars_search = response.css(".results")
        cars_urls = cars_search.css("a::attr(href)").extract()
        cars_urls = ['http://approvedused.renault.com.au' + url for url in cars_urls if url != '#pop-up']
        cars_urls = list(set(cars_urls))
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "http://approvedused.renault.com.au/details/2019-renault-captur-zen-auto/OAG-AD-17633153"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css("h1::text").extract()[1]
        year = title.split(" ")[0]
        car_model, car_badge = self.parse_car_model_badge(title)
        initial_details = {
            "LINK": link, "MAKE": self.make, "MODEL": car_model, "BADGE": car_badge, "YEAR": year}
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

        after_make = title.lower().split(self.make.lower())[-1].strip()
        car_model = None
        car_badge = None
        self.models = [item.lower() for item in self.models]
        for model in self.models:
            if model in after_make:
                car_model = model.upper()
                car_badge = after_make.split(model)[-1].upper().strip()
                break
        return car_model, car_badge
