import datetime
from pydub import AudioSegment
import matplotlib.colors as colors
import matplotlib.cm as cm
import os
import copy

# Table to hold a list of audio files
#  - can't make the previous and next reference the ids as a key
#	 because of insertion order effects!

db.define_table('sites',
    Field('latitude', 'float'),
    Field('longitude', 'float'),
    Field('site_name', 'string'))

db.define_table('audio',
    Field('site_id', 'reference sites'),
    Field('filename', 'string'),
    Field('record_date', 'date'),
    Field('start_time', 'time'),
    Field('length_seconds', 'float'),
    Field('static_filepath', 'string'),
    Field('box_id', 'string'),
    Field('box_url', 'string'))
