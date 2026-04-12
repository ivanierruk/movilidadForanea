# Intercity Mobility & Hotel Geolocation — Web Scraping System

Automated data extraction system for intercity bus travel and hotel geolocation in Mexico. The system collects route information (schedules, fares, terminals) from four bus platforms and georeferenced hotel coordinates from Booking.com.

Developed as part of a research project at **UNAM - IIEc** (Instituto de Investigaciones Económicas).

## Overview

The system consists of five independent Python scripts, one per platform:

| Script | Platform | Data collected |
|---|---|---|
| `ado_scraper.py` | [ADO](https://www.ado.com.mx/) | Bus routes: south, southeast & Gulf of Mexico |
| `omnibus_scraper.py` | [Omnibus de México](https://www.omnibus.com.mx/) | Bus routes: north, Bajío & central Mexico |
| `clickbus_scraper.py` | [ClickBus](https://www.clickbus.com.mx/) | Bus routes: multi-carrier aggregator |
| `busbud_scraper.py` | [BusBud](https://www.busbud.com/) | Bus routes: multi-carrier aggregator |
| `booking_scraper.py` | [Booking.com](https://www.booking.com/) | Hotel coordinates via GraphQL API interception |

Each script can be executed independently, in any order, and at any time.

## Requirements

- **Python 3.10** (see `.python-version`)
- **Google Chrome** installed on your system (Selenium automates a real browser instance; it does not emulate one)
- ChromeDriver is managed automatically by `webdriver-manager` at runtime

## Installation

### Option A: venv (recommended)

```bash
# Clone the repository
git clone https://github.com/<username>/movilidadForanea.git
cd movilidadForanea

# Create virtual environment with Python 3.10
python3.10 -m venv venv

# Activate the environment
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option B: uv (alternative)

```bash
# Clone the repository
git clone https://github.com/<username>/movilidadForanea.git
cd movilidadForanea

# Create virtual environment (uv downloads Python 3.10 automatically if needed)
uv venv venv --python=python3.10

# Activate the environment
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

> **Note:** On Windows and Debian-based distributions, `uv` may require manual installation of `setuptools` and `wheel` before installing the project dependencies:
> ```bash
> uv pip install setuptools wheel
> uv pip install -r requirements.txt
> ```

## Configuration

Before running any script, set the output directory by editing the `path_out` variable at the top of each script file:

```python
path_out = "/your/desired/output/path/"
```

The output directory must exist before execution — the scripts do not create it automatically. The `output/` folder in this repository is provided for this purpose.

### Customizing cities and dates

Each script defines its own list of cities and date range internally:

- **Cities:** Edit the `define_routes()` method to modify the list of origin-destination cities. Note that city names differ across platforms for the same location (e.g., "Ciudad de México, CDMX" in ADO vs. "Ciudad de Mexico, México, México" in BusBud).
- **Dates:** Edit the `define_dates()` method to adjust the date range. Mobility scripts generate consecutive dates starting from the execution day. The Booking script uses a single check-in date with a fixed 5-day stay.

## Usage

Activate the virtual environment and run any script from the terminal:

```bash
# Activate environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Run a scraper
python scripts/ado_scraper.py
python scripts/busbud_scraper.py
python scripts/clickbus_scraper.py
python scripts/omnibus_scraper.py
python scripts/booking_scraper.py
```

Scripts run in **visible (non-headless) mode** — a Chrome window will open and you can observe the extraction process in real time. Each script generates individual `.xlsx` files per query and a consolidated file per platform upon completion.

## Output

### Mobility module (ADO, Omnibus, ClickBus, BusBud)

Each consolidated file contains trip records with the following core fields:

| Field | Description |
|---|---|
| `Origin General` | Control field: query city from the input list |
| `Origin` | Origin city or terminal as shown on the platform |
| `Destination` | Destination city or terminal as shown on the platform |
| `Departure Time` | Departure time |
| `Arrival Time` | Arrival time |
| `Price` | Fare for the queried date |
| `Travel Date` | Travel date (YYYY-MM-DD) |
| `Scraping Date` | Extraction timestamp |
| `id` | Unique identifier (MD5 hash) |

Additional fields by platform: ADO includes `Day Offset`; ClickBus includes `Bus Company`, `Duration`, and `Seats Available`.

### Hotel module (Booking.com)

| Field | Description |
|---|---|
| `id` | Property ID from Booking.com API |
| `pageName` | Property page name |
| `address` | Property address |
| `countryCode` | Country code |
| `longitude` | Longitude coordinate |
| `latitude` | Latitude coordinate |
| `checkIn` | Check-in date |
| `checkOut` | Check-out date |
| `query_date` | Extraction timestamp |
| `destination` | Queried destination city |

## Error Logging

Each script generates a `.log` file in the output directory with warnings and errors (failed selectors, captured exceptions, export errors). Progress messages are printed to the console during execution.

## Important Notes

- Scripts include systematic wait times between requests to avoid overloading the consulted servers.
- The system depends on the HTML structure of each platform. Interface changes (CSS selectors, element attributes, calendar components) may require updating the scripts.
- City naming conventions differ across platforms and must be verified manually when configuring a new set of cities.
- Google Chrome must be installed independently — it is not part of the Python environment.

## Project Structure

```
.
├── .gitignore
├── .python-version
├── LICENSE
├── README.md
├── requirements.txt
├── output/
│   └── .gitkeep
└── scripts/
    ├── ado_scraper.py
    ├── busbud_scraper.py
    ├── clickbus_scraper.py
    ├── omnibus_scraper.py
    └── booking_scraper.py
```

## License

See [LICENSE](LICENSE) for details.

## Author

John Do — UNAM IIEc
