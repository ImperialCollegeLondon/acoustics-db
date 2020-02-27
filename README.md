# Acoustics DB

This website is used to maintain a database of remotely collected audio data.

It is currently running on:

https://acoustics-db.safeproject.net


## Website

The website exposes some simple information pages:

* [Home](https://acoustics-db.safeproject.net/home)
* [Map](https://acoustics-db.safeproject.net/map): a simple Leaflet map of the recorder locations.
* [Audio](https://acoustics-db.safeproject.net/audio): a searchable table of collected audio files 
* [Availability](https://acoustics-db.safeproject.net/availability): a graph of recorder availability and a summary of new files added through time.

An administrator interface provides access to underlying tables of sites, deployments, taxa and the like and exposes some admin tasks.

## API

There are a number of different JSON services exposed in the code (see `controllers/default.py` for details) but there are two key services used to drive the public website.

### [https://acoustics-db.safeproject.net/calls/json/api_response]()

The response from this API is JSON data containing a dictionary with five top level entries:

1. `sitesById`: This is a dictionary of site information keyed by numeric id with the following structure. Note that the photo element holds a different photo of the site for each hour of the day.


```json
{
	"1": {
		"site_name": "E100_edge",
		"habitat": "Logged Fragment",
		"photo": {
			"00:00": "https://acoustics-db.safeproject.net/download/site_images.image.ab1d69adfceb223b.50313230303732312e4a5047.JPG",
			"01:00": "https://acoustics-db.safeproject.net/download/site_images.image.aa797f073f41726b.50313230303731332e4a5047.JPG",
			...
		},
		"short_desc": null,
		"longitude": 117.58604,
		"latitude": 4.68392,
		"n_audio": 3826
	},
	...
}
```

2. `taxaById`: This is a dictionary of species information keyed by numeric id. The species information contains links to representative images (which can be an external GBIF occurrence or a local file as in the example below) and audio (typically linked through a GBIF occurrence)

```json
{
	"1": {
		"common_name": "Fluffy-backed Tit-Babbler",
		"gbif_key": 6100830,
		"taxon_rank": "SPECIES",
		"scientific_name": "Macronus ptilosus",
		"image": {
			"gbif_occurrence_key": null,
			"gbif_rights_holder": null,
			"media_url": "https://acoustics-db.safeproject.net/download/taxa.image.a60f2c3027f2f648.315f666c756666792d6261636b65645f7469742d626162626c65722e6a7067.jpg"
		},
		"audio": {
			"gbif_occurrence_key": 1934977174,
			"gbif_media_identifier": "https://www.xeno-canto.org/sounds/uploaded/PWDLINYMKL/Fluffy-backedTit-babblercall.mp3",
			"gbif_rights_holder": "Mike Nelson",
			"gbif_occurrence_behavior": "call"
		},
		"id": 1,
		"taxon_class": "Aves"
	},
	...
}
```

3.  "taxaIdBySiteId": This is a simple dictionary keyed by site ID that provides a list of taxon ids for taxa observed at a site:

```json
 {
	 "1":  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 108, 74, 94, 48, 109, 107, 72, 92, 69, 71, 104, 98, 49, 51, 95, 103, 30, 43, 126, 34, 26, 50, 97, 31, 137, 32, 133, 148, 140, 56, 47, 73],
	 "2": [3, 26, 22, 13, 1, 6, 25, 5, 10, 2, 21, 27, 28, 29, 30, 31, 17, 32, 33, 4, 11, 20, 39, 9, 40, 97, 34, 14, 54, 76, 98, 71, 101, 112, 79, 107, 113, 82, 94, 108, 123, 12, 19, 38, 35, 49, 56, 52, 45, 43, 15, 37, 136, 53, 74, 95, 57],
	...
}
 ``` 
 
 4. `taxaIdBySiteIdByTime`:  This further breaks down taxa by site. For each site key, there is a dictionary, keyed by hour and providing a list of taxon ids observed during that hour of the day at that site:
```json
 {
	"1": {"0": [107, 69, 71, 104, 11, 73],
		  "1": [104, 107, 72], 
		  "2": [72, 98, 73], 
		  ...
		  },
	"2": {"0": [71, 98], 
		  "1": [71, 98, 107], 
		  "2": [71, 98, 112],
		  ...
		  },
	...
}
```
  5. `siteAudioByAudioId": This is a list of dictionaries providing links to audio recordings by time and site. The number of recordings per site depends on the length of the audio slots: with 20 minute recordings there will be 72 (24 * 3). Each entry in the list identifies a recording made in a time slot at a particular site and provides recording IDs to access that audio.

```json
[
	{
		"date": "2018-12-15",
		"audio": 21714,
		"site": 1,
		"box_id": "367938937588",
		"time": "00:03:32"
	},
	{
		"date": "2018-12-15",
		"audio": 21679,
		"site": 1,
		"box_id": "367933501749",
		"time": "00:23:32"
	},
	...
]
```

### [https://acoustics-db.safeproject.net/call/json/get_dl_access_token]()

This API just returns a string token that is used to provide access to the audio file.
