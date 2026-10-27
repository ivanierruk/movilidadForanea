"""Booking.com hotel-geolocation scraper.

Extracts georeferenced hotel coordinates from Booking.com for the cities and
check-in date given in the configuration, and writes one .xlsx file per city
plus a consolidated file.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import brotli
import pandas as pd
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from ..config import Config

logger = logging.getLogger(__name__)

PLATFORM = "booking"


class BookingScraper:
    def __init__(self, headless: bool = False, stay_nights: int = 5):
        """
        Initialize the Selenium WebDriver with Chrome options.
        """
        self.options = Options()
        if headless:
            self.options.add_argument("--headless=new")
        self.stay_nights = stay_nights
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=self.options
        )
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://www.booking.com"
        self.logger = logging.getLogger(self.__class__.__name__)

    def open_browser(self):
        """Open the browser and initialize WebDriver and WebDriverWait with error handling"""
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=self.options
            )
            self.wait = WebDriverWait(self.driver, 10)
            self.driver.get(self.base_url)
        except Exception as e:
            self.logger.error(f"Error opening browser: {e}", exc_info=True)
            print(f"Error opening browser: {e}")
            if self.driver:
                self.driver.quit()
            raise

    def close_browser(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

    def close_popup(self):
        """Close a possible pop up window form the website"""
        try:
            close_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@aria-label='Dismiss sign-in info.']")
                )
            )
            close_button.click()
            time.sleep(1)  # Wait for pop-up to close
            print("Pop-up closed successfully")
        except Exception as e:
            print("No pop-up found or unable to close pop-up, proceeding...")
            self.logger.info(
                f"No pop-up found or unable to close pop-up, proceeding: {e}",
                exc_info=True,
            )

    def insert_destination(self, destination):
        """Locate and fill destination field in the browser URL"""
        try:
            destination_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "ss"))
            )
            # Pass the destination
            destination_field.send_keys(destination)
            time.sleep(2)
            destination_field.send_keys(Keys.TAB)
            time.sleep(1)
        except Exception as e:
            print("Error inserting destination...")
            self.logger.error(
                f"Error inserting destination '{destination}': {e}", exc_info=True
            )
            raise

    def open_date_picker(self):
        """Locate and interact with DatePicker (opens the date picker first)"""
        try:
            date_field = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "[data-testid='searchbox-dates-container']")
                )
            )
            date_field.click()
            time.sleep(1)
        except Exception as e:
            print("Error opening date picker...")
            self.logger.error(f"Error opening date picker: {e}", exc_info=True)
            raise

    def insert_date(self, travel_date):
        """Insert the travel date in the format expected by the date picker"""
        try:
            print(f"Travel date: {travel_date}")

            # Define check-in and check-out dates
            checkin_date_obj = datetime.strptime(travel_date, "%Y-%m-%d")
            checkin_date = checkin_date_obj.strftime("%Y-%m-%d")  # keep as string
            checkout_date = (
                checkin_date_obj + timedelta(days=self.stay_nights)
            ).strftime("%Y-%m-%d")
            checkout_date_obj = datetime.strptime(checkout_date, "%Y-%m-%d")
        except Exception as e:
            print(f"Error on the date parsing ({travel_date})...")
            self.logger.error(
                f"Error on the date parsing ({travel_date}): {e}", exc_info=True
            )

        # Parse the displayed month/year from the first calendar pane
        try:
            month_year_element = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.d7bd90e008:first-child h3")
                )
            )
            month_year_text = month_year_element.text
            current_month = datetime.strptime(month_year_text, "%B %Y")
        except Exception as e:
            self.logger.error(f"Error parsing calendar month: {e}")
            print(f"Error parsing calendar month: {e}")
            current_month = datetime.today().replace(day=1)  # Fallback to current month

        # Navigate to check-in month
        try:
            checkin_date_obj = datetime.strptime(checkin_date, "%Y-%m-%d")
            months_diff = (checkin_date_obj.year - current_month.year) * 12 + (
                checkin_date_obj.month - current_month.month
            )
            for _ in range(months_diff):
                next_month_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[aria-label='Next month']")
                    )
                )
                next_month_button.click()
                time.sleep(1)  # Wait for calendar to update
        except Exception as e:
            self.logger.error(f"Error checking-in month: {e} ")
            raise

        # Select check-in date from the first calendar pane
        try:
            checkin_element = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f"div.d7bd90e008:first-child span[data-date='{checkin_date}']",
                    )
                )
            )
            checkin_element.click()
            print(f"Selected check-in date: {checkin_date}")
        except Exception as e:
            self.logger.error(f"Error selecting check-in date {checkin_date}: {e}")
            print(f"Error selecting check-in date {checkin_date}: {e}")

        time.sleep(1)  # Wait for calendar to update

        # Check if check-in and check-out are in the same month
        same_month = (
            checkin_date_obj.month == checkout_date_obj.month
            and checkin_date_obj.year == checkout_date_obj.year
        )

        if same_month:
            # Select check-out date from the first calendar pane
            try:
                checkout_element = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            f"div.d7bd90e008:first-child span[data-date='{checkout_date}']",
                        )
                    )
                )
                checkout_element.click()
                print(f"Selected check-out date: {checkout_date} (same month)")
            except Exception as e:
                self.logger.error(
                    f"Error selecting check-out date {checkout_date} in first pane: {e}"
                )
                print(
                    f"Error selecting check-out date {checkout_date} in first pane: {e}"
                )
        else:
            # Parse the displayed month/year from the second calendar pane
            try:
                month_year_element = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.d7bd90e008:nth-child(2) h3")
                    )
                )
                month_year_text = month_year_element.text
                current_month = datetime.strptime(month_year_text, "%B %Y")
            except Exception as e:
                self.logger.error(f"Error parsing second calendar month: {e}")
                print(f"Error parsing second calendar month: {e}")
                current_month = datetime.today().replace(day=1) + timedelta(days=30)

            # Navigate to check-out month
            try:
                months_diff = (checkout_date_obj.year - current_month.year) * 12 + (
                    checkout_date_obj.month - current_month.month
                )
                for _ in range(months_diff):
                    next_month_button = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "button[aria-label='Next month']")
                        )
                    )
                    next_month_button.click()
                    time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error selecting check-out month: {e}")
                raise

            # Select check-out date from the second calendar pane
            try:
                checkout_element = self.wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            f"div.d7bd90e008:nth-child(2) span[data-date='{checkout_date}']",
                        )
                    )
                )
                checkout_element.click()
                print(f"Selected check-out date: {checkout_date} (different month)")
            except Exception as e:
                self.logger.error(
                    f"Error selecting check-out date {checkout_date} in second pane: {e}"
                )
                print(
                    f"Error selecting check-out date {checkout_date} in second pane: {e}"
                )

        time.sleep(1)  # Wait for date picker to close
        return checkin_date, checkout_date

    def submit_search_button(self):
        """Submit form clicking the submit button"""
        try:
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            submit_button.click()
            time.sleep(8)
            print("Search form submitted successfully")
        except Exception as e:
            print("Error submitting search form...")
            self.logger.error(f"Error submitting search form: {e}", exc_info=True)
            raise

    def submit_button_map(self):
        """To click the button map"""
        # clean memory (requests)
        if hasattr(self.driver, "requests"):
            del self.driver.requests

        try:
            # 1. Exact button based on the HTML
            map_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-map-trigger-button='1']")
                )
            )

            # 2. Scroll to place the button at center and force focus
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", map_button
            )
            time.sleep(1)

            # 3. Click the button
            map_button.click()
            print(
                "Clicked map button using CSS selector: button[data-map-trigger-button='1']"
            )

            time.sleep(15)
        except Exception as e:
            self.logger.error(f"Failed to click map button: {e}", exc_info=True)
            raise Exception("Could not click 'Show on map' button.")

    def extract_bounding_box(self):
        """Extract the MARKERS_ON_MAP bounding box from the first GraphQL response"""
        graphql_requests = [
            req
            for req in self.driver.requests
            if req.method == "POST" and "booking.com/dml/graphql" in req.url
        ]

        for request in graphql_requests:
            try:
                content_encoding = request.response.headers.get("Content-Encoding", "")
                if "br" in content_encoding.lower():
                    body = brotli.decompress(request.response.body).decode("utf-8")
                elif "gzip" in content_encoding.lower():
                    body = gzip.decompress(request.response.body).decode("utf-8")
                else:
                    body = request.response.body.decode("utf-8", errors="replace")

                json_data = json.loads(body)
                bboxes = (
                    json_data.get("data", {})
                    .get("searchQueries", {})
                    .get("search", {})
                    .get("searchMeta", {})
                    .get("boundingBoxes", [])
                )

                for bbox in bboxes:
                    if bbox.get("type") == "MARKERS_ON_MAP":
                        bb = {
                            "swLat": bbox["swLat"],
                            "swLon": bbox["swLon"],
                            "neLat": bbox["neLat"],
                            "neLon": bbox["neLon"],
                        }

                        print(
                            f"Bounding box: swLat={bb['swLat']}, swLon={bb['swLon']}, "
                            f"neLat={bb['neLat']}, neLon={bb['neLon']}"
                        )
                        return bb
            except Exception as e:
                self.logger.warning(f"Error extracting bounding box: {e}")
                continue

        print("No MARKERS_ON_MAP bounding box found")
        return None

    def subdivide_bounding_box(self, bbox, grid_size=3):
        """Subdivide a bounding box into a grid of smaller boxes with slight overlap"""
        lat_step = (bbox["neLat"] - bbox["swLat"]) / grid_size
        lon_step = (bbox["neLon"] - bbox["swLon"]) / grid_size
        overlap = 0.01  # ~1km overlap to avoid missing properties at edges

        sub_boxes = []
        for row in range(grid_size):
            for col in range(grid_size):
                sub_box = {
                    "swLat": bbox["swLat"] + (row * lat_step) - overlap,
                    "swLon": bbox["swLon"] + (col * lon_step) - overlap,
                    "neLat": bbox["swLat"] + ((row + 1) * lat_step) + overlap,
                    "neLon": bbox["swLon"] + ((col + 1) * lon_step) + overlap,
                }
                sub_boxes.append(sub_box)

        return sub_boxes

    def pan_map_to_bounds(self, sub_boxes):
        """Pan the map to each sub-box using the captured map instance"""
        # 12 is the initial value for the zoom
        for idx, box in enumerate(sub_boxes):
            pan_js = f"""
            var bounds = new google.maps.LatLngBounds(
                new google.maps.LatLng({box['swLat']}, {box['swLon']}),
                new google.maps.LatLng({box['neLat']}, {box['neLon']})
            );
            window.foundMap.fitBounds(bounds);
            window.foundMap.setZoom(Math.max(window.foundMap.getZoom(), 14));
            """
            try:
                self.driver.execute_script(pan_js)
                print(
                    f"Panned to sub-box {idx + 1}/{len(sub_boxes)}, total GraphQL requests so far: "
                    f"{len([r for r in self.driver.requests if 'graphql' in r.url and r.method == 'POST'])}"
                )
                time.sleep(5)
            except Exception as e:
                print(f"Error panning to sub-box {idx + 1}: {e}")
                self.logger.error(f"Error panning to sub-box {idx + 1}: {e}")
                continue

    def capture_map_instance(self):
        """Inject JS patch and trigger a small drag to capture the Google Maps instance"""
        patch_js = """
        window.foundMap = null;
        ['setCenter', 'panTo', 'panBy', 'fitBounds', 'setZoom', 'getBounds'].forEach(function(method) {
            var orig = google.maps.Map.prototype[method];
            google.maps.Map.prototype[method] = function() {
                window.foundMap = this;
                google.maps.Map.prototype[method] = orig;
                return orig.apply(this, arguments);
            };
        });
        """
        self.driver.execute_script(patch_js)
        print("Injected map capture patch")

        try:
            map_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.gm-style"))
            )
            actions = ActionChains(self.driver)
            actions.click_and_hold(map_element).move_by_offset(
                50, 0
            ).release().perform()
            time.sleep(5)
        except Exception as e:
            self.logger.error(f"Error during map drag: {e}")
            return False

        found = self.driver.execute_script("return window.foundMap !== null;")
        if found:
            zoom = self.driver.execute_script("return window.foundMap.getZoom();")
            print(f"Map instance captured, current zoom: {zoom}")
            return True
        else:
            print("Failed to capture map instance")
            return False

    def get_containers(self, travel_date, destination):
        """Fetch and parse a json containing all the data form the query"""
        graphql_requests = [
            req
            for req in self.driver.requests
            if req.method == "POST" and "https://www.booking.com/dml/graphql" in req.url
        ]

        # How many had results vs None response:
        null_count = len([r for r in graphql_requests if r.response is None])
        print(
            f"Total GraphQL requests: {len(graphql_requests)}, null responses: {null_count}"
        )

        all_responses = []
        if not graphql_requests:
            print("No POST requests to https://www.booking.com/dml/graphql found.")
        else:
            for i, request in enumerate(graphql_requests):
                try:
                    content_encoding = request.response.headers.get(
                        "Content-Encoding", ""
                    )

                    parsed_url = urllib.parse.urlparse(request.url)
                    query_params = urllib.parse.parse_qs(parsed_url.query)

                    if "br" in content_encoding.lower():
                        response_body = brotli.decompress(request.response.body).decode(
                            "utf-8"
                        )
                    elif "gzip" in content_encoding.lower():
                        response_body = gzip.decompress(request.response.body).decode(
                            "utf-8"
                        )
                    else:
                        response_body = request.response.body.decode(
                            "utf-8", errors="replace"
                        )

                    # get the response to a json
                    json_data = json.loads(response_body)

                    # ============= VALIDATION ==============
                    # Save the results only if the request contains the desired structure
                    results = None
                    try:
                        results = json_data["data"]["searchQueries"]["search"][
                            "results"
                        ]
                    except (KeyError, TypeError):
                        pass

                    if results:
                        all_responses.append(json_data)
                    # =======================================

                except (json.JSONDecodeError, AttributeError, brotli.error) as e:
                    self.logger.warning(
                        f"Error parsing request {i+1} ({request.url}): {e}"
                    )
                    try:
                        self.logger.warning(
                            f"Response headers: {dict(request.response.headers)}"
                        )
                    except Exception:
                        print("Could not print response headers...")
                        self.logger.error("Could not print response headers.")
                    continue

        return all_responses

    def export_excel(
        self,
        output_dir,
        trips_data_list,
        destination,
        travel_date,
        checkin_date,
        checkout_date,
    ):
        """Export trips data to a unique Excel file"""
        print("Exporting Excel file...")
        dict_query = {
            "id": [],
            "pageName": [],
            "address": [],
            "countryCode": [],
            "longitude": [],
            "latitude": [],
            "checkIn": [],
            "checkOut": [],
        }

        try:
            for trips_data in trips_data_list:
                results = trips_data["data"]["searchQueries"]["search"]["results"]
                for i in range(len(results)):
                    basic = results[i]["basicPropertyData"]
                    dict_query["id"].append(basic["id"])
                    dict_query["pageName"].append(basic["pageName"])
                    dict_query["address"].append(basic["location"]["address"])
                    dict_query["countryCode"].append(basic["location"]["countryCode"])
                    dict_query["longitude"].append(basic["location"]["longitude"])
                    dict_query["latitude"].append(basic["location"]["latitude"])
                    dict_query["checkIn"].append(checkin_date)
                    dict_query["checkOut"].append(checkout_date)

            date_str = str(datetime.today())
            dest_safe = destination.replace(", ", "_").replace(" ", "_")
            # Truncated to keep the filename within the Windows path limit
            filename = (
                Path(output_dir) / f"Booking_trips_to_{dest_safe}_{date_str[:12]}.xlsx"
            )

            print("Generating the DataFrame...")
            df = pd.DataFrame(dict_query)
            df["query_date"] = date_str
            df["destination"] = dest_safe

            # Drop the duplicated
            df.drop_duplicates(subset=["id"], inplace=True)
            print(f"Export DataFrame shape without duplicates: {df.shape} ...")

            # export to excel
            df.to_excel(filename, index=False, engine="openpyxl")

            print(f"Saved trips to file {dest_safe}_{date_str[:12]}.xlsx")
            return filename
        except Exception as e:
            print("Error exporting excel file...")
            self.logger.error(f"Error exporting excel file: {e}", exc_info=True)

    @staticmethod
    def concatenate_excels(output_dir, output_files):
        """Concatenate all Excel files obtained during the scraping into a single final file"""
        if not output_files:
            print("No Excel files to concatenate.")
            logging.getLogger("BookingScraper").error("No Excel files to concatenate.")
            return None

        try:
            all_dfs = [pd.read_excel(file, engine="openpyxl") for file in output_files]
            combined_df = pd.concat(all_dfs, ignore_index=True)
            final_output = Path(output_dir) / "Booking_trips_combined.xlsx"
            combined_df.to_excel(final_output, index=False, engine="openpyxl")

            print(f"Concatenated {len(output_files)} files into {final_output}")
            return final_output
        except Exception as e:
            print("Error concatenating all files...")
            logging.getLogger("BookingScraper").error(
                f"Error concatenating all files: {e}", exc_info=True
            )


def _setup_file_logging(output_dir: Path) -> None:
    """
    Attach a file handler that writes errors to output_dir/scraping_errors_Booking.log.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(
        output_dir / "scraping_errors_Booking.log", encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(handler)


def scrape_booking(config: Config) -> pd.DataFrame:
    """
    Run the full Booking extraction driven by `config`.
    """
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_file_logging(output_dir)

    cities = config.accommodation.cities
    # Accommodation uses a single check-in date (not a range like mobility).
    dates = [config.accommodation.checkin_date.strftime("%Y-%m-%d")]

    scraper = BookingScraper(
        headless=config.accommodation.headless,
        stay_nights=config.accommodation.stay_nights,
    )
    output_files = []

    for destination in tqdm(cities, desc="Cities"):
        for travel_date in tqdm(dates, desc=f"Dates for {destination}", leave=False):
            try:
                scraper.open_browser()
                scraper.close_popup()
                scraper.insert_destination(destination)
                scraper.open_date_picker()
                checkin_date, checkout_date = scraper.insert_date(travel_date)
                scraper.submit_search_button()
                scraper.close_popup()
                scraper.submit_button_map()

                # Extract bounding box and pan through sub-areas
                bbox = scraper.extract_bounding_box()
                map_captured = scraper.capture_map_instance()

                if bbox and map_captured:
                    sub_boxes = scraper.subdivide_bounding_box(bbox, grid_size=5)
                    scraper.pan_map_to_bounds(sub_boxes)

                trips_data_list = scraper.get_containers(travel_date, destination)

                print(f"Size of requests: {len(trips_data_list)}")

                if trips_data_list:
                    filename = scraper.export_excel(
                        output_dir,
                        trips_data_list,
                        destination,
                        travel_date,
                        checkin_date,
                        checkout_date,
                    )
                    if filename:
                        output_files.append(filename)
                else:
                    print(f"No trips found for {destination} on {travel_date}")
            except Exception as e:
                print(f"Error scraping {destination} on {travel_date}...")
                scraper.logger.error(
                    f"Error scraping {destination} on {travel_date}: {e}", exc_info=True
                )
            finally:
                scraper.close_browser()
                time.sleep(10)

    final_output = scraper.concatenate_excels(output_dir, output_files)
    if final_output:
        return pd.read_excel(final_output, engine="openpyxl")
    return pd.DataFrame()
