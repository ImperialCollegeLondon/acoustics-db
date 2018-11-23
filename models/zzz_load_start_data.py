import os
import csv
import datetime

## Code to load example from file if there isn't any

if db(db.sites).count() == 0:
	# password is 'password' put through the default hashing algorithm

    data = [{'site_name':"E100 edge", 'latitude':4.68392, 'longitude':117.58604},
            {'site_name':"D100 641", 'latitude':4.71129, 'longitude':117.58753},
            {'site_name':"C10 621", 'latitude':4.71118, 'longitude':117.61899},
            {'site_name':"B10", 'latitude':4.72747, 'longitude':117.61433},
            {'site_name':"E1 648", 'latitude':4.693722, 'longitude':117.581175},
            {'site_name':"D Matrix", 'latitude':4.70272, 'longitude':117.59141},
            {'site_name':"C Matrix", 'latitude':4.71011, 'longitude':117.61071},
            {'site_name':"Riparian 1", 'latitude':4.65041, 'longitude':117.54203},
            {'site_name':"Riparian 2", 'latitude':4.65278, 'longitude':117.54653},
            {'site_name':"VJR 1", 'latitude':4.664433, 'longitude':117.535133},
            {'site_name':"VJR 2", 'latitude':4.66803, 'longitude':117.53897},
            {'site_name':"B1 602", 'latitude':4.72834, 'longitude':117.62350},
            {'site_name':"OP3 843",'latitude': 4.64005, 'longitude':117.45265},
            {'site_name':"OP Young", 'latitude':4.63707, 'longitude':117.52016}]
    
    db.sites.bulk_insert(data)

if db(db.recorders).count() == 0:

    data = [{"recorder_id":'RPiID-00000000c0e3c6fc'},
            {"recorder_id":'RPiID-00000000ef3410fd'},
            {"recorder_id":'RPiID-000000005ec3ba66'},
            {"recorder_id":'RPiID-000000005ee4697b'},
            {"recorder_id":'RPiID-0000000075818774'},
            {"recorder_id":'RPiID-000000006cb9d2cb'},
            {"recorder_id":'RPiID-0000000094cecfb7'},
            {"recorder_id":'RPiID-000000009b617d6'},
            {"recorder_id":'RPiID-000000008acc6628'},
            {"recorder_id":'RPiID-00000000823f6bbd'}]

    db.recorders.bulk_insert(data)

if db(db.deployments).count() == 0:

    data = [["B10",    10,    "16/10/2018",    "RPiID-00000000c0e3c6fc"],
            ["E1 648",    5,    "17/10/2018",    "RPiID-00000000ef3410fd"],
            ["E100 edge",    13,    "17/10/2018",    "RPiID-000000005ec3ba66"],
            ["C10 621",    10,    "18/10/2018",    "RPiID-000000005ee4697b"],
            ["VJR 1",    30,    "26/10/2018",    "RPiID-0000000075818774"],
            ["VJR 2",    5,    "19/10/2018",    "RPiID-000000006cb9d2cb"],
            ["Riparian 1",    17,    "26/10/2018",    "RPiID-0000000094cecfb7"],
            ["Riparian 2",    16,    "23/10/2018",    "RPiID-000000009b617d6"],
            ["D100 641",    7,    "22/10/2018",    "RPiID-000000008acc6628"],
            ["D Matrix",    10,    "22/10/2018",    "RPiID-00000000823f6bbd"]]

    for nm, hght, start, recid in data:
        
        site_id = db(db.sites.site_name == nm).select().first().id
        rec_id = db(db.recorders.recorder_id == recid).select().first().id
        
        db.deployments.insert(recorder_id = rec_id,
                              site_id = site_id,
                              deployed_from = datetime.datetime.strptime(start,'%d/%m/%Y'),
                              deployed_to = datetime.datetime.strptime("31/12/2020",'%d/%m/%Y'),
                              height = hght)
