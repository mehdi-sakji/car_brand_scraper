import scrapy
import json
from selenium import webdriver
import pandas
import pdb


class AudiSpider(scrapy.Spider):
    """ Spider for scraping Audi cars. """


    name = "audi"


    def init_data(self):
        """ Initiates global settings. """

        self.make = "Audi"
        self.details_mapping = {
            "VEHICLE": "TITLE", "COLOUR": "EXTERIOR COLOUR", "STOCK #": "STOCK NO",
            "BODY": "BODY TYPE", "CO²": "CO2 EMISSIONS", "KMS": "ODOMETER",
            "MODEL YEAR": "YEAR", "FUEL EFFICIENCY": "FUEL ECONOMY", "DRIVE": "DRIVE TYPE",
            "REG PLATE": "REGO", "SEAT CAPACITY": "SEATS", "INDUCTION": "INDUCTION TYPE"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://audisearch.com.au/listing"
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
            base_url = "https://audisearch.com.au/listing?page={}".format(str(current_pagination))
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
        #for url in cars_urls:
        #    yield scrapy.Request(
        #        url = url, callback = self.parse_car, meta={"url": url})
        url = "https://audisearch.com.au/details/497155/2015-audi-s3-sedan"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url}) 


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".cl-heading")[1].css("h1::text").extract_first()
        car_model, car_badge = self.parse_car_model_badge(title)
        price = response.css(".car-price")[0].css(".overall-price")[0].css("span::text").extract_first()
        initial_details = {
            "LINK": link, "MAKE": self.make, "MODEL": car_model, "BADGE": car_badge, "PRICE": price
        }
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
        parsed_details_df["value"] =  parsed_details_df["value"].apply(lambda value: value.strip())
        return parsed_details_df


    def parse_car_model_badge(self, title):
        """ Recognizes car model and badge from its title. """

        title_tokens = title.split(" ")
        car_model = title_tokens[2]
        car_badge = title_tokens[3]
        return car_model, car_badge