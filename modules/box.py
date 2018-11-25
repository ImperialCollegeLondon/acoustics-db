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


def scan_box(client, root, date_index = 4, pi_index = 3):
    
    """
    Searches through the folder structure indexing all MP3 files. 
    The search is date restricted by the last scan, with the scan date
    store in the database.

    :param client: An authorised Box API client instance
    :param root: A Box object ID for the starting folder
    """
    
    
    # find the most recent scan date
    qry = current.db(current.db.box_scans)
    last_scan = qry.select(orderby=~current.db.box_scans.scan_datetime,
                           limitby=(0,1)).first()
    
    # If this has run before, there should be a row, but first
    # time around we choose an arbitrary old date.
    # Either way, convert that to a string to pass to Box, which requires the timezone 
    # specification. Note that web2py strips microseconds from the datetime
    # when storing, which is good because Box doesn't accept them.
    if last_scan is None:
        scan_from = datetime.datetime(1970,1,1)
        scan_from_str = scan_from.isoformat() + 'Z'
    else:
        scan_from_str = last_scan.scan_datetime.isoformat() + 'Z'
    
    # Build a list of tuples of deployment data - this is a relatively small number of
    # rows of data that are going to get checked repeatedly, so hitting the db for every
    # file is a bottleneck
    deployments = current.db((current.db.recorders.id == current.db.deployments.recorder_id) &
                             (current.db.sites.id == current.db.deployments.site_id)).select()

    # Get the search endpoint within the provided root folder
    # Note that the path collection is always relative to the client root
    # folder (client.folder('0')) regardless of any ancestors provided.
    root_folder = client.folder(root).get()
    # get the time the scan starts, so that any files added during the search
    # aren't missed by the next scan
    scan_started = datetime.datetime.now()
    
    file_search = client.search().query(query='*.mp3', 
                                        ancestor_folders=[root_folder],
                                        file_extensions=['mp3'],
                                        created_at_range=(scan_from_str, None), 
                                        type='file',
                                        fields=['name', 'id', 'path_collection'])
    
    new_known = 0
    new_unknown = 0
    
    # now iterate over the file search generator
    for this_file in file_search:
        # get the path
        path = [dir.name for dir in this_file.path_collection['entries']]
        
        # Check the deployment is known,
        # - get the recorder id and date,  currently from hardcoded points in the dir tree
        rec_date = datetime.datetime.strptime(path[date_index], '%Y-%m-%d').date()
        rec_id = path[pi_index]
        
        which_deployment = [(rec_id == dp.recorders.recorder_id) & 
                            (rec_date >= dp.deployments.deployed_from) & 
                            (rec_date <= dp.deployments.deployed_to) for dp in deployments]
        
        if True in which_deployment:
            # TODO - this assumes deployments don't overlap and chooses the first if they do.
            deployment_record = deployments[which_deployment.index(True)]
            did = deployment_record.deployments.id
            sid = deployment_record.deployments.site_id
            hab = deployment_record.sites.habitat
        else:
            did = None
            sid = None
            hab = None
        
        # Is the file already known
        if not current.db.audio(box_id=this_file.id):

            rec_start = datetime.datetime.strptime(this_file.name[:8], '%H-%M-%S').time()
            rec_datetime = datetime.datetime.combine(rec_date, rec_start)
            
            current.db.audio.insert(deployment_id=did,
                                    site_id=sid,
                                    habitat=hab,
                                    recorder_id=rec_id,
                                    filename=this_file.name,
                                    record_datetime=rec_datetime,
                                    start_time=rec_start,
                                    length_seconds=1200,
                                    box_dir=os.path.join(*path),
                                    box_id=this_file.id,
                                    box_url=None)
            if did is None:
                new_unknown +=1
            else:
                new_known += 1
    
    # Insert the new scan date
    current.db.box_scans.insert(scan_datetime=scan_started,
                                known_total=current.db(current.db.audio.site_id).count(),
                                unknown_total=current.db(current.db.audio.site_id == None).count(),
                                known_new=new_known,
                                unknown_new=new_unknown)
    
    current.db.commit()
    
    return dict()


