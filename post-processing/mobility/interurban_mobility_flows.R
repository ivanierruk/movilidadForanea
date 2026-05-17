############################################################
#### MOBILITY DATA PROCESSING
############################################################


############################################################
#### REQUIRED PACKAGES
############################################################

install.packages("readxl")
install.packages("tidyverse")
install.packages("sf")

library(readxl)
library(tidyverse)
library(sf)


############################################################
#### MOBILITY DATA INTEGRATION
############################################################

# Load mobility datasets and convert them to data frames
# Bus operators: ADO (ado) and Omnibus de Mexico (odm)
# Aggregator platforms: ClickBus (cbs) and budBus (bds)

ado <- read_excel("ado.xlsx")
ado <- as.data.frame(ado)
head(ado)

bds <- read_excel("budbus.xlsx")
bds <- as.data.frame(bds)
head(bds)

cbs <- read_excel("clickbus.xlsx")
cbs <- as.data.frame(cbs)
head(cbs)

odm <- read_excel("omnibus.xlsx")
odm <- as.data.frame(odm)
head(odm)

# Check variable names across data sets 
names(ado)
names(bds)
names(cbs)
names(odm)

# Add a variable to identify the scraping source
ado$source <- "ado"
bds$source <- "budbus"
cbs$source <- "clickbus"
odm$source <- "odm"

# Merge all mobility data sets into a single data frame
trips <- rbind(ado, bds, cbs, odm)

head(trips)

# Check the number of observations by scraping source
table(trips$source)


############################################################
#### MOBILITY DATA CLEANING AND STANDARDIZATION
############################################################

# Remove unnecessary variables
trips <- trips[, -c(4:6)]

head(trips)

# Keep only the date from the scraping timestamp
trips$scraping <- as.Date(trips$scraping)

head(trips)

# Review origin city labels before standardization
table(trips$ori_gral)

# Create a new variable for standardized origin city keys
trips$ori_city <- NA


# Acapulco
trips$ori_city[grepl("Acapulco", trips$ori_gral)] <- "aca"
table(trips$ori_gral[trips$ori_city == "aca"])

# Cancún
trips$ori_city[grepl("Cancún|Cancun", trips$ori_gral)] <- "can"
table(trips$ori_gral[trips$ori_city == "can"])

# Mexico City
trips$ori_city[grepl("Mexico|México|CDMX", trips$ori_gral)] <- "mex"
table(trips$ori_gral[trips$ori_city == "mex"])

# Mazatlán
trips$ori_city[grepl("Mazatlan|Mazatlán", trips$ori_gral)] <- "mzt"
table(trips$ori_gral[trips$ori_city == "mzt"])

# Guadalajara
trips$ori_city[grepl("Guadalajara", trips$ori_gral)] <- "gdl"
table(trips$ori_gral[trips$ori_city == "gdl"])

# León
trips$ori_city[grepl("Leon|León", trips$ori_gral)] <- "leo"
table(trips$ori_gral[trips$ori_city == "leo"])

# Monterrey
trips$ori_city[grepl("Monterrey", trips$ori_gral)] <- "mty"
table(trips$ori_gral[trips$ori_city == "mty"])

# Puebla
trips$ori_city[grepl("Puebla", trips$ori_gral)] <- "pue"
table(trips$ori_gral[trips$ori_city == "pue"])

# Puerto Vallarta
trips$ori_city[grepl("Vallarta", trips$ori_gral)] <- "pva"
table(trips$ori_gral[trips$ori_city == "pva"])

# Veracruz
trips$ori_city[grepl("Veracruz", trips$ori_gral)] <- "ver"
table(trips$ori_gral[trips$ori_city == "ver"])

# Review standardized origin city keys
table(trips$ori_city)
table(trips$ori_city, useNA = "ifany")

# Remove records with non-classifiable or ambiguous origin cities
trips <- trips[!is.na(trips$ori_city), ]

table(trips$ori_city, useNA = "ifany")

head(trips)


# Create a variable for standardized destination city keys
# Destination labels correspond to bus terminals rather than cities;
# therefore, destination terminal names are reviewed and coded manually
trips$dest_city <- NA

# Review destination terminal labels before coding
table(trips$destino, useNA = "ifany")

# Create a frequency table of destination terminals
dest_table <- table(trips$destino, useNA = "ifany")

