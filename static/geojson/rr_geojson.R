library(sf)
library(geojsonio)

# POLYGONS
borders <- st_read('/Users/dorme/Research/SAFE/Workstation_rsync/SAFE_GIS/Sampling_area_borders/Sampling_area_borders_WGS84.shp')
layout <- st_read('/Users/dorme/Research/SAFE/Workstation_rsync/SAFE_GIS/SAFE_layout/SAFE_layout_WGS84.shp')

# reduce to current audio sites
borders <- borders[3:4,]
fragments <- layout[layout$CATEGORY=='Fragment',]

# cut fragments out of experimental site to avoid overplotting
borders_holes <- st_difference(borders, st_union(fragments))

# assign categories and reconcile field names
borders_holes$type <- c("primary", "matrix")
fragments$type <- ("logged")
fragments$name <- fragments$CODE

data <- rbind(borders_holes[, c('name', 'type')], fragments[, c('name', 'type')])

# STREAMS
streams <- st_read('/Users/dorme/Research/SAFE/Workstation_rsync/SAFE_GIS/Stream_networks/SRTM_stream_networks/SRTM_Channels.shp')

# issue with zero length stream section
n <- st_length(streams)
streams <- streams[-which(as.numeric(n) == 0),]

# get stream sections surrounding SAFE
safe_buffer <- st_buffer(st_transform(st_union(data), "+init=EPSG:32650"), 10000)
streams_safe <- st_intersection(streams, safe_buffer)
streams_safe <- st_transform(streams_safe, '+init=EPSG:4326')

# EXPORT
geojson_write(data, file='map_data.geojson')
geojson_write(streams_safe, file='stream_data.geojson')

# PLOT to check
plot(st_geometry(st_transform(safe_buffer, '+init=EPSG:4326')))
plot(st_geometry(streams_safe), add=TRUE, col='cornflowerblue')
plot(data['type'], add=TRUE, col=sf.colors(alpha=0.5))

