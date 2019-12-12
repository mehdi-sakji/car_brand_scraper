import scrapy
import json
import pandas
import pdb


class CentralAutoSpider(scrapy.Spider):
    """ Spider for scraping Central Auto cars. """


    name = "central_auto"


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

        base_url = "http://www.centralautoauctions.com.au/search_results.aspx?sitekey=CMA&make=All+Makes&model=All+Models"
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

        car_blocks = response.css(".result-item")
        cars_urls = [
            "http://www.centralautoauctions.com.au/" + car_block.css("a::attr(href)").extract_first() for car_block in car_blocks]
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "http://www.centralautoauctions.com.au/cp_veh_inspection_report.aspx?sitekey=CMA&MTA=175304&/2005-AUDI-A3---SILVER-A-HATCHBACK"
        yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        title = response.css(".post-title::text").extract_first()
        initial_details = {
            "TITLE": title, "LINK": link}
        initial_details["DEALER NAME"] = "Central Auto Auctions"
        initial_details["LOCATION"] = "Central Auto Auctions Pty Ltd Lic. MD 1006191 171 Fison Ave West Eagle Farm Qld 4009"
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
