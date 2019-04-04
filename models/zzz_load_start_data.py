import os
import csv
import datetime
from module_admin_functions import make_thumb
import glob

# Code to load example from file if there isn't any - password generated using:
# str(db.auth_user.password.validate(string)[0])

if db(db.auth_user).count() == 0:
    db.auth_user.insert(first_name='Admin',
                        last_name='Admin',
                        username='admin',
                        email='d.orme@imperial.ac.uk',
                        password='pbkdf2(1000,20,sha512)$b0a46bad495e614a$5f1fde78956bc7f5fd4bc00e0443c019a70f9ee7')

if db(db.sites).count() == 0:

    data = [{'site_name': "E100_edge", 'latitude': 4.68392, 'longitude': 117.58604, 'habitat': "Logged Fragment"},
            {'site_name': "D100_641", 'latitude': 4.71129, 'longitude': 117.58753, 'habitat': "Logged Fragment"},
            {'site_name': "C10_621", 'latitude': 4.71118, 'longitude': 117.61899, 'habitat': "Logged Fragment"},
            {'site_name': "B10", 'latitude': 4.72747, 'longitude': 117.61433, 'habitat': "Logged Fragment"},
            {'site_name': "E1_648", 'latitude': 4.693722, 'longitude': 117.581175, 'habitat': "Logged Fragment"},
            {'site_name': "D_Matrix", 'latitude': 4.70272, 'longitude': 117.59141, 'habitat': "Cleared Forest"},
            {'site_name': "C_Matrix", 'latitude': 4.71011, 'longitude': 117.61071, 'habitat': "Cleared Forest"},
            {'site_name': "Riparian_1", 'latitude': 4.65041, 'longitude': 117.54203, 'habitat': "Riparian Reserve"},
            {'site_name': "Riparian_2", 'latitude': 4.65278, 'longitude': 117.54653, 'habitat': "Riparian Reserve"},
            {'site_name': "VJR_1", 'latitude': 4.664433, 'longitude': 117.535133, 'habitat': "Old Growth"},
            {'site_name': "VJR_2", 'latitude': 4.66803, 'longitude': 117.53897, 'habitat': "Old Growth"},
            {'site_name': "B1_602", 'latitude': 4.72834, 'longitude': 117.62350, 'habitat': "Logged Fragment"},
            {'site_name': "OP3_843",'latitude': 4.64005, 'longitude': 117.45265, 'habitat': "Oil Palm"},
            # {'site_name':"OP Young", 'latitude': 4.63707, 'longitude': 117.52016,'habitat': "Oil Palm"}
            {'site_name':"OP_Belian", 'latitude': 4.63707, 'longitude': 117.52016,'habitat': "Oil Palm"}
            ]

    db.sites.bulk_insert(data)

if db(db.deployments).count() == 0:

    data = [["B10",        10, "16/10/2018",  "RPiID-00000000c0e3c6fc"],
            ["E1_648",      5, "17/10/2018",  "RPiID-00000000ef3410fd"],
            ["E100_edge",  13, "17/10/2018",  "RPiID-000000005ec3ba66"],
            ["C10_621",    10, "18/10/2018",  "RPiID-000000005ee4697b"],
            ["VJR_1",      30, "26/10/2018",  "RPiID-0000000075818774"],
            ["VJR_2",       5, "19/10/2018",  "RPiID-000000006cb9d2cb"],
            ["Riparian_1", 17, "26/10/2018",  "RPiID-0000000094cecfb7"],
            ["Riparian_2", 16, "23/10/2018",  "RPiID-000000009b618d6d"],
            ["D100_641",    7, "22/10/2018",  "RPiID-000000008acc6628"],
            ["D_Matrix",   10, "22/10/2018",  "RPiID-00000000823f6bbd"]]

    for nm, hght, start, recid in data:
        
        site_id = db(db.sites.site_name == nm).select().first().id

        db.deployments.insert(recorder_id=recid,
                              site_id=site_id,
                              deployed_from=datetime.datetime.strptime(start, '%d/%m/%Y'),
                              deployed_to=datetime.datetime.strptime("31/12/2020", '%d/%m/%Y'),
                              deployed_by='Sarab Sethi',
                              height=hght)


# Load taxon details and Shutterstock imagery provided by Aaron Signorelli

if db(db.taxa).count() == 0:

    taxon_csv = os.path.join(request.folder, 'private', 'taxa', 'taxa_with_images.csv')
    taxon_data = csv.DictReader(open(taxon_csv, 'r'))

    for taxon in taxon_data:

        if taxon['file']:
            img_in = os.path.join(request.folder, 'private', 'taxa', 'shutterstock_imagery', taxon['file'])
            taxon['image'] = db.taxa.image.store(open(img_in, 'rb'), taxon['file'])
            taxon['image_is_local'] = True
        else:
            taxon['image_is_local'] = False

        rec = db.taxa.insert(**taxon)

        if taxon['file']:
            make_thumb(rec, 'taxa')


if db(db.taxon_observations).count() == 0:

    obs_file = os.path.join(request.folder, 'private', 'taxa', 'taxon_observations.csv')
    obs_file = csv.DictReader(open(obs_file, 'r'))

    for obs in obs_file:

        taxon = db(db.taxa.scientific_name == obs['scientific_name']).select().first()
        site = db(db.sites.site_name == obs['site']).select().first()

        if site is not None:
            db.taxon_observations.insert(taxon_id=taxon.id,
                                         site_id=site.id,
                                         obs_time=obs['time'],
                                         obs_hour=datetime.datetime.strptime(obs['time'], '%H:%M').hour)

if db(db.site_images).count() == 0:

    for habitat in HABITATS:

        hab_dir = os.path.join(request.folder, 'private', 'initial_site_images_small', habitat)
        initial_images = glob.glob(hab_dir + '/*')

        for image in initial_images:

            img_st = db.site_images.image.store(open(image, 'rb'), image)
            rec = db.site_images.insert(name=image,
                                        image=img_st,
                                        habitat=habitat)
            make_thumb(rec)