# Inspect destination terminal names to identify which entries correspond
# to each selected city and group them by index ranges
names(dest_table)


# Acapulco (destination terminal names 1 to 24)
trips$dest_city[trips$destino %in% names(dest_table)[1:24]] <- "aca"

# Mexico City (destination terminal names 25 to 30)
trips$dest_city[trips$destino %in% names(dest_table)[25:30]] <- "mex"

# Cancún (destination terminal names 31 to 32)
trips$dest_city[trips$destino %in% names(dest_table)[31:32]] <- "can"

# Puebla (destination terminal names 33 to 34)
trips$dest_city[trips$destino %in% names(dest_table)[33:34]] <- "pue"

# Mexico City (destination terminal name 35)
trips$dest_city[trips$destino %in% names(dest_table)[35]] <- "mex"

# Cancún (destination terminal name 36)
trips$dest_city[trips$destino %in% names(dest_table)[36]] <- "can"

# Guadalajara (destination terminal name 37)
trips$dest_city[trips$destino %in% names(dest_table)[37]] <- "gdl"

# Mazatlán (destination terminal name 38)
trips$dest_city[trips$destino %in% names(dest_table)[38]] <- "mzt"

# Monterrey (destination terminal names 39)
trips$dest_city[trips$destino %in% names(dest_table)[39]] <- "mty"

# Veracruz (destination terminal names 40)
trips$dest_city[trips$destino %in% names(dest_table)[40]] <- "ver"

# Mexico City (destination terminal names 41 to 83)
trips$dest_city[trips$destino %in% names(dest_table)[41:83]] <- "mex"

# Mazatlán (destination terminal names 84 to 91)
trips$dest_city[trips$destino %in% names(dest_table)[84:91]] <- "mzt"

# Acapulco (destination terminal name 92)
trips$dest_city[trips$destino %in% names(dest_table)[92]] <- "aca"

# Mexico City (destination terminal name 93)
trips$dest_city[trips$destino %in% names(dest_table)[93]] <- "mex"

# Guadalajara (destination terminal names 94 to 120)
trips$dest_city[trips$destino %in% names(dest_table)[94:120]] <- "gdl"

# Mexico City (destination terminal name 121)
trips$dest_city[trips$destino %in% names(dest_table)[121]] <- "mex"

# León (destination terminal names 122 to 132)
trips$dest_city[trips$destino %in% names(dest_table)[122:132]] <- "leo"

# Mazatlán (destination terminal names 133 to 134)
trips$dest_city[trips$destino %in% names(dest_table)[133:134]] <- "mzt"

# Mexico City (destination terminal names 135 to 137)
trips$dest_city[trips$destino %in% names(dest_table)[135:137]] <- "mex"

# Monterrey (destination terminal names 138 to 145)
trips$dest_city[trips$destino %in% names(dest_table)[138:145]] <- "mty"

# Puebla (destination terminal names 146 to 153)
trips$dest_city[trips$destino %in% names(dest_table)[146:153]] <- "pue"

# Puerto Vallarta (destination terminal names 154 to 161)
trips$dest_city[trips$destino %in% names(dest_table)[154:161]] <- "pva"

# Mexico City (destination terminal names 162 to 167)
trips$dest_city[trips$destino %in% names(dest_table)[162:167]] <- "mex"

# Acapulco (destination terminal name 168)
trips$dest_city[trips$destino %in% names(dest_table)[168]] <- "aca"

# León (destination terminal name 169)
trips$dest_city[trips$destino %in% names(dest_table)[169]] <- "leo"

# Mexico City (destination terminal names 170 to 171)
trips$dest_city[trips$destino %in% names(dest_table)[170:171]] <- "mex"

# Entry 172 does not match any city included in the study

# Veracruz (destination terminal names 173 to 191)
trips$dest_city[trips$destino %in% names(dest_table)[173:191]] <- "ver"


# Remove records with non-classifiable or out-of-scope destination cities
trips <- trips[!is.na(trips$dest_city), ]

# Check standardized destination city keys
table(trips$dest_city, useNA = "ifany")

# Verify that no unclassified destination labels remain
table(trips$destino[is.na(trips$dest_city)], useNA = "ifany")

head(trips)


