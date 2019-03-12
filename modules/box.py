#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Box interface module. 

Used to generate the cached client in the rr model and to provide
functions to scan the Box root folder for files and update the database
'''

import json
import os
import datetime

from boxsdk import JWTAuth, Client
from boxsdk.exception import BoxAPIException

# current exposes the database abstraction layer as current.db
from gluon import current


def store_token(access_token, _):
    """
    Callback function for storage of the access token
    """
    os.environ.setdefault('access_token', access_token)


def authorize_jwt_client_json(config, private_key_file):
    """
    Function to obtain an authorised Box API Client using JWT
    """
    if os.path.exists(config):
        with open(config, 'r') as json_file:
            config = json.load(json_file)
    else:
        raise IOError('Config file not found')

    jwt_auth = JWTAuth(
        client_id=config['boxAppSettings']['clientID'],
        client_secret=config['boxAppSettings']['clientSecret'],
        enterprise_id=config['enterpriseID'],
        jwt_key_id=config['boxAppSettings']['appAuth']['publicKeyID'],
        access_token=None,
        rsa_private_key_file_sys_path=private_key_file,
        rsa_private_key_passphrase=str(config['boxAppSettings']['appAuth']['passphrase']).encode('utf_8'),
        store_tokens=lambda acc, _: store_token(acc, _)
    )

    jwt_auth.authenticate_instance()
    return Client(jwt_auth)


def downscope_to_root_download(client):
    """
    Function to provide a downscoped access token from the server JWT client
    that can be provided to users.
    :param client: A JWT Client instance
    :return: A Box SDK TokenResponse object
    """

    root = client.folder(current.myconf.take('box.data_root'))
    dl_token = client.downscope_token(scopes=['item_download'], item=root)

    return dl_token


def scan_box(client):
    
    """
    Searches through the folder structure indexing all MP3 files. 
    The search is date restricted by the last scan, with the scan date
    stored in the database.

    :param client: An authorised Box API client instance
    """
    
    # find the most recent scan date
    qry = current.db(current.db.box_scans)
    last_scan = qry.select(orderby=~current.db.box_scans.scan_datetime,
                           limitby=(0, 1)).first()
    
    # If this has run before, there should be a row, but first time around we choose
    # an arbitrary old date. Either way, convert that to a string to pass to Box,
    # which requires the timezone specification. Note that web2py strips microseconds
    # from the datetime when storing, which is good because Box doesn't accept them.
    if last_scan is None:
        scan_from = datetime.datetime(1970, 1, 1)
        scan_from_str = scan_from.isoformat() + 'Z'
    else:
        scan_from_str = last_scan.scan_datetime.isoformat() + 'Z'

    # Get the folder scan configuration
    folder_scan = current.myconf.take('box.data_folders')

    # Record the time the scan starts, so that any files added during the search
    # aren't missed by the next scan
    scan_started = datetime.datetime.now()

    new_known = 0
    new_unknown = 0

    # Loop over those folders
    for this_folder in folder_scan:

        # Call the search endpoint limiting to files within the current folder.
        # Note that the path collection is always relative to the root folder
        # (client.folder('0')) regardless of any ancestors provided.
        file_search = client.search().query(query='*.mp3',
                                            ancestor_folders=[client.folder(this_folder['id']).get()],
                                            file_extensions=['mp3'],
                                            created_at_range=(scan_from_str, None),
                                            type='file',
                                            fields=['name', 'id', 'path_collection', 'size'],
                                            limit=200)

        # Now iterate over the file search generator
        for this_file in file_search:

            # If the file isn't already known
            if current.db.audio(box_id=this_file.id):
                continue

            # Extract the path
            path = [entry.name for entry in this_file.path_collection['entries']]

            # Two kinds of data folders:
            # 1) 'Deployed' data - only the rpid is reported in the path, so location
            #    is looked up against a table of deployments.
            # 2) Other data needs to contain the location in the path.

            # Get the date of the recording from the folder structure
            rec_date = datetime.datetime.strptime(path[this_folder['date_index']], '%Y-%m-%d').date()

            if this_folder['deployed']:

                # Check the deployment of this recorder is known
                rec_id = path[this_folder['pi_index']]

                deployment_record = current.db((current.db.deployments.recorder_id == rec_id) &
                                               (current.db.deployments.deployed_from <= rec_date) &
                                               (current.db.deployments.deployed_to >= rec_date) &
                                               (current.db.deployments.site_id == current.db.sites.id)
                                               ).select(limitby=(0, 1)).first()

                if deployment_record:
                    # TODO - this assumes deployments don't overlap and chooses the first if they do.
                    did = deployment_record.deployments.id
                    sid = deployment_record.deployments.site_id
                    hab = deployment_record.sites.habitat
                    new_known += 1
                else:
                    did = None
                    sid = None
                    hab = None
                    new_unknown += 1
            else:
                # Get the location of the recorder
                loc_id = path[this_folder['location_index']]
                site = current.db(current.db.sites.site_name == loc_id).select(limitby=(0, 1)).first()

                if site:
                    did = None
                    sid = site.id
                    hab = site.habitat
                    new_known += 1
                else:
                    did = None
                    sid = None
                    hab = None
                    new_unknown += 1

            # Now insert the file into the database
            rec_start = datetime.datetime.strptime(this_file.name[:8], '%H-%M-%S').time()
            rec_datetime = datetime.datetime.combine(rec_date, rec_start)

            current.db.audio.insert(deployment_id=did,
                                    site_id=sid,
                                    habitat=hab,
                                    recorder_type=this_folder['recorder_type'],
                                    filename=this_file.name,
                                    record_datetime=rec_datetime,
                                    start_time=rec_start,
                                    length_seconds=1200,  # unless I can figure out a way to get actual time
                                    file_size=this_file.size,
                                    box_dir=os.path.join(*path),
                                    box_id=this_file.id)

    # Insert the new scan date
    current.db.box_scans.insert(scan_datetime=scan_started,
                                known_total=current.db(current.db.audio.site_id).count(),
                                unknown_total=current.db(current.db.audio.site_id == None).count(),
                                known_new=new_known,
                                unknown_new=new_unknown)

    current.db.commit()

    return dict()
