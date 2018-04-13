#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Populates the environment variables from a json file
and authenticates via Jason Web Token
'''

import json
import os
import pandas
import datetime

from boxsdk import JWTAuth, Client
from boxsdk.exception import BoxAPIException

JSON_FILE = os.path.join(request.folder, 'private', '679891_r1z60k7r_config.json')
PRIVATE_KEY_FILE = os.path.join(request.folder, 'private', 'box_private_key.pem')
ROOT_ID = u'13400251912'


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


def crawl_audio_tree(client, root_id):
    """
    Crawls through the folder structure indexing MP3 files.

    :param client: An authorised Box API client instance
    :param root: A Box object ID for the starting folder
    :return: A pandas dataframe containing db rows for the files
    """

    # get the root RPiID directories
    root_folder = client.folder(root_id).get(fields=['name'])
    root_contents = root_folder.get_items_marker(fields=['name', 'id'])
    rpiid_folders = [itm.id for itm in root_contents if itm.name.startswith('RPiID')]

    # pandas dataframe to store file data
    audio = pandas.DataFrame(columns=['site_id', 'filename', 'record_date', 'start_time',
                                      'length_seconds', 'static_filepath', 'box_id'],
                             index=range(0, 100000))
    row_index = 0

    # now search the date folders within each rpiid
    for current_rpiid in rpiid_folders:

        current_rpiid = client.folder(current_rpiid).get(fields=['name'])

        date_folders = current_rpiid.get_items_marker(fields=['name', 'id', 'path_collection'])

        for date in date_folders:

            items = date.get_items_marker(fields=['name', 'id'])

            # Loop over the items generator, storing audio files
            for itm in items:
                if itm.type == u'file' and itm.name.endswith(u'.mp3'):
                    rec_date = datetime.datetime.strptime(date.name, '%Y-%m-%d').date()
                    rec_start = datetime.datetime.strptime(itm.name[:8], '%H.%M.%S').time()
                    path = current_rpiid.name + '/' + date.name + '/' + itm.name
                    audio.loc[row_index] = [current_rpiid.name, itm.name, rec_date, rec_start,
                                            1200, path, itm.id]
                    row_index += 1
                    if row_index % 500 == 0:
                        print(row_index)


def get_shared_audio_url(record_id):

    """
    Function to get a download url for a file

    :param record_id: Audio Record ID
    :returns A url for the file
    """

    audio = db.audio[record_id]

    if audio.box_url is None:
        # Get a shared download link from the file object
        try:
            file_info = box_client.file('247440796746').get(fields=['authenticated_download_url'])
            url = file_info.authenticated_download_url
            # url = box_client.file(audio.box_id).get_shared_link_download_url(access=u'open')
            audio.update_record(box_url = url)
            return url
        except BoxAPIException:
            return None
    else:
        return audio.box_url


def get_audio_url(file_id):

    """
    Function to look for the download url for a file in the ram cache
    and get a fresh one if it isn't there.

    :param file_id: Unicode representation of Box file ID
    :returns A url for the file
    """
    cache_key = 'box_file_' + file_id
    url = cache.ram(cache_key, lambda: refresh_download_url(box_client, file_id),
                    time_expire=2*60)
    return url


def refresh_download_url(client, file_id):
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


box_client = cache.ram('box_client', lambda: authorize_jwt_client_json(JSON_FILE, PRIVATE_KEY_FILE),
                       time_expire=60*60*24)