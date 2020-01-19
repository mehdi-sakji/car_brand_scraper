import scrapy
import json
import pandas
from datetime import datetime
import pdb


class CityMotorSpider(scrapy.Spider):
    """ Spider for scraping City Motor cars. """


    name = "city_motor"


    def init_data(self):
        """ Initiates global settings. """

        self.details_mapping = {
            "ENGINE": "INDUCTION TYPE",
            "BUILD MONTH/YEAR": "YEAR",
            "COMPLIANCE PLATE MONTH/YEAR": "COMPLIANCE DATE",
            "VARIANT": "BADGE",
            "BODY": "BODY TYPE",
            "ENGINE SIZE": "ENGINE",
            "KILOMETRES": "ODOMETER",
            "COLOUR": "EXTERIOR COLOUR",
            "STOCK NUMBER": "STOCK NO"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "https://www.citymotorauction.com.au/as_stock.aspx?sitekey=CTY&make=All%20Makes&model=All%20Models&keyword=&fromyear%20=From%20Any&toyear=To%20Any&body=All%20Body%20Types"
        self.init_data()
        yield scrapy.Request(
            url = base_url, callback = self.parse_all_cars_within_page)


    def parse_all_cars_within_page(self, response):
        """ Extracts all cars URLs within a page. """

        page_content = response.css(".pagecontent")[1]
        car_blocks = page_content.css("tr")
        cars_rel_urls = [
            car_block.css("td")[2].css("a::attr(href)").extract_first() for car_block in car_blocks[1:]]
        cars_urls = ["https://www.citymotorauction.com.au/" + item for item in cars_rel_urls if item is not None]
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        initial_details = {"LINK": link, "TIMESTAMP": int(datetime.timestamp(datetime.now()))}
        initial_details["DEALER NAME"] = "City Motor Auction"
        initial_details["LOCATION"] = "720 Kingsford Smith Drive Eagle Farm QLD, 4009"
        features = response.css("#lblExtras::text").extract_first()
        if features is not None:
            initial_details["VEHICLE FEATURES"] = features
        comments = response.css("#lblComments *::text").extract()
        if len(comments)>=1:
            comments = [item.strip() for item in comments]
            initial_details["COMMENTS"] = "\n".join(comments)
        details = response.css(".pagecontent")[0].css("tr")[1].xpath("./td")[0].css("tr")[2:-2]
        identification = response.css(".pagecontent")[0].css("tr")[1].xpath("./td")[1].css("tr")[1:]
        vehicle_checks_lines = response.css(".pagecontent")[0].xpath("./table")[1].css("tr")[1:]
        parsed_details_df = self.parse_details(details, identification, vehicle_checks_lines, initial_details)
        parsed_details_df = self.alter_details(parsed_details_df)
        tmp_dict = parsed_details_df.to_dict(orient="list")
        parsed_details = dict(zip(tmp_dict["key"], tmp_dict["value"]))
        yield parsed_details


    def parse_details(self, details, identification, vehicle_checks_lines, initial_details):
        """ Parses vehicle's details box. """

        parsed_details = initial_details
        for detail in details:
            parsed_details[detail.css("td::text").extract_first()] = detail.css(
                "td")[1].css("span::text").extract_first()
        for detail in identification:
            parsed_details[detail.css("td::text").extract_first()] = detail.css(
                "td")[1].css("span::text").extract_first()
        for line in vehicle_checks_lines:
            vehicle_checks = line.xpath("./td")
            for i in range(0, len(vehicle_checks) ,2):
                parsed_details[vehicle_checks[i].xpath("./text()").extract_first()] = vehicle_checks[i+1].xpath(
                    "./span/text()").extract_first()
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
