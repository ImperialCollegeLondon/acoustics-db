library(openxlsx)
library(rgbif)
library(uuid)

dat <- read.xlsx('~/Research/SAFE/Web2Py/web2py_2_12_2/applications/rainforest_rhythms/static/taxa/website_spec_list.xlsx')

names(dat) <- make.names(names(dat))

# Corrections
dat$Genus[dat$Genus == 'Eutrophis'] <- 'Eutropis'
dat$Genus[dat$Genus == 'Amnirana'] <- 'Hylarana' # Amnirana nicobariensis
dat$Genus[dat$Genus == 'Kurixalus'] <- 'Rhacophorus' # Kurixalus appendiculatus
dat$Genus[dat$Genus == 'Chalcorana'] <- 'Hylarana' # Chalcorana raniceps
dat$Species..latin.[dat$Species..latin. == 'othilopus'] <- 'otilophus' # Polypedates othilopus
dat$Species..latin.[dat$Species..latin. == 'frittinniens'] <- 'fritinniens' # Leptolalax frittinniens


# Taxon table
dat$binomial <- with(dat, paste(Genus, Species..latin.))
taxa <- unique(subset(dat, select=c(Species..English., Genus, Species..latin., Group, binomial)))

# look up on GBIF
gbif <- lapply(taxa$binomial, name_backbone)
taxa$match_type <- sapply(gbif, '[[', 'matchType')

subset(taxa, match_type != 'EXACT')

taxa$rank <- sapply(gbif, '[[', 'rank')
taxa$gbif_key <- sapply(gbif, '[[', 'usageKey')
taxa$taxon_class <- sapply(gbif, '[[', 'class')

# export tables to populate db
taxa <- taxa[, c('Species..English.', 'binomial', 'rank', 'gbif_key', 'taxon_class')]
names(taxa) <- c('common_name', 'scientific_name', 'taxon_rank', 'gbif_key', 'taxon_class')

taxon_observations <- dat[, c('binomial', 'Site', 'Time')]
names(taxon_observations) <- c('scientific_name', 'site', 'time')

write.csv(taxa, 'taxa.csv')
write.csv(taxon_observations, 'taxon_observations.csv')


