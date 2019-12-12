import scrapy
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pandas
import pdb


class HyundaiSpider(scrapy.Spider):
    """ Spider for scraping Hyundai website. """


    name = "hyundai"


    def init_data(self):
        """ Initiates global settings. """

        self.make = "Hyundai"
        self.models = ["Accent"]
        self.details_mapping = {
            "VEHICLE": "TITLE", "BODY COLOUR": "EXTERIOR COLOUR", "STOCKNO": "STOCK NO",
            "ANCAP SAFETY RATING": "ANCAP RATING", "BODY CONFIGURATION": "BODY TYPE",
            "CO² EMISSIONS": "CO2 EMISSIONS"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "http://cars.hyundai.com.au/list.php/used_cars/page_1/"
        self.init_data()
        """
        driver = webdriver.PhantomJS()
        driver.get(base_url) 
        self.extract_max_pagination(driver)
        driver.close()
        """
        self.max_pagination = 1
        for current_pagination in range(self.max_pagination):
            base_url = "http://cars.hyundai.com.au/list.php/used_cars/page_{}/".format(str(current_pagination))
            yield scrapy.Request(
                url = base_url, callback = self.parse_all_cars_within_page)


    def extract_max_pagination(self, driver):
        """ Extracts the number of max paginations as the total number of results divided by the size of a page. """

        pagination_text = driver.find_element_by_class_name("footer-text").text
        self.max_pagination = int(pagination_text.split("/")[-1].split("\n")[0])
        return 1


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        cars_blocks = response.css(".vehicle-item")
        cars_urls = [
            car_block.css("a::attr(href)").extract_first() for car_block in cars_blocks]
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "http://cars.hyundai.com.au/view.php/used_cars/2015_Hyundai_Accent_RB2_Active_Red_4_Speed_Sports_Automatic_Hatchback/20136420/"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".vehicle-header")[0].css("h1::text").extract_first()
        year = title.split(" ")[0]
        car_model, car_badge = self.parse_car_model_badge(title)
        initial_details = {
            "LINK": link, "MAKE": self.make, "MODEL": car_model, "BADGE": car_badge, "YEAR": year}
        car_panels = response.css(".cta-key-values")[0].css("h4 *::text").extract()
        if len(car_panels)>=6:
            engine = " ".join([car_panels[4], car_panels[5]])
            initial_details["ENGINE"] = engine
        comments = response.css("div#dealer_summary_content")[0].css("p *::text").extract()
        if comments is not None and len(comments)>=1:
            initial_details["COMMENTS"] = " ".join(comments)
        dealer_summary_content = response.css("div#dealer_summary_content")[1]
        dealer_name = dealer_summary_content.css("h5::text").extract_first()
        initial_details["DEALER NAME"] = dealer_name
        location = dealer_summary_content.css("p::text").extract_first()
        initial_details["LOCATION"] = location
        driver = webdriver.PhantomJS()
        driver.get(link)
        input_postcode = driver.find_element_by_name("userpostcode")
        input_postcode.send_keys("2148")
        input_postcode.send_keys(Keys.ENTER)
        price = driver.find_element_by_class_name("pricing_container").find_element_by_class_name("price_value").text
        if price is not None:
            initial_details["PRICE"] = price
        driver.close()
        features = response.css("#vehicle-features")[0].css("td::text").extract()
        initial_details["VEHICLE FEATURES"] = ",".join(features)
        details = response.css("#vehicle-details")[0].css("tr")
        parsed_details_df = self.parse_details(details, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        yield parsed_details


    def parse_details(self, details, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            try:
                parsed_details[detail.css("td::text")[0].extract()] = detail.css("td::text")[1].extract()
            except:
                parsed_details[detail.css("td::text").extract_first()] = detail.css("td::attr(title)").extract_first()
            finally:
                pass
        parsed_details_df = pandas.DataFrame.from_dict(parsed_details, orient="index", columns=["value"])
        parsed_details_df["key"] = parsed_details_df.index
        parsed_details_df.reset_index(inplace=True, drop=True)
        return parsed_details_df


    def alter_details(self, parsed_details_df):
        """ Alters details to match mapping format. """

        parsed_details_df["key"] = parsed_details_df["key"].apply(lambda key: key.strip().upper())
        parsed_details_df["key"] = parsed_details_df["key"].apply(
            lambda key: self.details_mapping[key] if key in self.details_mapping.keys() else key)
        return parsed_details_df


    def parse_car_model_badge(self, title):
        """ Recognizes car model from its title. """

        after_make = title.split(self.make)[-1].strip()
        car_model = None
        car_badge = None
        for model in self.models:
            if model in after_make:
                car_model = model
                car_badge = after_make.split(model)[-1].strip()
            break
        return car_model, car_badge
