# Reproducible workflow

This document walks through the full pipeline end to end, from installing the
package to producing the final maps. The pipeline has two stages:

1. **Data extraction (Python, this package):** collect bus routes and hotel
   coordinates into standardized spreadsheets.
2. **Spatial analysis (R, in `post-processing/`):** turn those datasets into an
   origin–destination (OD) flow map and hotel kernel-density maps.

Stage 2 is not part of the installable package; it is included to document the
complete research workflow.

---

## Stage 1 — Data extraction

### 1. Install

```bash
python -m pip install "git+https://github.com/ivanierruk/movilidadForanea.git@v2.0.0"
```

Google Chrome must be installed on the system (see the README requirements).

### 2. Configure

Copy the example configuration and edit it:

```bash
cp examples/config.example.yaml config.yaml
```

For a **reproducible** run, set explicit dates (`start_date`, `checkin_date`)
rather than the special value `"today"`. An explicit date lets anyone repeat the
exact query later; `"today"` is a convenience for routine use, but makes the
query non-deterministic because it depends on the day it is run.

City names must be spelled as each platform expects them (see the README note on
platform-specific naming).

### 3. Run

```bash
# Everything (the four bus platforms and Booking), sequentially
movilidad-foranea all --config config.yaml

# Or one group / one platform at a time
movilidad-foranea mobility --config config.yaml
movilidad-foranea mobility --platform ado --config config.yaml
movilidad-foranea hotels --config config.yaml
```

Runs are sequential by design, so a large run (many city pairs × dates) takes
time. Each query waits for results to render; if none appear, a warning is
written to the platform's log rather than silently reporting "no trips".

### 4. Outputs

Results are written under `output/<platform>/`:

- per route/date files (`*.xlsx`),
- a consolidated, de-duplicated file in **both** `*_combined.xlsx` and
  `*_combined.csv`,
- a `scraping_errors_<platform>.log` with any warnings/errors.

The CSV combined file is the recommended input for the analysis stage.

---

## Stage 2 — Spatial analysis (R)

The R scripts live in `post-processing/` and reproduce the maps used in the
research project.

### Inputs required by the R scripts

- The consolidated bus datasets (ADO, Omnibus, ClickBus, BusBud) and the Booking
  dataset produced in Stage 1.
- `ciudades.csv` — city coordinates used to place OD flows and to anchor the
  maps (provided in `post-processing/`).
- `contorno_pais/` — the Mexico boundary shapefile used to crop the maps
  (provided in `post-processing/`).

### Column mapping (manual preparation step)

The R scripts expect a cleaned, renamed set of columns. Before running them, the
extracted columns are renamed to match the names used in R, and the unused
`Day Offset` and `Price` columns are removed. The mapping is:

| Extracted column | Column used in R |
|------------------|------------------|
| Origin General   | ori_gral         |
| Origin           | origen           |
| Destination      | destino          |
| Day Offset       | (removed)        |
| Departure Time   | salida           |
| Arrival Time     | llegada          |
| Price            | (removed)        |
| Travel Date      | fecha_viaje      |
| Scraping Date    | scraping         |
| id               | id               |

> This renaming is currently a manual step; it is documented here so the full
> workflow is reproducible. Automating it is a candidate for future work.

### Scripts

- `interurban_mobility_flows.R` — integrates the four bus datasets, standardizes
  terminals into city keys, builds the OD matrix, and produces
  `flow_cities.jpg` (line thickness = number of available trips).
- `hotel_kernel_analysis.R` — runs kernel density estimation (KDE) on the Booking
  coordinates and produces `local_kernel.jpg` (sigma = 30 km) and
  `regional_kernel.jpg` (sigma = 60 km).

---

## Reproducibility notes

- Every extracted row records its own `Travel Date` and `Scraping Date`, so a
  dataset documents exactly when it was collected.
- Because the data comes from live commercial websites, re-running on a different
  day will not reproduce the same rows (availability and prices change). Use the
  archived dataset (and its DOI) to reproduce a specific analysis; use the code
  to collect a fresh dataset.
- Web sources are fragile: platforms change their markup, add bot protection, or
  vary their layout (see the README limitations). A scraper that works today may
  need updating later.
