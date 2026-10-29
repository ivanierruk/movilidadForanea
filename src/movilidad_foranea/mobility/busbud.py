"""BusBud bus-route scraper.

Extracts intercity bus routes from the BusBud aggregator
(https://www.busbud.com/) for the origin-destination pairs and dates given in
the configuration, and writes one .xlsx file per route-date plus a
consolidated file per platform.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from ..config import Config
from ._dates import build_travel_dates

logger = logging.getLogger(__name__)

PLATFORM = "busbud"


class BusBudScraper:
    def __init__(self, headless: bool = False):
        """
        Initialize the Selenium WebDriver with Chrome options.
        """
        self.options = Options()
        if headless:
            self.options.add_argument("--headless=new")
        self.options.add_argument("--window-size=1920,1080")  # wide view
        self.driver = None
        self.wait = None
        self.base_url = "https://www.busbud.com/es-mx/bt/billetes-de-autobus"
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_trip_id(
        self,
        origin,
        destination,
        departure_time,
        arrival_time,
        travel_date,
        scraping_date,
    ):
        """Generate a unique trip ID using a hash of trip attributes"""
        raw_string = f"{origin}|{destination}|{departure_time}|{arrival_time}|{travel_date}|{scraping_date}"
        hash_hex = hashlib.md5(raw_string.encode("utf-8")).hexdigest()[:8]
        return f"AMBB_{hash_hex}"

    def open_browser(self):
        """Open the browser and initialize WebDriver and WebDriverWait with error handling"""
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.options,
            )
            self.wait = WebDriverWait(self.driver, 10)
            self.driver.get(self.base_url)
            time.sleep(5)
        except Exception as e:
            print("Error opening browser...")
            self.logger.error(f"Error opening browser: {e}", exc_info=True)
            if self.driver:
                self.driver.quit()
            raise

    def close_browser(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

    def insert_origin(self, origin):
        """Locate and fill origin field in the browser URL"""
        try:
            origin_field = self.wait.until(
                EC.element_to_be_clickable((By.ID, "origin-c1ty-input"))
            )
            origin_field.click()
            time.sleep(1)

            # Clear any existing value
            origin_field.clear()
            time.sleep(1)

            # Type the city name character by character
            short_name = origin.split(",")[0]
            for char in short_name:
                origin_field.send_keys(char)
                time.sleep(0.1)

            time.sleep(3)  # Wait for suggestions

            # Click the first suggestion
            suggestion = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#origin-dropdown div[role='option']")
                )
            )
            suggestion.click()
            print("Origin inserted...")
            time.sleep(3)
        except Exception as e:
            print("Error inserting origin...")
            self.logger.error(f"Error inserting origin '{origin}': {e}", exc_info=True)
            raise

    def insert_destination(self, destination):
        """Locate and fill destination field in the browser URL"""
        try:
            destination_field = self.wait.until(
                EC.element_to_be_clickable((By.ID, "destination-c1ty-input"))
            )
            destination_field.click()
            time.sleep(1)

            destination_field.clear()
            time.sleep(1)

            short_name = destination.split(",")[0]
            for char in short_name:
                destination_field.send_keys(char)
                time.sleep(0.1)

            time.sleep(3)

            suggestion = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#destination-dropdown div[role='option']")
                )
            )
            suggestion.click()
            print("Destination inserted...")
            time.sleep(2)
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
                EC.presence_of_element_located((By.ID, "outbound-date-input"))
            )
            date_field.click()
            time.sleep(3)
        except Exception as e:
            print("Error opening date picker...")
            self.logger.error(f"Error opening date picker: {e}", exc_info=True)
            raise

    def insert_date(self, travel_date):
        """Insert the travel date in the format expected by the date picker"""
        try:
            aria_label_date = (
                f"{travel_date.year}-{travel_date.month:02d}-{travel_date.day:02d}"
            )

            # Pass the date to the datepicker
            date_element = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f"button[aria-label='{aria_label_date}']")
                )
            )
            date_element.click()
            time.sleep(3)
        except Exception as e:
            print("Error inserting the date...")
            self.logger.error(f"Error inserting the date, error: ({e})", exc_info=True)

    def get_window(self):
        """Get the correct window, since the website opens two windows when performing the search"""
        original_window = self.driver.current_window_handle
        print(f"Original window: {original_window}")
        return original_window

    def submit_search_button(self):
        """Submit form clicking the submit button"""
        try:
            submit_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button[aria-label='Búsqueda'][id='search-submit-button-md']",
                    )
                )
            )
            submit_button.click()
            time.sleep(10)
        except Exception as e:
            print("Error submitting search form...")
            self.logger.error(f"Error submitting search form: {e}", exc_info=True)
            raise

    def select_window(self, original_window):
        """To select the proper window once the search is performed"""
        try:
            results_window = None
            all_windows = self.driver.window_handles  # to get all the windows

            # to iterate over all windows (tabs)
            for window in all_windows:
                if window != original_window:  # change to the proper window
                    self.driver.switch_to.window(window)
                    current_url = self.driver.current_url
        except Exception as e:
            print("Error selecting the window...")
            self.logger.error(f"Error selecting the window: {e}", exc_info=True)
            raise

    def get_containers(self, travel_date, origin, destination):
        """Fetch and parse trip containers, extracting the relevant information"""
        try:
            trip_containers = self.driver.find_elements(
                By.CSS_SELECTOR, "[data-testid*='departure-card']"
            )
            scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trips_data = []

            print("Trip containers: ", len(trip_containers))
            unique_trips = set()  # Track unique trips
            time.sleep(5)

            # get the original origin and original destination
            original_origin = origin.split(",")[0]
            original_destination = destination.split(",")[0]
        except Exception as e:
            print("Error finding container elements...")
            self.logger.error(f"Error finding container elements: {e}", exc_info=True)
            raise

        for trip in trip_containers:

            # Scroll with offset to avoid header overlap
            self.driver.execute_script("window.scrollBy(0, -100);")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", trip
            )
            time.sleep(0.3)  # Reduced wait time

            # Get trip content to create unique hash
            try:
                content = trip.find_element(
                    By.CSS_SELECTOR, "[data-cy='departure-card-content']"
                ).text
            except Exception as e:
                self.logger.error(
                    f"Error finding container element content: {e}", exc_info=True
                )
                content = trip.text

            # Create unique hash of trip content
            trip_hash = hashlib.md5(content.encode()).hexdigest()

            # Skip if we've already processed this trip
            if trip_hash in unique_trips:
                continue
            unique_trips.add(trip_hash)

            # Departure time
            try:
                departure_time = trip.find_element(
                    By.CSS_SELECTOR, "time[itemprop='departureTime']"
                ).text.strip()
            except Exception as e:
                self.logger.error(f"Error extracting departure time: {e}")
                departure_time = "N/A"

            # Arrival time
            try:
                arrival_time = trip.find_element(
                    By.CSS_SELECTOR, "time[itemprop='arrivalTime']"
                ).text.strip()
            except Exception as e:
                self.logger.error(f"Error extracting arrival time: {e}")
                arrival_time = "N/A"

            # Extract Origin (specific station)
            try:
                origin_container = trip.find_element(
                    By.CSS_SELECTOR,
                    "[data-cy='departure-card-locations'] > div:first-child",
                )
                trip_origin = origin_container.find_element(
                    By.CSS_SELECTOR,
                    "span.t-t4yyVf-DCLocation-locationDetail-ref",
                ).text.strip()
            except Exception as e:
                print(
                    f"Origin error for trip {original_origin} -> {original_destination}..."
                )
                self.logger.error(f"Error finding origin station: {e}", exc_info=True)
                trip_origin = "N/A"

            # Extract Destination (specific station)
            try:
                destination_container = trip.find_element(
                    By.CSS_SELECTOR,
                    "[data-cy='departure-card-locations'] > div:nth-child(2)",
                )
                trip_destination = destination_container.find_element(
                    By.CSS_SELECTOR,
                    "span.t-t4yyVf-DCLocation-locationDetail-ref",
                ).text.strip()
            except Exception as e:
                print(
                    f"Destination error for trip {original_origin} -> {original_destination}..."
                )
                self.logger.error(
                    f"Error finding destination station: {e}", exc_info=True
                )
                trip_destination = "N/A"

            # Price
            try:
                price_value = trip.find_element(
                    By.CSS_SELECTOR, "[data-cy='displayed-price']"
                ).text.strip()
                price = f"MXN {price_value.replace('$', '').replace(',', '')}"
            except Exception as e:
                self.logger.error(f"Error finding price: {e}", exc_info=True)
                price = "N/A"

            trips_data.append(
                {
                    "Origin General": original_origin,
                    "Origin": original_origin + "-" + trip_origin,
                    "Destination": original_destination + "-" + trip_destination,
                    "Departure Time": departure_time[
                        14:
                    ].strip(),  # to avoid extra data in the tag
                    "Arrival Time": arrival_time[
                        15:
                    ].strip(),  # to avoid extra data in the tag
                    "Price": price,
                    "Travel Date": travel_date.strftime("%Y-%m-%d"),
                    "Scraping Date": scraping_date,
                    "id": self.generate_trip_id(
                        trip_origin,
                        trip_destination,
                        departure_time,
                        arrival_time,
                        travel_date.strftime("%Y-%m-%d"),
                        scraping_date,
                    ),  # hash id
                }
            )

        return trips_data

    def export_excel(self, output_dir, trips_data, origin, destination, travel_date):
        """Export trips data to a unique Excel file for each route-date combination"""
        date_str = travel_date.strftime("%Y-%m-%d")
        origin_safe = origin.replace(", ", "_").replace(" ", "_")
        dest_safe = destination.replace(", ", "_").replace(" ", "_")
        filename = (
            Path(output_dir)
            / f"BudBus_trips_{origin_safe}_to_{dest_safe}_{date_str[:12]}.xlsx"
        )

        try:
            df = pd.DataFrame(trips_data)
            df.to_excel(filename, index=False, engine="openpyxl")
            print(f"Saved {len(trips_data)} trips to {filename}")
            return filename
        except Exception as e:
            print("Error exporting excel file...")
            self.logger.error(f"Error exporting excel file: {e}", exc_info=True)

    @staticmethod
    def concatenate_excels(output_dir, output_files):
        """Concatenate all Excel files obtained during the scraping into a single final file"""
        if not output_files:
            print("No Excel files to concatenate.")
            return

        try:
            all_dfs = [pd.read_excel(file, engine="openpyxl") for file in output_files]
            combined_df = pd.concat(all_dfs, ignore_index=True)
            final_output = Path(output_dir) / "budBus_trips_combined.xlsx"
            print(f"Data with duplicates: {combined_df.shape}")
            combined_df.drop_duplicates(
                subset="id", inplace=True
            )  # Drop duplicated IDs
            combined_df.to_excel(final_output, index=False, engine="openpyxl")
            print(f"Data without duplicates: {combined_df.shape}")
            print(f"Concatenated {len(output_files)} files into {final_output}")
            return final_output
        except Exception as e:
            print("Error concatenating all files...")
            logging.getLogger("BusBudScraper").error(
                f"Error concatenating all files: {e}", exc_info=True
            )


def _setup_file_logging(output_dir: Path) -> None:
    """Attach a file handler that writes errors to output_dir/scraping_errors_Busbud.log."""
    output_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(
        output_dir / "scraping_errors_Busbud.log", encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(handler)


def scrape_busbud(config: Config) -> pd.DataFrame:
    """
    Run the full BusBud extraction driven by `config`.
    """
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_file_logging(output_dir)

    routes = config.mobility.routes
    dates = build_travel_dates(config.mobility.start_date, config.mobility.n_days)

    scraper = BusBudScraper(headless=config.mobility.headless)
    output_files = []

    for origin, destination in tqdm(routes, desc="Routes"):
        for travel_date in tqdm(
            dates, desc=f"Dates for {origin} to {destination}", leave=False
        ):
            try:
                scraper.open_browser()
                scraper.insert_origin(origin)
                scraper.insert_destination(destination)
                scraper.open_date_picker()
                scraper.insert_date(travel_date)
                original_window = scraper.get_window()  # get the current window
                scraper.submit_search_button()
                scraper.select_window(
                    original_window
                )  # select the proper window with all the containers
                trips_data = scraper.get_containers(travel_date, origin, destination)

                if trips_data:
                    filename = scraper.export_excel(
                        output_dir, trips_data, origin, destination, travel_date
                    )
                    if filename:
                        output_files.append(filename)
                else:
                    print(
                        f"No trips found for {origin} to {destination} on {travel_date.strftime('%Y-%m-%d')}"
                    )
            except Exception as e:
                print(
                    f"Error scraping {origin} to {destination} on {travel_date.strftime('%Y-%m-%d')}: {e}"
                )
                scraper.logger.error(
                    f"Error scraping {origin} - {destination} on {travel_date}: {e}",
                    exc_info=True,
                )
            finally:
                scraper.close_browser()
                time.sleep(10)

    final_output = scraper.concatenate_excels(output_dir, output_files)
    if final_output:
        return pd.read_excel(final_output, engine="openpyxl")
    return pd.DataFrame()
