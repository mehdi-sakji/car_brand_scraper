from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
import pandas
import csv
from datetime import datetime
import json
from selenium.webdriver.firefox.options import Options
import pdb


class SlatteryScraper():

    def __init__(self):

        self.details_mapping = {
            "COLOUR": "EXTERIOR COLOUR",
            "VARIANT": "BADGE",
            "KMS SHOWING": "ODOMETER",
            "MOTOR TYPE": "ENGINE",
            "GEARBOX MAKE/MODEL": "TRANSMISSION",
            "STEERING TYPE": "STEERING",
            "ENGINE": "ENGINE NUMBER",
            "MOTOR TYPE": "ENGINE"}
        self.base_url = "https://www.slatteryauctions.com.au/search/cars-commercial-vehicles-motorcycles?gclid=Cj0KCQjwl8XtBRDAARIsAKfwtxBX33_4QMER8CNoUeURBhw1Q4IStUCf7ORD8CnKeSoWvAW2wa5U3ToaApoqEALw_wcB"
        options = Options()
        options.add_argument('--headless')
        executable_path = "/home/saronida/lib/geckodriver"
        self.driver = webdriver.Firefox(executable_path=executable_path, options=options)
        

    def get_cars_urls(self):
        """ TODO """

        self.driver.get(self.base_url)
        time.sleep(10)
        item_cards = self.driver.find_elements_by_class_name("item-card__inner")
        cars_urls = [item_card.find_element_by_tag_name("a").get_attribute("href") for item_card in item_cards]
        return cars_urls


    def parse_details(self, description_details, details, asset_conditions, extra, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in description_details:
            key = detail.split(":")[0]
            value = detail.split(":")[1]
            if value != "":
                parsed_details[key] = value
        for detail in details:
            parsed_details[detail.find_element_by_tag_name("th").text] = detail.find_element_by_tag_name("td").text
        for detail in asset_conditions:
            parsed_details[detail.find_element_by_tag_name("th").text] = detail.find_element_by_tag_name("td").text
        features_list = []
        for feature in extra:
            if "text-success" in feature.find_element_by_tag_name("td").find_element_by_tag_name("i").get_attribute("class"):
                features_list.append(feature.find_element_by_tag_name("th").text)
        parsed_details["VEHICLE FEATURES"] = ",".join(features_list)
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


    def scrape_all_cars(self, cars_urls):
        """ TODO """

        all_cars = []
        for i, example_url in enumerate(cars_urls):
            print("Scraping %d out of %d ...", (i, len(cars_urls)))
            all_cars.append(self.scrape_car(example_url))
        return all_cars


    def scrape_car(self, example_url):
        """ TODO """

        self.driver.get(example_url)
        link = example_url
        title = self.driver.find_elements_by_class_name("product-details__title")[1].text
        initial_details = {
            "TITLE": title, "LINK": link, "TIMESTAMP": int(datetime.timestamp(datetime.now()))}
        initial_details["DEALER NAME"] = "Slattery Auctions"
        location = self.driver.find_element_by_class_name("snapshot__details").find_elements_by_tag_name("li")[2].text
        initial_details["LOCATION"] = location
        product_details_comments_features = self.driver.find_element_by_id("product-details")
        description = product_details_comments_features.find_elements_by_class_name("table-product-details")[0]
        description_items = description.text.split("\n")
        description_details = [item for item in description_items if ":" in item and len(item.split(":"))==2]
        details_block = product_details_comments_features.find_elements_by_class_name("table-product-details")[1]
        details = details_block.find_elements_by_tag_name("tr")
        asset_conditions_block = product_details_comments_features.find_elements_by_class_name("table-product-details")[2]
        asset_conditions = asset_conditions_block.find_elements_by_tag_name("tr")
        extra_block = product_details_comments_features.find_elements_by_class_name("table-product-details")[3]
        extra = extra_block.find_elements_by_tag_name("tr")
        parsed_details_df = self.parse_details(description_details, details, asset_conditions, extra, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        return parsed_details


    def save_cars(self, all_cars):
        """ TODO """

        with open('../../results/slattery.json', 'w') as json_file:
            for car_dict in all_cars:
                json.dump(car_dict, json_file) 
                json_file.write("\n")
        return


if __name__=="__main__":

    slattery_scraper = SlatteryScraper()
    cars_urls = slattery_scraper.get_cars_urls()
    all_cars = slattery_scraper.scrape_all_cars(cars_urls)
    slattery_scraper.save_cars(all_cars)
