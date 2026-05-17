############################################################
#### HOTEL DATA PROCESSING
############################################################


############################################################
#### REQUIRED PACKAGES
############################################################

install.packages("readxl")
install.packages("spatstat.geom")
install.packages("spatstat.explore")
install.packages("sf")
install.packages("terra")
install.packages("tidyverse")

library(readxl)
library(spatstat.geom)
library(spatstat.explore)
library(sf)
library(terra)
library(tidyverse)


############################################################
#### SELECTED CITIES AND BASE MAP
############################################################

# Load the selected cities dataset
cities <- read.csv(
  "ciudades.csv",
  fileEncoding = "latin1",
  stringsAsFactors = FALSE
)

head(cities)

# Convert the selected cities into an sf point object
cities_sf <- st_as_sf(
  cities,
  coords = c("longitud", "latitud"),
  crs = 4326
)

# Load the national boundary shapefile
mex <- st_read("contorno_pais/Contorno_Mexico.shp")

# Transform city points to the same CRS as the national boundary
cities_proj <- st_transform(cities_sf, st_crs(mex))

# Quick visual check of selected cities and national boundary
plot(st_geometry(mex),
     col = "grey90",
     border = "grey40")

plot(st_geometry(cities_proj),
     add = TRUE,
     pch = 16,
     col = "red",
     cex = 1.3)

text(st_coordinates(cities_proj),
     labels = cities_proj$Clave,
     pos = 4,
     cex = 0.9)


############################################################
#### HOTEL DATA CLEANING
############################################################

# Load hotel data and convert to data frame
hotels <- read_excel("Booking.xlsx")
head(hotels)

hotels <- as.data.frame(hotels)
head(hotels)
dim(hotels)

# Select and rename variables required for the analysis
hotels <- hotels %>%
  select(
    id,
    hotel_name = pageName,
    city = destination,
    longitude,
    latitude,
    query_date
  )

head(hotels)

# Check city labels in both data sets before re-coding
table(cities$Clave)
table(hotels$city)


# Re-code hotel city names using the standardized city keys
hotels$city <- recode(
  hotels$city,
  "Acapulco_Guerrero_Mexico" = "aca",
  "Cancún_México" = "can",
  "Guadalajara_Jalisco_Mexico" = "gdl",
  "León_Guanajuato_Mexico" = "leo",
  "Mazatlán_Sinaloa_Mexico" = "mzt",
  "Mexico_City_Mexico_DF_Mexico" = "mex",
  "Monterrey_Nuevo_León_Mexico" = "mty",
  "Puebla_State_of_Puebla_Mexico" = "pue",
  "Puerto_Vallarta_Jalisco_Mexico" = "pva",
  "Veracruz_Veracruz_Mexico" = "ver"
)

head(hotels)
table(hotels$city)

# Replace hyphens in hotel names with blank spaces
hotels$hotel_name <- gsub("-", " ", hotels$hotel_name)

head(hotels)

# Keep only the date from the scraping time
hotels$query_date <- as.Date(hotels$query_date)

head(hotels)


############################################################
#### HOTEL POINT PATTERN AND KERNEL DENSITY
############################################################

# Convert hotel records into an sf point object
hotels_sf <- st_as_sf(
  hotels,
  coords = c("longitude", "latitude"),
  crs = 4326
)

# Transform hotel points to the same CRS as the national boundary
hotels_proj <- st_transform(hotels_sf, st_crs(mex))

# Visual check of hotel locations
plot(st_geometry(mex), col = "grey90", border = "grey40")
plot(st_geometry(hotels_proj), add = TRUE, pch = 16, col = "blue", cex = 0.4)

# Extract projected coordinates
hotel_coords <- st_coordinates(hotels_proj)

# Define the observation window using the national boundary extent
mex_bbox <- st_bbox(mex)

hotel_ppp <- ppp(
  hotel_coords[, 1], hotel_coords[, 2],
  window = owin(
    c(mex_bbox["xmin"], mex_bbox["xmax"]),
    c(mex_bbox["ymin"], mex_bbox["ymax"])
  )
)

# Estimate local-scale kernel density to show city-level concentrations
kernel_local <- density(hotel_ppp, sigma = 30000, eps = 1500)

# Visual check of local-scale kernel density
plot(kernel_local)
plot(st_geometry(mex), add = TRUE, border = "grey40")

# Estimate regional-scale kernel density to show broader spatial corridors
kernel_regional <- density(hotel_ppp, sigma = 60000, eps = 1500)

# Visual check of regional-scale kernel density
plot(kernel_regional)
plot(st_geometry(mex), add = TRUE, border = "grey40")


############################################################
#### KERNEL DENSITY MAPS
############################################################

# Define color palette for kernel density maps
kernel_cols <- colorRampPalette(
  c("#FFFDF6",
    "#BDEDF2",
    "#5EC9D3",
    "#1FA3B8",
    "#0B6FA4",
    "#084081",
    "#081D58")
)(120)


############################################################
#### LOCAL-SCALE KERNEL DENSITY MAP
############################################################

# Convert the local-scale spat stat kernel density object to raster
kernel_local_raster <- rast(kernel_local)

# Convert the national boundary to Spat Vector format
mex_vect <- vect(mex)

# Check and assign CRS to the raster object
crs(kernel_local_raster)
crs(mex_vect)

crs(kernel_local_raster) <- crs(mex_vect)

crs(kernel_local_raster)

# Crop the local-scale kernel raster to the national boundary extent
kernel_local_crop <- crop(kernel_local_raster, mex_vect)

# Mask the raster to keep only the national territory
kernel_local_mask <- mask(kernel_local_crop, mex_vect)

