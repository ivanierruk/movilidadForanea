# Intercity mobility and accommodation in Mexico: from web platforms to spatial data

**`movilidad-foranea` — Reproducible extraction of intercity bus routes and hotel geolocation in Mexico.**

`movilidad-foranea` is an installable Python package that collects intercity
bus-travel information (schedules, terminals, fares) from four bus platforms and
georeferenced hotel coordinates from Booking.com, for a user-defined set of
cities and dates. It was developed as part of a research project at
**UNAM – IIEc** (Universidad Nacional Autónoma de México, Instituto de
Investigaciones Económicas / National Autonomous University of Mexico, Institute
for Economic Research).

This package is the reusable, installable successor to the original collection of
standalone scripts: the scraping logic is the same, but the cities, dates and
output location are now supplied through a configuration file instead of being
edited inside the source code, and every scraper is available through a single
command-line interface (CLI).

---

## Scientific purpose

Studying interurban mobility and the spatial distribution of tourism
infrastructure in Mexico requires harmonized, reproducible data on **how people
can travel between cities** and **where lodging is concentrated**. Such data is
not published as a single open dataset: it is scattered across commercial
booking platforms, each with its own interface, city-naming conventions and page
structure.

This software addresses that gap by:

- collecting bus-route availability between city pairs from four platforms
  (ADO, Omnibus de México, ClickBus and BusBud),
- collecting georeferenced hotel locations from Booking.com, and
- producing standardized spreadsheets whose column names are aligned across
  platforms, ready for downstream origin–destination (OD) and spatial analysis.

The resulting datasets support the construction of interurban travel-flow
matrices and kernel-density estimates of accommodation supply (see
*Post-processing* below).

---

## Data collected

