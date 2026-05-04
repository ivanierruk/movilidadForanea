from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import itertools
from tqdm import tqdm
import pandas as pd
import glob
import os
import re
import hashlib
import logging

# Set the output path for files 
path_out = '/home/output/'

# ================= LOGGER ======================
# Configure logging at the module level
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(path_out + 'scraping_errors_ADO.log', encoding='utf-8'),  # Log to file
    ]
)

logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# ===============================================

class ADOScraper:
    def __init__(self):
        """Initialize the Selenium WebDriver with Chrome options."""
        self.options = Options()
        self.driver = None
        self.wait = None
        self.base_url = "https://www.ado.com.mx/"
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_trip_id(self, origin, destination, departure_time, arrival_time, travel_date, scraping_date):
        """Generate a unique trip ID using a hash of trip attributes"""
        raw_string = f"{origin}|{destination}|{departure_time}|{arrival_time}|{travel_date}|{scraping_date}"
        hash_hex = hashlib.md5(raw_string.encode('utf-8')).hexdigest()[:8]
        return f"AMAD_{hash_hex}"

    def open_browser(self):
        """Open the browser and initialize WebDriver and WebDriverWait with error handling"""
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.options
            )
            self.wait = WebDriverWait(self.driver, 10)
            self.driver.get(self.base_url)
            time.sleep(5)
        except Exception as e:
            print(f"Error opening browser...")
            self.logger.error(f"Error opening browser: {e}", exc_info=True)
            if self.driver:
                self.driver.quit()
            raise

    def close_browser(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

    def define_routes(self):
        """Define all route combinations"""
        locations = [
            "Ciudad de México, CDMX",
            "Puebla, Pue.",
            "Cancún, Q.R.",
            "Acapulco de Juarez, Gro.",
            "Veracruz, Ver.",
        ]
        return list(itertools.permutations(locations, 2))

    def define_dates(self):
        """Generate the days into the future starting from today"""
        today = datetime.today()
        return [today + timedelta(days=i) for i in range(10)]

    def insert_origin(self, origin):
        """Locate and fill origin field in the browser URL"""
        try:
            # Wait for any loader overlay to disappear
            try:
                time.sleep(5)
                self.wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.ado-loader")
                ))
            except:
                time.sleep(5)
                pass

            time.sleep(5)
            origin_field = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "input-field")))
            origin_field.clear()
            origin_field.send_keys(origin)
            time.sleep(2)
            self.driver.find_element(By.XPATH, f"//*[contains(text(), '{origin}')]").click()
            print("Origin inserted...")
            time.sleep(5)
        except Exception as e:
            print(f"Error inserting origin...")
            self.logger.error(f"Error inserting origin '{origin}': {e}", exc_info=True)
            raise

    def insert_destination(self, destination):
        """Locate and fill destination field in the browser URL"""
        try: 
            destination_field = self.driver.find_elements(By.CLASS_NAME, "input-field")[1]
            destination_field.clear()
            destination_field.send_keys(destination)
            time.sleep(2)
            self.driver.find_element(By.XPATH, f"//*[contains(text(), '{destination}')]").click()
            print("Destination inserted...")
            time.sleep(5)
        except Exception as e:
            print(f"Error inserting destination...")
            self.logger.error(f"Error inserting destination '{destination}': {e}", exc_info=True)
            raise

    def open_date_picker(self):
        """Locate and interact with DatePicker (opens the date picker first)"""
        try: 
            date_field = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "date-field")))
            date_field.click()
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "DayPicker-Day")))
            time.sleep(3)
        except Exception as e: 
            print(f"Error opening date picker...")
            self.logger.error(f"Error opening date picker: {e}", exc_info=True)
            raise

    def insert_date(self, travel_date):
        """Insert the travel date in the format expected by the date picker"""

        try: 
            target_date_label = travel_date.strftime("%a %b %d %Y")
            date_element = self.driver.find_element(
                By.XPATH,
                f"//div[contains(@class, 'DayPicker-Day') and @aria-label='{target_date_label}']"
            )
            date_element.click()
            print("Date inserted...")
            time.sleep(3)
        except Exception as e:
            print(f"Error inserting the date...")
            self.logger.error(f"Error inserting the date, error: ({e})", exc_info=True)

    def submit_search_button(self):
        """Submit form clicking the submit button"""
        try: 
            submit_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-search")))
            submit_button.click()
            time.sleep(20)
        except Exception as e: 
            print(f"Error submitting search form...")
            self.logger.error(f"Error submitting search form: {e}", exc_info=True)
            raise

    def get_containers(self, travel_date, general_origin):
        """Fetch and parse trip containers, extracting the relevant information"""

        try: 
            trip_containers = self.driver.find_elements(By.CLASS_NAME, "trip-info")
            scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trips_data = []
        except Exception as e: 
            print(f"Error finding container elements...")
            self.logger.error(f"Error finding container elements: {e}", exc_info=True)
            raise

        print(f"Extracting data for {len(trip_containers)} containers...")

        # Iterate over the containers to extract the data 
        for trip in trip_containers:
            try: 

                start_time_elem = trip.find_element(By.CLASS_NAME, "trip-info_details_content_start-time")
                departure_time = start_time_elem.find_element(By.CLASS_NAME, "triptime").text.strip()
                origin = start_time_elem.text.replace(departure_time, "").strip()

                end_time_elem = trip.find_element(By.CLASS_NAME, "trip-info_details_content_end-time")
                arrival_time = end_time_elem.find_element(By.CLASS_NAME, "triptime").text.strip()
                destination_full = end_time_elem.text.replace(arrival_time, "").strip()
                
                # Split destination into day offset and clean destination
                day_offset = ""
                destination = destination_full
                if "+1 día" in destination_full:
                    day_offset = "+1"
                    destination = destination_full.replace("+1 día", "").strip()

                try:
                    price_elem = trip.find_element(
                        By.XPATH,
                        ".//p[contains(@class, 'trip-card_details_iternary-price_discounted')]"
                    )
                    price = price_elem.text.split(" MXN")[0].strip()
                except:
                    price = "N/A"

                trips_data.append({
                    "Origin General": general_origin.split(",")[0],  # Extract city name before comma
                    "Origin": origin,
                    "Destination": destination,
                    "Day Offset": day_offset,
                    "Departure Time": departure_time,
                    "Arrival Time": arrival_time,
                    "Price": price,
                    "Travel Date": travel_date.strftime("%Y-%m-%d"),
                    "Scraping Date": scraping_date,
                    "id": self.generate_trip_id(origin, destination, departure_time, arrival_time, travel_date.strftime("%Y-%m-%d"), scraping_date) # hash id 
                })
            except Exception as e: 
                self.logger.error(f"Error in the trip containers: {e}", exc_info=True)

        return trips_data

    def export_excel(self, path_out, trips_data, origin, destination, travel_date):
        """Export trips data to a unique Excel file for each route-date combination"""
        date_str = travel_date.strftime("%Y-%m-%d")
        origin_safe = origin.replace(", ", "_").replace(" ", "_")
        dest_safe = destination.replace(", ", "_").replace(" ", "_")
        filename = f"{path_out}ado_trips_{origin_safe}_to_{dest_safe}_{date_str[:12]}.xlsx"

        try: 
            df = pd.DataFrame(trips_data)
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"Saved {len(trips_data)} trips to {filename}")
            return filename

        except Exception as e: 
            print(f"Error exporting excel file...")
            self.logger.error(f"Error exporting excel file: {e}", exc_info=True)

    @staticmethod
    def concatenate_excels(path_out, output_files):
        """Concatenate all Excel files obtained during the scraping into a single final file"""
        if not output_files:
            print("No Excel files to concatenate...")
            return
        try: 
            all_dfs = [pd.read_excel(file, engine='openpyxl') for file in output_files]
            combined_df = pd.concat(all_dfs, ignore_index=True)
            final_output = f"{path_out}ado_trips_combined.xlsx"
            print(f"Data with duplicates: {combined_df.shape}")
            combined_df.drop_duplicates(subset='id', inplace=True) # Drop duplicated IDs (since we don't have more data)
            combined_df.to_excel(final_output, index=False, engine='openpyxl')
            print(f"Data without duplicates: {combined_df.shape}")
            print(f"Concatenated {len(output_files)} files into {final_output}")

        except Exception as e: 
            print("Error concatenating all files...")
            self.logger.error(f"Error concatenating all files: {e}", exc_info=True)

if __name__ == "__main__":
    
    scraper = ADOScraper()
    routes = scraper.define_routes()
    dates = scraper.define_dates()

    output_files = []

    for origin, destination in tqdm(routes, desc="Routes"):
        for travel_date in tqdm(dates, desc=f"Dates for {origin} to {destination}", leave=False):
            try:
                scraper.open_browser()
                scraper.insert_origin(origin)
                scraper.insert_destination(destination)
                scraper.open_date_picker()
                scraper.insert_date(travel_date)
                scraper.submit_search_button()
                trips_data = scraper.get_containers(travel_date, origin)  # Pass general_origin

                if trips_data:
                    filename = scraper.export_excel(path_out, trips_data, origin, destination, travel_date)
                    output_files.append(filename)
                else:
                    print(f"No trips found for {origin} to {destination} on {travel_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"Error scraping {origin} to {destination} on {travel_date.strftime('%Y-%m-%d')}...")
                scraper.logger.error(f"Error scraping {origin} - {destination} on {travel_date}: {e}", exc_info=True)
            finally:
                scraper.close_browser()
                time.sleep(10)

    scraper.concatenate_excels(path_out, output_files)
