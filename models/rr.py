import datetime
import os
import box

# These could be in a table, but simpler to hard code a fixed global set
HABITATS = {'Old Growth', 'Logged Fragment', 'Riparian Reserve', 'Cleared Forest', 'Oil Palm'}
RECORDER_TYPES = {'rpi-eco-monitor', 'Directional Microphone'}


db.define_table('sites',
    Field('latitude', 'float'),
    Field('longitude', 'float'),
    Field('site_name', 'string'),
    Field('short_desc', 'string'),
    Field('long_desc', 'string'),
    Field('image', 'upload'),
    Field('habitat', 'string', requires=IS_IN_SET(HABITATS)),
    format='%(site_name)s')

db.define_table('recorders',
    Field('recorder_id', 'string'),
    Field('recorder_type', 'string', requires=IS_IN_SET(RECORDER_TYPES)),
    format='%(recorder_id)s')

db.define_table('deployments',
    Field('recorder_id', 'reference recorders'),
    Field('site_id', 'reference sites'),
    Field('deployed_from', 'date'),
    Field('deployed_to', 'date'),
    Field('deployed_by', 'string'),
    Field('height', 'float'))

# The table below is deliberately not completely normalised. Scanning
# Box should always provide a recorder ID, record date and start time,
# along with other metadata. The final two fields are assigned by 
# matching recorder and date to deployments and this could be changed
# if deployment records are changed. Site and habitat could be joined 
# in via the deployments table but are stored directly here because 
# the majority of queries can then act on a single table without joins.

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
    Field('box_url', 'string'),
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


# create and cache an instance of the BOX connection
JSON_FILE = os.path.join(request.folder, myconf.take('box.app_config'))
PRIVATE_KEY_FILE = os.path.join(request.folder, myconf.take('box.pem_file'))

box_client = cache.ram('box_client', lambda: box.authorize_jwt_client_json(JSON_FILE, PRIVATE_KEY_FILE), time_expire=60)