############################################################
#### ORIGIN–DESTINATION MATRIX
############################################################

# Create a simple frequency table between origin and destination city keys
od_table <- as.data.frame(table(trips$ori_city, trips$dest_city))

head(od_table)

# Rename columns for clarity
names(od_table) <- c("ori_city", "dest_city", "n_trips")

head(od_table)

# Remove city pairs with no recorded trips
od_table <- od_table[od_table$n_trips > 0, ]

head(od_table)

# Check the number of observed links by origin and destination
table(od_table$ori_city)
table(od_table$dest_city)



############################################################
#### ADD CITY COORDINATES TO THE OD MATRIX
############################################################

# Load selected city coordinates
city_coords_raw <- read.csv("ciudades.csv",
  fileEncoding = "latin1",
  stringsAsFactors = FALSE
)

head(city_coords_raw)

# Select and rename coordinate variables
city_coords <- city_coords_raw %>%
  select(Clave, latitud, longitud) %>%
  rename(
    city_key = Clave,
    lat = latitud,
    lon = longitud
  )

head(city_coords)

# Add origin city coordinates to the OD matrix
od_coords <- od_table %>%
  left_join(city_coords, by = c("ori_city" = "city_key")) %>%
  rename(
    lat_ori = lat,
    lon_ori = lon
  )

head(od_coords)

# Add destination city coordinates to the OD matrix
od_coords <- od_coords %>%
  left_join(city_coords, by = c("dest_city" = "city_key")) %>%
  rename(
    lat_dest = lat,
    lon_dest = lon
  )

head(od_coords)


############################################################
#### SPATIALIZE ORIGIN–DESTINATION FLOWS
############################################################

# Build line geometries from origin and destination coordinates
od_lines <- lapply(1:nrow(od_coords), function(i) {
  st_linestring(matrix(
    c(od_coords$lon_ori[i],  od_coords$lat_ori[i],
      od_coords$lon_dest[i], od_coords$lat_dest[i]),
    ncol = 2,
    byrow = TRUE
  ))
})

# Convert the list of lines into an sf object
od_sf <- st_sf(
  od_coords,
  geometry = st_sfc(od_lines, crs = 4326)
)

# Visual check of the OD spatial object
od_sf
plot(st_geometry(od_sf))

# Load the national boundary shapefile
mex <- st_read("contorno_pais/Contorno_Mexico.shp")

# Transform OD flows to the same CRS as the base map
od_sf_proj <- st_transform(od_sf, st_crs(mex))


############################################################
#### PRELIMINARY OD FLOW MAP
############################################################

# Scale the number of trips to use as line width in the map
od_sf_proj$lwd <- 0.5 + sqrt(od_sf_proj$n_trips) / max(sqrt(od_sf_proj$n_trips)) * 5

# Draw national boundary
plot(st_geometry(mex),
     col = "grey90",
     border = "grey40",
     axes = FALSE)

# Add OD flows with proportional line width
plot(st_geometry(od_sf_proj),
     add = TRUE,
     col = rgb(0.1, 0.2, 0.7, 0.5),
     lwd = od_sf_proj$lwd)

# Add map frame
box(which = "plot", lwd = 1.2)

# Add axes
axis(1, lwd = 0.8, cex.axis = 0.8)
axis(2, lwd = 0.8, cex.axis = 0.8)

# Add map title
title("Interurban travel flows between selected cities in Mexico",
      line = -1.5)

# Add preliminary legend
legend("bottomleft",
       inset = c(0.15, 0.15),
       legend = c("Low flows", "Medium", "High flows"),
       lwd = c(1, 3, 5),
       col = rgb(0.1, 0.2, 0.7, 0.5),
       bg = "white",
       box.col = "grey70",
       cex = 1)


############################################################
#### FINAL OD FLOW MAP
############################################################

