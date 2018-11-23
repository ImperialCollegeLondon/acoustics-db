import datetime
import os
import box

db.define_table('sites',
    Field('latitude', 'float'),
    Field('longitude', 'float'),
    Field('site_name', 'string'),
    Field('short_desc', 'string'),
    Field('long_desc', 'string'),
    Field('image', 'upload'),
    format='%(site_name)s')

db.define_table('recorders',
    Field('recorder_id', 'string'),
    format='%(recorder_id)s')

db.define_table('deployments',
    Field('recorder_id', 'reference recorders'),
    Field('site_id', 'reference sites'),
    Field('deployed_from', 'date'),
    Field('deployed_to', 'date'),
    Field('height', 'float'))

# The table below isn't completely normalised but the site links to audio are used 
# frequently. When deployments are unknown then site_id and deployment_id are null.

db.define_table('audio',
    Field('deployment_id', 'reference deployments'),
    Field('site_id', 'reference sites'),
    Field('filename', 'string'),
    Field('record_datetime', 'datetime'),
    Field('start_time', 'time'),
    Field('length_seconds', 'float'),
    Field('box_dir', 'string'),
    Field('box_id', 'string'),
    Field('box_url', 'string'))

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