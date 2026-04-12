from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
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
path_out = "/home/output/"

# ================= LOGGER ======================
# Configure logging at the module level
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(path_out + 'scraping_errors_Clickbus.log', encoding='utf-8'),  # Log to file
    ]
)

logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
# ===============================================

class ClickbusScraper:
    def __init__(self):
        """Initialize the Selenium WebDriver with Chrome options."""
        self.options = Options()
        self.driver = None
        self.wait = None
        self.base_url = "https://www.clickbus.com.mx/"
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_trip_id(self, origin, destination, departure_time, arrival_time, travel_date, scraping_date):
        """Generate a unique trip ID using a hash of trip attributes"""
        raw_string = f"{origin}|{destination}|{departure_time}|{arrival_time}|{travel_date}|{scraping_date}"
        hash_hex = hashlib.md5(raw_string.encode('utf-8')).hexdigest()[:8]
        return f"AMCB_{hash_hex}"

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
            "Ciudad de México, CDMX - Todas las Terminales",
            "Guadalajara, JAL - Todas las Terminales",
            "Monterrey, NL - Todas las Terminales",
            "Puebla, PUE - Todas las terminales",
            "León, GTO - Todas las Terminales",
            "Cancun, QR (Todas las terminales)",
            "Acapulco, GRO - Todas las Terminales",
            "Veracruz, VER - Todas las terminales",
            "Mazatlán, SIN - Todas las terminales",
            "Puerto Vallarta, JAL - Todas las Terminales",
        ]
        return list(itertools.permutations(locations, 2))

    def define_dates(self):
        """Generate the days into the future starting from today"""
        today = datetime.today()
        return [today + timedelta(days=i) for i in range(10)]

    def insert_origin(self, origin):
        """Locate and fill origin field in the browser URL"""
        try:
            origin_field = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[formcontrolname='departure'].d-md-block")
            ))
            origin_field.clear()
            origin_field.send_keys(origin[:9])
            time.sleep(1)
            
            # Click the matching suggestion
            suggestion = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.dropdown div.option.ng-star-inserted")
            ))
            suggestion.click()
            print("Origin inserted...")
            time.sleep(3)
        except Exception as e:
            print(f"Error inserting origin...")
            self.logger.error(f"Error inserting origin '{origin}': {e}", exc_info=True)
            raise

    def insert_destination(self, destination):
        """Locate and fill destination field in the browser URL"""
        try: 
            
            destination_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[formcontrolname='arrival'].d-md-block")
                ))
            destination_field.clear()
            destination_field.send_keys(destination[:9])
            time.sleep(1)

            # Click the matching suggestion
            suggestion = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.dropdown.to div.option.ng-star-inserted")
            ))
            suggestion.click()
            print("Destination inserted...")
            time.sleep(3)
        except Exception as e:
            print(f"Error inserting destination...")
            self.logger.error(f"Error inserting destination '{destination}': {e}", exc_info=True)
            raise      

    def open_date_picker(self):
        """Locate and interact with DatePicker (opens the date picker first)"""
        try: 
            date_field = self.wait.until(EC.presence_of_element_located((By.ID, "departureDate")))
            date_field.click()
            time.sleep(3)
        except Exception as e: 
            print(f"Error opening date picker...")
            self.logger.error(f"Error opening date picker: {e}", exc_info=True)
            raise

    def insert_date(self, travel_date):
        """Insert the travel date in the format expected by the date picker"""
        try:
            # Wait for the datepicker to be visible
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ngb-datepicker")
            ))

            # Navigate to the correct month/year using the dropdowns
            month_select = self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='Select month']")
            month_select.send_keys(str(travel_date.month))
            time.sleep(1)

            year_select = self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='Select year']")
            year_select.send_keys(str(travel_date.year))
            time.sleep(1)

            # Click the day using aria-label format: d-M-yyyy
            date_label = f"{travel_date.day}-{travel_date.month}-{travel_date.year}"
            day_element = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f"div.ngb-dp-day[aria-label='{date_label}']:not(.disabled)")
            ))
            day_element.click()
            print(f"Date inserted...")
            time.sleep(3)
        except Exception as e:
            print(f"Error inserting the date...")
            self.logger.error(f"Error inserting the date, error: ({e})", exc_info=True)
            raise

    def submit_search_button(self):
        """Submit form clicking the submit button"""
        try: 
            #submit_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "search-widget-button")))

            submit_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.btn_purple")
            ))
            submit_button.click()
            print("Search form submitted...")
            time.sleep(10)
        except Exception as e: 
            print(f"Error submitting search form...")
            self.logger.error(f"Error submitting search form: {e}", exc_info=True)
            raise

    def get_containers(self, travel_date, general_origin):
        """Fetch and parse trip containers, extracting the relevant information"""
        try:
            trip_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.detail-wrap")
            scraping_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trips_data = []
            print(f"Found {len(trip_containers)} trip containers")
        except Exception as e:
            print(f"Error finding container elements...")
            self.logger.error(f"Error finding container elements: {e}", exc_info=True)
            raise

        for trip in trip_containers:
            try:
                # Bus company
                bus_company = trip.find_element(By.CSS_SELECTOR, "span.title").text.strip()

                # Developers use airport in the div name for some reason 
                # Departure: first name block (not .arrival)
                departure_block = trip.find_element(By.CSS_SELECTOR, "div.airport-name:not(.arrival)")
                departure_time = departure_block.find_element(By.TAG_NAME, "h4").text.strip()
                origin_terminal = departure_block.find_element(By.TAG_NAME, "h6").text.strip()

                # Arrival: airport-name with .arrival class
                arrival_block = trip.find_element(By.CSS_SELECTOR, "div.airport-name.arrival")
                arrival_time = arrival_block.find_element(By.TAG_NAME, "h4").text.strip()
                destination_terminal = arrival_block.find_element(By.TAG_NAME, "h6").text.strip()

                # Duration
                duration = trip.find_element(By.CSS_SELECTOR, "div.stop").text.split("\n")[0].strip()

                # Price
                try:
                    price = trip.find_element(By.CSS_SELECTOR, "span.price").text.strip()
                except:
                    price = "N/A"

                # Seats available
                try:
                    seats_text = trip.find_element(By.CSS_SELECTOR, "div.remaining-seats span").text.strip()
                    seats = seats_text.split(" ")[0] if seats_text else "N/A"
                except:
                    seats = "N/A"

                trips_data.append({
                    "Origin General": general_origin.split(",")[0],
                    "Bus Company": bus_company,
                    "Origin": origin_terminal,
                    "Destination": destination_terminal,
                    "Duration": duration,
                    "Departure Time": departure_time,
                    "Arrival Time": arrival_time,
                    "Price": price,
                    "Seats Available": seats,
                    "Travel Date": travel_date.strftime("%Y-%m-%d"),
                    "Scraping Date": scraping_date,
                    "id": self.generate_trip_id(origin_terminal, destination_terminal, departure_time, arrival_time, travel_date.strftime("%Y-%m-%d"), scraping_date)
                })
            except Exception as e:
                self.logger.error(f"Error in the trip containers: {e}", exc_info=True)
                continue

        return trips_data

    def export_excel(self, path_out, trips_data, origin, destination, travel_date):
        """Export trips data to a unique Excel file for each route-date combination"""
        date_str = travel_date.strftime("%Y-%m-%d")
        origin_safe = origin.replace(", ", "_").replace(" ", "_")
        dest_safe = destination.replace(", ", "_").replace(" ", "_")
        filename = f"{path_out}clickBus_trips_{origin_safe}_to_{dest_safe}_{date_str[:12]}.xlsx"

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
            print("No Excel files to concatenate.")
            return

        try: 
            all_dfs = [pd.read_excel(file, engine='openpyxl') for file in output_files]
            combined_df = pd.concat(all_dfs, ignore_index=True)
            final_output = f"{path_out}clickBus_trips_combined.xlsx"
            print(f"Data with duplicates: {combined_df.shape}")
            combined_df.drop_duplicates(subset=['id'], inplace=True) # Drop duplicated IDs (since we don't have more data)
            combined_df.to_excel(final_output, index=False, engine='openpyxl')
            print(f"Data without duplicates: {combined_df.shape}")
            print(f"Concatenated {len(output_files)} files into {final_output}")
        except Exception as e: 
            print("Error concatenating all files...")
            self.logger.error(f"Error concatenating all files: {e}", exc_info=True)

if __name__ == "__main__":

    scraper = ClickbusScraper()
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
                print(f"Error scraping {origin} to {destination} on {travel_date.strftime('%Y-%m-%d')}: {e}")
            finally:
                scraper.close_browser()
                time.sleep(10)

    scraper.concatenate_excels(path_out, output_files)