# Preliminary local-scale kernel density map
plot(kernel_local_mask,
     col = kernel_cols,
     legend = FALSE,
     main = "")

# Add national boundary
plot(st_geometry(mex),
     add = TRUE,
     border = "grey30",
     lwd = 1)


############################################################
#### LOCAL-SCALE KERNEL DENSITY MAP STYLE
############################################################

# Function to draw the local-scale kernel density map
map_kernel_local <- function() {
  
  # Draw national boundary as base map
  plot(st_geometry(mex),
       col = "#FFFDF6",
       border = "grey30",
       axes = FALSE)
  
  # Add local-scale kernel density raster
  plot(kernel_local_mask,
       add = TRUE,
       col = kernel_cols,
       legend = FALSE,
       axes = FALSE)
  
  # Redraw national boundary
  plot(st_geometry(mex),
       add = TRUE,
       border = "grey30",
       lwd = 1)
  
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
  title("Local-scale kernel density of hotels in selected cities in Mexico",
        line = -1.5)
}


############################################################
#### CITY LABELS FOR KERNEL DENSITY MAPS
############################################################

# Extract projected coordinates and city keys for manual label placement
city_label_coords <- data.frame(
  city_key = cities_proj$Clave,
  st_coordinates(cities_proj)
)

head(city_label_coords)

# Extract coordinates by city
aca_crd <- city_label_coords[city_label_coords$city_key == "aca", ]
can_crd <- city_label_coords[city_label_coords$city_key == "can", ]
mex_crd <- city_label_coords[city_label_coords$city_key == "mex", ]
gdl_crd <- city_label_coords[city_label_coords$city_key == "gdl", ]
leo_crd <- city_label_coords[city_label_coords$city_key == "leo", ]
mzt_crd <- city_label_coords[city_label_coords$city_key == "mzt", ]
mty_crd <- city_label_coords[city_label_coords$city_key == "mty", ]
pue_crd <- city_label_coords[city_label_coords$city_key == "pue", ]
ver_crd <- city_label_coords[city_label_coords$city_key == "ver", ]
pva_crd <- city_label_coords[city_label_coords$city_key == "pva", ]

# Function to add manually adjusted city labels
add_kernel_city_labels <- function() {
  
  text(aca_crd$X - 100000, aca_crd$Y, "Acapulco", cex = 1.1, col = "#2C7F7B")
  text(can_crd$X - 100000, can_crd$Y, "Cancún", cex = 1.1, col = "#2C7F7B")
  text(mex_crd$X - 10000, mex_crd$Y + 90000, "Mexico City", cex = 1.1, col = "#2C7F7B")
  text(gdl_crd$X, gdl_crd$Y - 90000, "Guadalajara", cex = 1.1, col = "#2C7F7B")
  text(leo_crd$X + 10000, leo_crd$Y + 80000, "León", cex = 1.1, col = "#2C7F7B")
  text(mzt_crd$X + 120000, mzt_crd$Y + 40000, "Mazatlán", cex = 1.1, col = "#2C7F7B")
  text(mty_crd$X, mty_crd$Y - 80000, "Monterrey", cex = 1.1, col = "#2C7F7B")
  text(pue_crd$X + 10000, pue_crd$Y - 70000, "Puebla", cex = 1.1, col = "#2C7F7B")
  text(ver_crd$X + 100000, ver_crd$Y - 12816, "Veracruz", cex = 1.1, col = "#2C7F7B")
  text(pva_crd$X - 180000, pva_crd$Y + 45000, "Puerto Vallarta", cex = 1.1, col = "#2C7F7B")
}

# Draw final local-scale kernel density map
par(bg = "#F4E7E1")
map_kernel_local()
add_kernel_city_labels()


############################################################
#### REGIONAL-SCALE KERNEL DENSITY MAP
############################################################

# Convert the regional-scale spatstat kernel density object to raster
kernel_regional_raster <- rast(kernel_regional)

# Check and assign CRS to the raster object
crs(kernel_regional_raster)
crs(mex_vect)

crs(kernel_regional_raster) <- crs(mex_vect)

crs(kernel_regional_raster)

# Crop the regional-scale kernel raster to the national boundary extent
kernel_regional_crop <- crop(kernel_regional_raster, mex_vect)

# Mask the raster to keep only the national territory
kernel_regional_mask <- mask(kernel_regional_crop, mex_vect)

# Preliminary regional-scale kernel density map
plot(kernel_regional_mask,
     col = kernel_cols,
     legend = FALSE,
     main = "")

# Add national boundary
plot(st_geometry(mex),
     add = TRUE,
     border = "grey30",
     lwd = 1)


############################################################
#### REGIONAL-SCALE KERNEL DENSITY MAP STYLE
############################################################

# Function to draw the regional-scale kernel density map
map_kernel_regional <- function() {
  
  # Draw national boundary as base map
  plot(st_geometry(mex),
       col = "#FFFDF6",
       border = "grey30",
       axes = FALSE)
  
  # Add regional-scale kernel density raster
  plot(kernel_regional_mask,
       add = TRUE,
       col = kernel_cols,
       legend = FALSE,
       axes = FALSE)
  
  # Redraw national boundary
  plot(st_geometry(mex),
       add = TRUE,
       border = "grey30",
       lwd = 1)
  
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
  title("Regional-scale kernel density of hotels in selected cities in Mexico",
        line = -1.5)
}

# Draw final regional-scale kernel density map
par(bg = "#F4E7E1")
map_kernel_regional()
add_kernel_city_labels()


############################################################
# Export settings can be adjusted according to visualization needs