# Function to draw the final OD flow map
map_od_flows <- function() {
  
  # Draw national boundary as base map
  plot(st_geometry(mex),
       col = "#FFFDF6",
       border = "grey30",
       axes = FALSE)
  
  # Add OD flows with color and transparency
  plot(st_geometry(od_sf_proj),
       add = TRUE,
       col = rgb(0.05, 0.25, 0.55, 0.55),
       lwd = od_sf_proj$lwd)
  
  # Add map frame
  box(which = "plot", lwd = 1.2)
  
  # Add x-axis
  axis(1,
       at = c(1000000, 2000000, 3000000, 4000000),
       labels = c("1,000,000", "2,000,000", "3,000,000", "4,000,000"),
       lwd = 0.8,
       cex.axis = 0.8,
       las = 1)
  
  # Add y-axis
  axis(2,
       at = c(500000, 1000000, 1500000, 2000000),
       labels = c("500,000", "1,000,000", "1,500,000", "2,000,000"),
       lwd = 0.8,
       cex.axis = 0.8,
       las = 1)
  
  # Add map title
  title("Interurban travel flows between selected cities in Mexico",
        line = -1.5)
  
  # Draw background box for the legend
  rect(xleft = 700000, ybottom = 430000,
       xright = 1300000, ytop = 900000,
       col = "grey95", border = "grey80")
  
  # Add legend without its default box
  legend(x = 650000, y = 1000000,
         title = "Flows",
         legend = c("Low", "Medium", "High"),
         lwd = c(1, 3, 5),
         col = rgb(0.05, 0.25, 0.55, 0.55),
         bty = "n",
         cex = 1,
         x.intersp = 0.8,
         y.intersp = 0.8)
}


############################################################
#### CITY LABELS FOR OD FLOW MAP
############################################################

# Convert city coordinates into an sf point object
cities_sf <- st_as_sf(
  city_coords,
  coords = c("lon", "lat"),
  crs = 4326
)

# Transform city points to the same CRS as the OD flow map
cities_proj <- st_transform(cities_sf, st_crs(mex))

cities_proj

# Extract projected coordinates and city keys for manual label placement
flow_label_coords <- data.frame(
  city_key = city_coords$city_key,
  st_coordinates(cities_proj)
)

head(flow_label_coords)

# Extract coordinates by city
aca_crd <- flow_label_coords[flow_label_coords$city_key == "aca", ]
can_crd <- flow_label_coords[flow_label_coords$city_key == "can", ]
mex_crd <- flow_label_coords[flow_label_coords$city_key == "mex", ]
gdl_crd <- flow_label_coords[flow_label_coords$city_key == "gdl", ]
leo_crd <- flow_label_coords[flow_label_coords$city_key == "leo", ]
mzt_crd <- flow_label_coords[flow_label_coords$city_key == "mzt", ]
mty_crd <- flow_label_coords[flow_label_coords$city_key == "mty", ]
pue_crd <- flow_label_coords[flow_label_coords$city_key == "pue", ]
ver_crd <- flow_label_coords[flow_label_coords$city_key == "ver", ]
pva_crd <- flow_label_coords[flow_label_coords$city_key == "pva", ]

# Function to add manually adjusted city labels
add_flow_city_labels <- function() {
  
  text(aca_crd$X - 100000, aca_crd$Y, "Acapulco", cex = 1.1, col = "#2F6B3F")
  text(can_crd$X + 80000, can_crd$Y, "Cancún", cex = 1.1, col = "#2F6B3F")
  text(mex_crd$X - 110000, mex_crd$Y - 20000, "Mexico City", cex = 1.1, col = "#2F6B3F")
  text(gdl_crd$X - 80000, gdl_crd$Y - 60000, "Guadalajara", cex = 1.1, col = "#2F6B3F")
  text(leo_crd$X + 58000, leo_crd$Y + 20000, "León", cex = 1.1, col = "#2F6B3F")
  text(mzt_crd$X - 80000, mzt_crd$Y, "Mazatlán", cex = 1.1, col = "#2F6B3F")
  text(mty_crd$X, mty_crd$Y + 20000, "Monterrey", cex = 1.1, col = "#2F6B3F")
  text(pue_crd$X + 50000, pue_crd$Y - 28513, "Puebla", cex = 1.1, col = "#2F6B3F")
  text(ver_crd$X + 100000, ver_crd$Y - 12816, "Veracruz", cex = 1.1, col = "#2F6B3F")
  text(pva_crd$X - 200000, pva_crd$Y + 15000, "Puerto Vallarta", cex = 1.1, col = "#2F6B3F")
}

# Draw final OD flow map
par(bg = "#F4E7E1")
map_od_flows()
add_flow_city_labels()


############################################################
# Export settings can be adjusted according to visualization needs