"""Omnibus de México bus-route scraper.

Extracts intercity bus routes from the Omnibus de México platform
(https://www.odm.com.mx/) for the origin-destination pairs and dates given in
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
from pandera.errors import SchemaErrors
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from ..cleaning import normalize_missing
from ..config import Config
from ..logging_setup import setup_file_logging
from ..validation import validate_mobility
from ._dates import build_travel_dates

PLATFORM = "omnibus"


class OmnibusScraper:
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
        self.base_url = "https://www.odm.com.mx/"
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
        return f"AMOB_{hash_hex}"

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
            # Locate and interact with the select2 origin field
            origin_field = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#cbx_estado + .select2-container")
                )
            )
            origin_field.click()

            # Locate the select2 search input
            search_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-search__field"))
            )
            search_input.clear()
            search_input.send_keys(origin)
            search_input.send_keys(Keys.ENTER)
            time.sleep(3)  # Allow autocomplete to settle
        except Exception as e:
            print("Error inserting origin...")
            self.logger.error(f"Error inserting origin '{origin}': {e}", exc_info=True)
            raise

    def insert_destination(self, destination):
        """Locate and fill destination field in the browser URL"""
        try:
            destination_field = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#cbx_municipio + .select2-container")
                )
            )
            destination_field.click()

            # Locate the select2 search input
            search_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-search__field"))
            )
            search_input.clear()
            search_input.send_keys(destination)
            search_input.send_keys(Keys.ENTER)
            time.sleep(3)
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
                EC.presence_of_element_located((By.ID, "fechasalida1"))
            )
            date_field.click()
            time.sleep(2)
        except Exception as e:
            print("Error opening date picker...")
            self.logger.error(f"Error opening date picker: {e}", exc_info=True)
            raise

    def insert_date(self, travel_date):
        """Insert the travel date in the format expected by the date picker"""
        try:
            day = travel_date.day
            month = travel_date.month - 1  # jQuery UI datepicker months are 0-indexed
            year = travel_date.year

            # Wait for the date picker to be visible
            self.wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, "ui-datepicker"))
            )

            # Select the specific day in the date picker
            day_selector = (
                f"td[data-month='{month}'][data-year='{year}'] "
                f"a.ui-state-default:not(.ui-state-disabled)"
            )
            day_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, day_selector))
            )

            # Filter for the exact day
            for element in day_elements:
                if element.text.strip() == str(day):
                    self.driver.execute_script(
                        "arguments[0].click();", element
                    )  # JavaScript click
                    break

            time.sleep(3)
        except Exception as e:
            print("Error inserting the date...")
            self.logger.error(f"Error inserting the date, error: ({e})", exc_info=True)

    def submit_search_button(self):
        """Submit form clicking the submit button"""
        try:
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "idboton"))
            )
            submit_button.click()
            time.sleep(15)
        except Exception as e:
            print("Error submitting search form...")
            self.logger.error(f"Error submitting search form: {e}", exc_info=True)
            raise

    def get_containers(self, travel_date, origin, destination):
        """Fetch and parse trip containers, extracting the relevant information"""
        try:
            trip_containers = self.driver.find_elements(By.ID, "u66237")
            scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trips_data = []
            print("Trip containers: ", len(trip_containers))
            time.sleep(4)

            # get the original origin
            original_origin = origin.split(" ")[0]
        except Exception as e:
            print("Error finding container elements...")
            self.logger.error(f"Error finding container elements: {e}", exc_info=True)
            raise

        for trip in trip_containers[1:]:
            try:
                # Departure time
                departure_time = (
                    trip.find_element(By.CSS_SELECTOR, "input.HoraSalida")
                    .get_attribute("value")
                    .strip()
                )

                # Arrival time
                arrival_time = (
                    trip.find_element(By.CSS_SELECTOR, "input.HoraLlegada")
                    .get_attribute("value")
                    .strip()
                )

                # Origin
                trip_origin = origin

                # Destination
                destination = destination

                try:
                    price_elem = (
                        trip.find_element(By.CSS_SELECTOR, "input.Tarifa_Promo")
                        .get_attribute("value")
                        .strip()
                    )
                    price = f"MXN {price_elem}"
                except Exception:
                    price = "N/A"

                trips_data.append(
                    {
                        "Origin General": original_origin,
                        "Origin": trip_origin,
                        "Destination": destination,
                        "Departure Time": departure_time,
                        "Arrival Time": arrival_time,
                        "Price": price,
                        "Travel Date": travel_date.strftime("%Y-%m-%d"),
                        "Scraping Date": scraping_date,
                        "id": self.generate_trip_id(
                            origin,
                            destination,
                            departure_time,
                            arrival_time,
                            travel_date.strftime("%Y-%m-%d"),
                            scraping_date,
                        ),  # hash id
                    }
                )
            except Exception as e:
                self.logger.error(f"Error in the trip containers: {e}", exc_info=True)

        return trips_data

    def export_excel(self, output_dir, trips_data, origin, destination, travel_date):
        """Export trips data to a unique Excel file for each route-date combination"""
        date_str = travel_date.strftime("%Y-%m-%d")
        origin_safe = origin.replace(", ", "_").replace(" ", "_")
        dest_safe = destination.replace(", ", "_").replace(" ", "_")
        filename = (
            Path(output_dir)
            / f"Omnibus_trips_{origin_safe}_to_{dest_safe}_{date_str[:12]}.xlsx"
        )

        try:
            df = pd.DataFrame(trips_data)
            df = normalize_missing(df)
            try:
                validate_mobility(df)
            except SchemaErrors as exc:
                self.logger.warning(
                    f"Data validation reported issues:\n%s {exc.failure_cases}"
                )
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
            final_output = Path(output_dir) / "omnibus_trips_combined.xlsx"
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
            logging.getLogger("OmnibusScraper").error(
                f"Error concatenating all files: {e}", exc_info=True
            )


def scrape_omnibus(config: Config) -> pd.DataFrame:
    """
    Run the full Omnibus extraction driven by `config`.
    """
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_file_logging(output_dir)

    routes = config.mobility.routes
    dates = build_travel_dates(config.mobility.start_date, config.mobility.n_days)

    scraper = OmnibusScraper(headless=config.mobility.headless)
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
                scraper.submit_search_button()
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
