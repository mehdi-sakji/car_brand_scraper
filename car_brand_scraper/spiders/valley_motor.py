import scrapy
import json
import pandas
import pdb


class ValleyMotorSpider(scrapy.Spider):
    """ Spider for scraping Valley Motor cars. """


    name = "valley_motor"


    def init_data(self):
        """ Initiates global settings. """

        self.details_mapping = {
            "BUILD MONTH/YEAR": "YEAR",
            "VARIANT": "BADGE",
            "ENGINE SIZE": "ENGINE SIZE (CC)",
            "COLOR": "EXTERIOR COLOUR",
            "ENGINE NO.": "ENGINE NUMBER"}


    def start_requests(self):
        """ Browse to the base url the scraper starts from. """

        base_url = "http://www.valleymotorauctions.com.au/search_results.aspx?sitekey=VMA&make=All%20Makes&model=All%20Models&keyword=&fromyear%20=From%20Any&toyear=To%20Any&body=All%20Body%20Types"
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

        car_blocks = response.css(".listing")
        cars_urls = [
            "http://www.valleymotorauctions.com.au/" + car_block.css("a::attr(href)").extract_first() for car_block in car_blocks]
        """
        for url in cars_urls:
            yield scrapy.Request(
                url = url, callback = self.parse_car, meta={"url": url})
        """
        url = "http://www.valleymotorauctions.com.au/cp_veh_inspection_report.aspx?sitekey=VMA&MTA=250969"
        yield scrapy.Request(
            url = url, callback = self.parse_car, meta={"url": url})


    def parse_car(self, response):
        """ Extracts one car's information. """

        link = response.meta.get("url")
        details_box = response.css(".details-box")[0]
        title = details_box.css(".title::text").extract_first()
        year = title.split(" ")[0]
        make = title.split(" ")[1]
        fuel_type = details_box.css("#lblFuelType::text").extract_first()
        rating_div = details_box.css(".rating")[0]
        rating = len(rating_div.css(".fa-star"))
        body_type = details_box.css("#lblBody::text").extract_first()
        transmission = details_box.css("#lblTransmission::text").extract_first()
        rego = details_box.css("#lblRego::text").extract_first()
        rego_expiry = details_box.css("#lblRegExpiry::text").extract_first()
        stock_no = details_box.css("#lblMTA::text").extract_first()
        initial_details = {
            "TITLE": title, "LINK": link, "MAKE": make, "YEAR": year, "FUEL TYPE": fuel_type,
            "ANCAP RATING": rating, "BODY TYPE": body_type, "TRANSMISSION": transmission, "REGO": rego,
            "REGO EXPIRY": rego_expiry, "STOCK NO": stock_no}
        initial_details["DEALER NAME"] = "Valley Motor Auctions"
        initial_details["LOCATION"] = "47 Munibung Road, Cardiff NSW 2285"
        overview_block = response.css("#overview")[0]
        overview = overview_block.css("p *::text").extract()
        features_block = response.css("#features")[0]
        features = features_block.css("li::text").extract()
        if len(overview)>=1:
            overview = [item.strip() for item in overview]
            initial_details["COMMENTS"] = " ".join(overview)
        if len(features)>=1:
            features = [item.strip() for item in features]
            initial_details["VEHICLE FEATURES"] = ",".join(features)
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