def crawl_audio_tree(client, root_id):
    
    """
    Crawls through the folder structure indexing MP3 files. This approach uses
    the folder structure, which is good for a first pass but search is needed
    to have a sensible update method

    :param client: An authorised Box API client instance
    :param root: A Box object ID for the starting folder
    """

    # get the root RPiID directories
    root_folder = client.folder(root_id).get(fields=['name'])
    root_contents = root_folder.get_items_marker(fields=['name', 'id'])
    rpiid_folders = [itm.id for itm in root_contents if itm.name.startswith('RPiID')]

    unknown_deployments = []
    n_new = 0
    
    # now search the date folders within each rpiid
    for current_rpiid in rpiid_folders:

        current_rpiid = client.folder(current_rpiid).get(fields=['name'])

        date_folders = current_rpiid.get_items_marker(fields=['name', 'id', 'path_collection'])

        for date in date_folders:
            
            if date.name == 'logs':
                continue
            
            items = date.get_items_marker(fields=['name', 'id'])
            
            # Check this is within a known deployment
            rec_date = datetime.datetime.strptime(date.name, '%Y-%m-%d').date()
            deployed = current.db((current.db.recorders.recorder_id == current_rpiid.name) &
                                  (current.db.recorders.id == current.db.deployments.recorder_id) &
                                  (current.db.deployments.deployed_from <= rec_date) &
                                  (current.db.deployments.deployed_to >= rec_date)).select()
            
            if len(deployed) == 0:
                unknown_deployments.append(current_rpiid.name + '/' + date.name)
            else:
                deployment_id = deployed.first().deployments.id
                # Loop over the items generator, storing audio files
                for itm in items:
                    if itm.type == u'file' and itm.name.endswith(u'.mp3'):
                    
                        if not current.db.audio(box_id=itm.id):
                            
                            n_new += 1
                            path = current_rpiid.name + '/' + date.name + '/' + itm.name
                            rec_start = datetime.datetime.strptime(itm.name[:8], '%H-%M-%S').time()
                            current.db.audio.insert(deployment=deployment_id,
                                                    filename=itm.name,
                                                    record_date=rec_date,
                                                    start_time=rec_start,
                                                    length_seconds=1200,
                                                    static_filepath= path,
                                                    box_id=itm.id,
                                                    box_url=None)
    
        current.db.commit()
    
    return dict(unknown_deployments=unknown_deployments, n_new=n_new)
#
# def get_shared_audio_url(record_id):
#
#     """
#     Function to get a download url for a file
#
#     :param record_id: Audio Record ID
#     :returns A url for the file
#     """
#
#     audio = db.audio[record_id]
#
#     if audio.box_url is None:
#         # Get a shared download link from the file object
#         try:
#             file_info = box_client.file('247440796746').get(fields=['authenticated_download_url'])
#             url = file_info.authenticated_download_url
#             # url = box_client.file('247440796746').get_shared_link_download_url(access=u'open')
#             audio.update_record(box_url = url)
#             return url
#         except BoxAPIException:
#             return None
#     else:
#         return audio.box_url
#
#
# def get_audio_url(file_id):
#
#     """
#     Function to look for the download url for a file in the ram cache
#     and get a fresh one if it isn't there.
#
#     :param file_id: Unicode representation of Box file ID
#     :returns A url for the file
#     """
#     cache_key = 'box_file_' + file_id
#     url = cache.ram(cache_key, lambda: refresh_download_url(box_client, file_id),
#                     time_expire=2*60)
#     return url


def get_download_url(client, file_id):
    """
    Function to pull a dl.cloudbox.com download URL for a file.
    These links expire, so this needs to be done before loading
    a file.

    :param client: An authorised Box API client instance
    :param file_id: The unicode ID of the Box file
    :return: A URL for the audio file
    """

    # Get the file object, just grabbing the download_url field to
    # reduce the size of the data request, and fail gracefully if
    # the file isn't found
    try:
        # file_info = client.file(file_id).get(fields=['authenticated_download_url'])
        file_info = client.file(file_id).get(fields=['download_url'])
    except BoxAPIException as e:
        return None

    # Check the object actually has a download url before we try
    # and return it.
    if hasattr(file_info, 'download_url'):
        return file_info.download_url
    else:
        return None
