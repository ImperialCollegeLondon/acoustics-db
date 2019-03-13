import os
import box

# These could be in a table, but simpler to hard code a fixed global set
HABITATS = {'Old Growth', 'Logged Fragment', 'Riparian Reserve', 'Cleared Forest', 'Oil Palm'}
RECORDER_TYPES = {'rpi-eco-monitor', 'point_recording'}


db.define_table('sites',
    Field('latitude', 'float'),
    Field('longitude', 'float'),
    Field('site_name', 'string'),
    Field('short_desc', 'string'),
    Field('long_desc', 'string'),
    Field('image', 'upload'),
    Field('habitat', 'string', requires=IS_IN_SET(HABITATS)),
    format='%(site_name)s')

db.define_table('deployments',
    Field('recorder_id', 'string'),
    Field('site_id', 'reference sites'),
    Field('deployed_from', 'date'),
    Field('deployed_to', 'date'),
    Field('deployed_by', 'string'),
    Field('height', 'float'))

# The table below is deliberately not completely normalised. Scanning
# Box should always provide a record date and start time, along with
# other metadata. The final fields are assigned either by matching a
# rpi-eco-monitor id to deployments or by matching a site name directly
# to the sites table.

db.define_table('audio',
    Field('filename', 'string'),
    Field('recorder_id', 'string'),
    Field('record_datetime', 'datetime'),
    Field('start_time', 'time'),
    Field('time_window', 'integer', default=None),
    Field('length_seconds', 'float'),
    Field('file_size', 'integer'),
    Field('box_dir', 'string'),
    Field('box_id', 'string'),
    Field('deployment_id', 'reference deployments'),
    Field('site_id', 'reference sites'),
    Field('habitat', 'string', requires=IS_IN_SET(HABITATS)),
    Field('recorder_type', 'string', requires=IS_IN_SET(RECORDER_TYPES)),
    Field('next_in_stream', 'integer', default=None))

db.define_table('box_scans',
    Field('scan_datetime', 'datetime'),
    Field('known_total', 'integer'),
    Field('known_new', 'integer'),
    Field('unknown_total', 'integer'),
    Field('unknown_new', 'integer'))

# Images - provide a library of site images keyed by habitat
db.define_table('site_images',
                Field('name', 'string'),
                Field('image', 'upload',
                      uploadfolder=os.path.join(request.folder, 'uploads', 'site_images')),
                Field('thumb', 'upload', readable=False, writable=False,
                      uploadfolder=os.path.join(request.folder, 'uploads', 'site_images_thumbs')),
                Field('hidden', 'boolean', default=False),
                Field('habitat', 'string', requires=IS_IN_SET(HABITATS)))

# Taxa
db.define_table('taxa',
                Field('common_name', 'string'),
                Field('scientific_name', 'string'),
                Field('taxon_rank', 'string'),
                Field('gbif_key', 'integer'),
                Field('taxon_class', 'string'))

db.define_table('taxon_observations',
                Field('taxon_id', 'reference taxa'),
                Field('site_id', 'reference sites'),
                Field('obs_time', 'time'),
                Field('time_window', 'integer', default=None))

db.define_table('gbif_image_occurrences',
                Field('taxon_id', 'reference taxa'),
                Field('gbif_occurrence_accepted_name', 'string'),
                Field('gbif_occurrence_taxon_key', 'integer'),
                Field('gbif_occurrence_key', 'integer',
                      represent=lambda value, row: "https://www.gbif.org/occurrence/{}".format(value)),
                Field('gbif_occurrence_license', 'string'),
                Field('gbif_occurrence_rights', 'string'),
                Field('gbif_occurrence_rights_holder', 'string'),
                Field('gbif_occurrence_references', 'string'),
                Field('gbif_occurrence_behavior', 'string'),
                Field('gbif_media_identifier', 'string'),
                Field('gbif_media_format', 'string'),
                Field('gbif_media_creator', 'string'),
                Field('gbif_media_description', 'string'))

db.define_table('gbif_sound_occurrences',
                Field('taxon_id', 'reference taxa'),
                Field('gbif_occurrence_accepted_name', 'string'),
                Field('gbif_occurrence_taxon_key', 'integer'),
                Field('gbif_occurrence_key', 'integer',
                      represent=lambda value, row: "https://www.gbif.org/occurrence/{}".format(value)),
                Field('gbif_occurrence_license', 'string'),
                Field('gbif_occurrence_rights', 'string'),
                Field('gbif_occurrence_rights_holder', 'string'),
                Field('gbif_occurrence_references', 'string'),
                Field('gbif_occurrence_behavior', 'string'),
                Field('gbif_media_identifier', 'string'),
                Field('gbif_media_format', 'string'),
                Field('gbif_media_creator', 'string'),
                Field('gbif_media_description', 'string'))



# create and cache an instance of the BOX connection and make
# it accessible from current so it can be used in modules

JSON_FILE = os.path.join(request.folder, myconf.take('box.app_config'))
PRIVATE_KEY_FILE = os.path.join(request.folder, myconf.take('box.pem_file'))

box_client = cache.ram('box_client',
                       lambda: box.authorize_jwt_client_json(JSON_FILE, PRIVATE_KEY_FILE),
                       time_expire=3600)

current.box_client = box_client

# create and cache a downscoped token to use in providing download links for audio files
# The expiry time is a bit of guess - they seem to last an hour or so but not precisely.
# Can we use the dl_token.expires_in to set a real expiry time?

dl_token = cache.ram('dl_token',
                     lambda: box.downscope_to_root_download(box_client),
                     time_expire=3600)

