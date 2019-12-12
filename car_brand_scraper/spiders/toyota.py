import scrapy
import json
from selenium import webdriver
import pandas
import pdb


class ToyotaSpider(scrapy.Spider):
    """ Spider for scraping Toyota cars. """


    name = "toyota"


    def init_data(self):
        """ Initiates global settings. """

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
            "P PLATE APPROVED": "P PLATE STATUS"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.toyota.com.au/used-cars/for-sale"
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
            #base_url = "http://approvedused.renault.com.au/search/all/all?s={}".format(str(current_pagination))
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

        car_ids = response.css(".vehicle-item::attr(id)").extract()
        car_ids = [item_id.split("listing")[1] for item_id in car_ids]
        cars_urls = ["/".join(["https://www.toyota.com.au/used-cars/for-sale", item_id]) for item_id in car_ids]
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "https://www.toyota.com.au/used-cars/for-sale/449014"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".vehicle-name")[0].css("strong::text").extract_first()
        year = title.split(" ")[0]
        initial_details = {
            "LINK": link, "MAKE": self.make, "YEAR": year}
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
