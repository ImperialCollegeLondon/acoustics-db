import os
import csv

## Code to load example from file if there isn't any

if db(db.auth_user).count() == 0:
	# password is 'password' put through the default hashing algorithm
	db.auth_user.insert(first_name='David',
						last_name='Orme',
						email='d.orme@imperial.ac.uk',
						password = 'pbkdf2(1000,20,sha512)$9959ad1756854922$780d4e345330feebc50f0cc9ec8fe03fcf53c9cc',
						id_skill = 2.0)

	db.auth_user.insert(first_name='Anne',
						last_name='Expert',
						email='anne_expert@mailinator.com',
						password = 'pbkdf2(1000,20,sha512)$9959ad1756854922$780d4e345330feebc50f0cc9ec8fe03fcf53c9cc',
						id_skill = 5.0)

	db.auth_user.insert(first_name='Annie',
						last_name='Idiot',
						email='annie_idiot@mailinator.com',
						password = 'pbkdf2(1000,20,sha512)$9959ad1756854922$780d4e345330feebc50f0cc9ec8fe03fcf53c9cc',
						id_skill = 1.0)


## ORDER matters here!

if db(db.audio).count() == 0:
	data_file = os.path.join(request.folder, 'private', 'db_data','audio.csv')
	db.audio.import_from_csv_file(open(data_file, 'rb'), null='None')

if db(db.calls).count() == 0:
	# these need special handling to create the calls
	data_file = open(os.path.join(request.folder, 'private', 'db_data','calls.csv'))
	data = csv.DictReader(data_file)
	
	for r in data:
		source = os.path.join(request.folder,'static', 'audio', db.audio[r['audio_id']].filename)
		_extract_call_and_add_to_db(source, r['audio_id'], float(r['start_time']), float(r['end_time']), 1, r['call_note'])


if db(db.taxa).count() == 0:
	data_file = os.path.join(request.folder, 'private', 'db_data','taxa.csv')
	db.taxa.import_from_csv_file(open(data_file, 'rb'), null='None')

if db(db.identifications).count() == 0:
	data_file = os.path.join(request.folder, 'private', 'db_data','identifications.csv')
	db.identifications.import_from_csv_file(open(data_file, 'rb'), null='None')

if db(db.scores).count() == 0:
	data_file = os.path.join(request.folder, 'private', 'db_data','scores.csv')
	db.scores.import_from_csv_file(open(data_file, 'rb'), null='None')