| Module | Platform | Data collected |
|--------|----------|----------------|
| `mobility.ado` | [ADO](https://www.ado.com.mx/) | Bus routes: south, southeast & Gulf of Mexico |
| `mobility.omnibus` | [Omnibus de México](https://www.odm.com.mx/) | Bus routes: north, Bajío & central Mexico |
| `mobility.clickbus` | [ClickBus](https://www.clickbus.com.mx/) | Bus routes: multi-carrier aggregator |
| `mobility.busbud` | [BusBud](https://www.busbud.com/) | Bus routes: multi-carrier aggregator |
| `accommodation.booking` | [Booking.com](https://www.booking.com/) | Hotel coordinates |

---

## Requirements

- **Python 3.10 or newer**
- **Google Chrome** installed on the system. Selenium automates a real Chrome
  instance; it does not emulate one. ChromeDriver itself is downloaded and
  managed automatically at runtime by `webdriver-manager`.

---

## Installation

The package can be installed directly from GitHub, without being published to
PyPI (the Python Package Index). Install a specific released version by tag:

```bash
python -m pip install "git+https://github.com/ivanierruk/movilidadForanea.git@v2.0.0"
```

### Development install

To work on the code itself, clone the repository and install it in *editable*
mode (`-e`), so that changes to the source take effect without reinstalling:

```bash
git clone https://github.com/ivanierruk/movilidadForanea.git
cd movilidadForanea
python -m pip install -e .
```

---

## Configuration

All run parameters live in a single YAML file; the source code is never edited
to change cities, dates or the output location. Copy the provided example and
adapt it:

```bash
cp examples/config.example.yaml config.yaml
```

A minimal `config.yaml` looks like this:

```yaml
# Directory where the output .xlsx files will be saved.
output_dir: "./output"

# --- Bus route extraction (mobility) ---
mobility:
  headless: false            # false = Chrome window is visible; true = hidden
  start_date: "2026-11-01"   # first travel date to query (format YYYY-MM-DD)
  n_days: 7                  # number of consecutive days to query from that date
  routes:                    # (origin, destination) pairs
    - [ "Ciudad de México, CDMX", "Acapulco" ]
    - [ "Ciudad de México, CDMX", "Puebla" ]

# --- Hotel extraction (accommodation / Booking) ---
accommodation:
  headless: false
  checkin_date: "2026-11-01" # check-in date
  stay_nights: 5             # length of stay in nights
  cities:                    # list of cities to query
    - "Cancún"
    - "Acapulco"
```

> **Important:** city names differ across platforms for the same location
> (for example, `"Ciudad de México, CDMX"` on ADO vs.
> `"Ciudad de Mexico, México, México"` on BusBud). The exact spelling each
> platform expects must be verified manually when configuring a new set of
> cities.

---

## Usage

Installing the package registers a `movilidad-foranea` command. Every subcommand
takes a `--config` pointing at your YAML file:

```bash
# Run every scraper (the four bus platforms and Booking), in sequence
movilidad-foranea all --config config.yaml

# Run all four bus platforms
movilidad-foranea mobility --config config.yaml

# Run a single bus platform
movilidad-foranea mobility --platform ado --config config.yaml

# Run only the hotel (Booking) scraper
movilidad-foranea hotels --config config.yaml
```

Scrapers run **sequentially, never in parallel**. Each one drives its own Chrome
session, and running several at once would place an unnecessarily heavy load on
the target sites and increase the risk of being blocked. The sequential design,
together with the built-in waits between requests, is a deliberate choice to
keep the tool respectful of the consulted servers.

By default Chrome runs in **visible (non-headless) mode**: a browser window opens
and the extraction can be observed in real time. Set `headless: true` in the
configuration to run without a visible window.

### Minimal reproducible example

```bash
# 1. Install the package
python -m pip install "git+https://github.com/ivanierruk/movilidadForanea.git@v2.0.0"

# 2. Create a configuration file
cp examples/config.example.yaml config.yaml
# (edit config.yaml: set output_dir, the routes and the dates you want)

# 3. Run a single, small extraction (one bus platform)
movilidad-foranea mobility --platform ado --config config.yaml
```

After the run finishes, the standardized results are in
`output/ado/ado_trips_combined.xlsx`.

---

## Inputs

- A **`config.yaml`** file (see *Configuration*) specifying the output directory,
  the origin–destination city pairs and date range for bus routes, and the
  cities, check-in date and length of stay for hotels.
- A working **Google Chrome** installation.

---

## Outputs

Each platform writes into its own subdirectory of `output_dir`, so results never
mix between platforms:

```
output/
├── ado/
│   ├── ado_trips_<origin>_to_<destination>_<date>.xlsx   # one file per route-date
│   ├── ado_trips_combined.xlsx                           # consolidated, de-duplicated
│   └── scraping_errors_ADO.log                           # warnings and errors
├── omnibus/
├── clickbus/
├── busbud/
└── booking/
    ├── Booking_trips_to_<city>_<date>.xlsx
    └── Booking_trips_combined.xlsx
```

- **Per route-date / per city files** contain the raw extracted rows.
- **`*_combined.xlsx`** files consolidate all of a platform's results for the run
  and drop duplicate trips/properties by a hashed identifier.
- **`scraping_errors_*.log`** records failed selectors, captured exceptions and
  export errors. Progress messages are printed to the console during execution.

The bus-route datasets share standardized column names (`Origin General`,
`Origin`, `Destination`, `Departure Time`, `Arrival Time`, `Travel Date`,
`Scraping Date`, `id`, …) so they can be concatenated across platforms. The
Booking dataset contains property identifiers and `latitude` / `longitude`
coordinates.

---

## Post-processing (R, optional)

The `post-processing/` directory contains the downstream **R** analysis used in
the research project. It is **not** part of the installable Python package, but
is included to document the complete, reproducible workflow:

- `interurban_mobility_flows.R` — integrates the four bus datasets, standardizes
  terminals into city keys, builds an origin–destination (OD) matrix and maps
  interurban travel flows.
- `hotel_kernel_analysis.R` — performs kernel density estimation (KDE) on the
  Booking coordinates to map local and regional accommodation concentration.

---

## Limitations

- **Web-source fragility.** Each scraper depends on the current HTML structure
  of its platform. Interface changes (CSS selectors, element attributes,
  calendar components) may break extraction and require updating the
  corresponding module. This is inherent to web scraping and should be expected
  over time.
- **BusBud is blocked by anti-bot protection.** BusBud was scrapable when this 
  project began, but the site has since deployed Cloudflare bot management, 
  which detects the automated browser through its fingerprint and behaviour and 
  blocks access. The busbud module is retained and works where no such protection 
  is present, but automated extraction from BusBud is no longer reliable. This 
  is an example of the temporal fragility of web sources: a source that works 
  today may be gated tomorrow.
- **City naming is platform-specific.** The same city must often be written
  differently on each platform, and must be verified manually (see
  *Configuration*).
- **Google Chrome is an external dependency.** It must be installed separately;
  it is not part of the Python environment.
- **No parallel execution.** Scrapers run one at a time by design (see *Usage*).
  A full run over many city pairs and dates can therefore take a long time.
- **`selenium-wire` dependency.** The Booking scraper relies on `selenium-wire`
  to intercept GraphQL responses. Depending on the Python and operating-system
  environment, this dependency can occasionally require additional setup.
- **Not for commercial use.** This software is intended for academic research.
  It includes systematic wait times to avoid overloading the consulted servers
  and should be used responsibly and in accordance with each platform's terms.
---

## License

This project is licensed under the GNU General Public License v3.0
(GPL-3.0-only). See the [LICENSE](LICENSE) file for the full text.

---

## Citation

If you use this software in your research, please cite it. A machine-readable
citation is provided in [`CITATION.cff`](CITATION.cff), and an archived,
citable version is available via Zenodo (DOI to be added for the v2.0.0
release).

---

## Authors

- Reyes, Victor — UNAM, Instituto de Investigaciones Económicas (IIEc)
- Espinosa, Iván — UNAM, Instituto de Investigaciones Económicas (IIEc)
