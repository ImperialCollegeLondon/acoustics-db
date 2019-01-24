# -*- coding: utf-8 -*-

from gluon.serializers import json
from itertools import tee, izip
import random
import json as json_package
import box

# common set of export classes to suppress
EXPORT_CLASSES = dict(csv_with_hidden_cols=False,
                      xml=False,
                      html=False,
                      tsv_with_hidden_cols=False,
                      tsv=False)

# ---
# Front page is a map of sites with counts
# ---


def index():

    """
    Controller creates a JSON dict of sites and links to add markers to the map
    """

    # select the site locations, counting the audio at each
    sitedata = db().select(db.sites.ALL,
                           db.audio.id.count().with_alias('n_audio'),
                           left=db.audio.on(db.audio.site_id == db.sites.id),
                           groupby=db.sites.id)
    
    sitedata = json(sitedata)

    return dict(sitedata=sitedata)

# ---
# Pure HTML pages that just need a controller to exist
# ---


def about():
    
    return dict()

# ---
# Publically accessible giant boring table of audio
# ---


def audio():
    
    """
    Provides a data table of the audio data
    """
    
    db.audio.record_datetime.represent = lambda val, row: val.date().isoformat()
    
    # player buttons
    ply1 = lambda row: A(SPAN(_class='glyphicon glyphicon-play'), 
                         _class='btn btn-sm btn-default',
                         _href=URL("default","simple_player", vars={'audio': row.id}))
                        
    ply2 = lambda row: A(SPAN(_class='glyphicon glyphicon-equalizer'), 
                         _class='btn btn-sm btn-default',
                         _href=URL("default","player", vars={'audio': row.id}))
    
    links = [dict(header = '', body = ply1),
             dict(header = '', body = ply2)]
    
    form = SQLFORM.grid(db.audio,
                        fields=[db.audio.site_id, 
                                db.audio.habitat,
                                db.audio.record_datetime,
                                db.audio.start_time],
                        links=links,
                        editable=False,
                        create=False,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

# ---
# Data management tables to expose sites, recorders and deployments
# ---


@auth.requires_login()
def sites():

    """
    Provides a data table of the sites data
    """

    form = SQLFORM.grid(db.sites,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def recorders():

    """
    Provides a data table of the recorders data
    """

    form = SQLFORM.grid(db.recorders,
                        maxtextlength=40,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def deployments():

    """
    Provides a data table of the deployments
    """

    form = SQLFORM.grid(db.deployments,
                        deletable=True,
                        maxtextlength=40,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def box_scans():

    """
    Provides a data table of the box scans
    """

    form = SQLFORM.grid(db.box_scans,
                        orderby=~db.box_scans.scan_datetime,
                        searchable=False,
                        deletable=False,
                        editable=False,
                        create=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def deployment_matching():

    """
    Provides a data table of the unmatched audio
    """
    
    # Why is there no Field .date() method for datetimes?
    qry = db(db.audio.site_id == None).select(db.audio.recorder_id,
                                              db.audio.record_datetime.day().with_alias('day'),
                                              db.audio.record_datetime.month().with_alias('month'),
                                              db.audio.record_datetime.year().with_alias('year'),
                                              orderby=~db.audio.record_datetime,
                                              distinct=True)
    
    return dict(form=SQLTABLE(qry, truncate=None, _class='table table-striped'))


# ---
# Actions: currently run as a callback on a button but 
# should probably get passed to run in the background 
# ---

@auth.requires_login()
def scan_box():
    """
    This action runs the scanning process. This should probably be run a
    cron job but for the moment this action provides the functionality 
    """
    
    root = myconf.take('box.data_root')
    
    box.scan_box(box_client, root)

    index_audio()

    assign_time_windows()


@auth.requires_login()
def rescan_deployments():
    """
    This action assigns audio to deployments. They are automatically
    matched when imported but this allows them to be updated when 
    deployments are changed. Setting all to 1 rescans all audio, not
    just the audio which didn't match at import.
    """
    
    # TODO - I suspect this might be faster using the DAL but the code
    # here can be ripped straight from the box.scan_box() code.

    deployments = db((db.recorders.id == db.deployments.recorder_id) &
                     (db.sites.id == db.deployments.site_id)).select()
    
    if 'all' in request.args:
        audio = db(db.audio).select()
    else:
        audio = db(db.audio.site_id == None).select()
    
    # now iterate over the selected rows
    for row in audio:
        
        # get the path
        which_deployment = [(row.recorder_id == dp.recorders.recorder_id) & 
                            (row.record_datetime.date() >= dp.deployments.deployed_from) & 
                            (row.record_datetime.date() <= dp.deployments.deployed_to) 
                            for dp in deployments]
        
        if True in which_deployment:
            deployment_record = deployments[which_deployment.index(True)]
            row.update_record(deployment_id=deployment_record.deployments.id,
                              site_id=deployment_record.deployments.site_id,
                              habitat=deployment_record.sites.habitat,
                              recorder_type=deployment_record.recorders.recorder_type)
    
    db.commit()

    index_audio()

    assign_time_windows()

# ---
# Indexing: functions to identify the next audio 'in stream' for each recording
# ---


@auth.requires_login()
def index_audio():
    """
    Controller to run the site by site indexing used to calculate
    next in stream for each recording
    """

    for site in db(db.sites).select():

        _index_site(site.id)


def pairwise(iterable):
    """
    Recipe from itertools to turn an iterable into a generator
    yielding successive pairs of entries:
        s -> (s0,s1), (s1,s2), (s2, s3), ...

    Parameters:
        iterable: An iterable object

    Returns:
        A generator giving pairs of entries in iterable
    """

    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def assign_time_windows():
    """
    Calculates the time window for each recording in db.audio and updates
    the database to store the window codes. These windows are used to
    group recordings to provide counts within time windows to the front
    end via the get_site API call.

    Returns:
        None
    """

    window_width = int(myconf.take('audio.window_width'))

    for row in db(db.audio).iterselect():

        t_sec = row.start_time.hour * 60 * 60 + row.start_time.minute * 60 + row.start_time.second
        row.update_record(time_window=t_sec / window_width)


def _index_site(site_id, rec_length=1200):
    """
    Collects all the audio for a site and calculates next in stream
    for each recording. This uses a window of similar start times
    to find a recording i) shortly after each recording, or ii) more
    recently or lastly iii) at a similar earlier time. This stores
    a simple set of indices in the db that provide a reasonably
    consistent sounding route through the audio available at a site.

    Parameters:
        site_id (int): the site id to index
        rec_length (int): the actual lengths of the recordings are not
            easily accessible, so this sets the offset in seconds from
            start_time to be used as the time of the end of the recording.
    """

    # get sufficiently long audio records for the site sorted in ascending order
    min_size = int(myconf.take('audio.min_size'))
    records = db((db.audio.site_id == site_id) &
                 (db.audio.file_size > min_size)).select(orderby=db.audio.record_datetime)

    # need at least two records
    if len(records) < 2:
        return None

    similarity_window = int(myconf.take('audio.window_width'))

    # get the maximum delay between records that counts as continuous
    # similar recordings and the timedelta for either side of start_time
    max_delay = rec_length + similarity_window / 2
    window = datetime.timedelta(seconds=similarity_window / 2)

    def _search_for_next(rec):
        """
        Internal function to find the next_in_stream from the db. Only needed
        when the sort order from the records set doesn't provide a matching
        next_in_stream.

        Returns:
            The db.audio.id of the next_in_stream
        """

        # get the similarity time window as a where condition allowing
        # for wrapping at midnight
        sim_min = (rec.record_datetime - window).time()
        sim_max = (rec.record_datetime + window).time()

        if sim_min < sim_max:
            sim_where = ((db.audio.start_time > sim_min) &
                         (db.audio.start_time < sim_max))
        else:
            sim_where = ((db.audio.start_time > sim_min) |
                         (db.audio.start_time < sim_max))

        # search the db for the next later recording within the similarity window
        later = db((db.audio.site_id == site_id) &
                   (db.audio.record_datetime > rec.record_datetime) &
                   sim_where).select(orderby=db.audio.record_datetime)

        if later:
            return later[0].id
        else:
            # if no later recordings in the slot, look for an earlier one
            earlier = db((db.audio.site_id == site_id) &
                         (db.audio.record_datetime < rec.record_datetime) &
                         sim_where).select(orderby=~db.audio.record_datetime)
            if earlier:
                return earlier[0].id
            else:
                return None

    # Now identify next_in_stream for each record
    for this_rec, next_rec in pairwise(records):

        # get the time to the next recording
        delta = next_rec.record_datetime - this_rec.record_datetime

        if delta.total_seconds() < max_delay:
            # the next record in ascending record datetime is within the max delay
            # of the current record, so call that next in stream
            this_rec.update_record(next_in_stream=next_rec.id)
        else:
            this_rec.update_record(next_in_stream=_search_for_next(this_rec))

    # handle the last record, which will be the most recent at the site
    next_rec.update_record(next_in_stream=_search_for_next(next_rec))

    return None

# ---
# Expose pages to play audio
# ---

def download_url(box_id):
    """
    Simple helper to pair the static download page with the current download access token value

    :param box_id:
    :return:
    """

    url = 'https://dl.boxcloud.com/api/2.0/files/{}/content?access_token={}'.format(box_id, dl_token.access_token)

    return url


def player():

    """
    Exposes the wavesurfer player for a given audio id
    """

    if request.vars['audio']:
        record = db.audio(request.vars['audio'])
        if record is None:
            redirect(URL('index'))
    else:
        redirect(URL('index'))

    if request.vars['start']:
        start = float(request.vars['start'])
    else:
        start = 0

    # Get a link to the audio on box
    audio_url = download_url(record.box_id)

    # pass summary data of identifications to allow javascript
    # to load ids for a selected call on the client side
    return dict(record=record, audio_url=audio_url, start=start)

def simple_player():

    """
    Exposes an audio player for a given audio id
    """

    if request.vars['audio']:
        record = db.audio(request.vars['audio'])
        if record is None:
            redirect(URL('index'))
    else:
        redirect(URL('index'))

    if request.vars['start']:
        start = float(request.vars['start'])/record.length_seconds
    else:
        start = 0

    # Get a link to the audio on box
    audio_url = download_url(record.box_id)

    # return the row information to the player
    return dict(record=record, audio_url=audio_url, start=start)


def play_stream():

    """
    Wraps a player around a call to stream get to allow users to play
    with the interface and hear the audio
    """

    # parse the variables
    if request.vars['time']:
        time = request.vars['time']
    else:
        time = '6.5'

    if request.vars['site']:
        site = request.vars['site']
    else:
        site = 1

    if request.vars['shuffle']:
        shuffle = request.vars['shuffle']
    else:
        shuffle = 0


    # call API
    failed, payload = _stream_get(site, time, shuffle)

    if failed:
        return dict(record={'Failed': payload['error']}, audio_url="")
    else:
        json_data = json_package.loads(payload)
        record = db.audio[json_data['audio']]
        return dict(record=record, audio_url=json_data['url'])


def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())


@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)

# ---
# Call services - could implement as a more RESTFUL API style thing but small set 
# of actions and only GET not any of the rest of the CRUD interface required.
# ---


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


def audio_row_to_json(row):
    """
    Helper function to take a row from the audio table and package
    it up to be served as a JSON response. Shared by stream_start,
    stream_next and stream_play. Note that it relies on the service
    decorator to actually serialise the dict to JSON.
    """

    return {'audio': row.id,
            'box_id': row.box_id,
            'date': row.record_datetime.date().isoformat(),
            'time': row.record_datetime.time().isoformat(),
            'site': row.site_id}

def _stream_get(site, time, shuffle=False):

    """
    This private function holds the engine behind the stream_get call
    and the play_stream controller. One powers a JSON response, the other
    exposes a player that uses the same interface. The code is held here
    so that it is accessible from within the controller.

    Given a start time, returns the details of a recording from which
    to start streaming audio.

    API variables:
        site (int): The id of the site to stream
        time (float): The time requested by the user.
        shuffle (bool): Use the most recent recording in the time window.

    Returns:
        A two tuple of an error code and a data payload
    """

    # parse arguments to API
    try:
        site = int(site)
        site_rec = db.sites[site]
        if not site_rec:
            return 1,  u'{"error": "Unknown Site ID"}'
    except ValueError:
            return 1, u'{"error": "Could not parse Site ID as integer"}'

    try:
        start_time = float(time)
        start_time = datetime.datetime(year=2000, month=12, day=31,
                                       hour=int(start_time),
                                       minute=int((start_time % 1) * 60))
    except ValueError:
        return 1, u'{"error": "Could not parse start time as decimal hour [0.0 - 23.99]"}'

    window = int(myconf.take('audio.window_width'))

    # build the query
    window = datetime.timedelta(seconds=window / 2)
    sim_min = (start_time - window).time()
    sim_max = (start_time + window).time()

    if sim_min < sim_max:
        sim_where = ((db.audio.start_time > sim_min) &
                     (db.audio.start_time < sim_max))
    else:
        sim_where = ((db.audio.start_time > sim_min) |
                     (db.audio.start_time < sim_max))

    # search the db for the next later recording within the similarity window
    min_size = int(myconf.take('audio.min_size'))
    candidates = db((db.audio.site_id == site) &
                    (db.audio.file_size > min_size) &
                    sim_where).select(orderby=~db.audio.record_datetime)

    if len(candidates) == 0:
        return 1, {"error": "No recordings match site and time requested"}
    else:
        if shuffle:
            row = random.choice(candidates)
        else:
            row = candidates[0]

        return 0, audio_row_to_json(row)


@service.json
def stream_get(site, time, shuffle=False):

    """
    Given a start time, returns the details of a recording from which
    to start streaming audio.

    API variables:
        site (int): The id of the site to stream
        time (float): The time requested by the user.
        shuffle (bool): Use the most recent recording in the time window.
    """

    failed, payload = _stream_get(site, time, shuffle)

    if failed:
        raise HTTP(400, payload)
    else:
        return payload


@service.json
def stream_next(audio):

    this_record = db.audio[audio]

    if this_record is None:
        return {}
    else:
        next_record = db.audio[this_record.next_in_stream]

        return audio_row_to_json(next_record)


@service.json
def stream_play(audio):

    this_record = db.audio[audio]

    if this_record is None:
        return {}
    else:
        return audio_row_to_json(this_record)


@service.json
def get_sites():

    # select the site locations, counting the audio at each
    min_size = int(myconf.take('audio.min_size'))
    qry = db.audio.file_size > min_size
    sitedata = db(qry).select(db.sites.id,
                              db.sites.site_name,
                              db.sites.short_desc,
                              db.sites.latitude,
                              db.sites.longitude,
                              db.sites.habitat,
                              db.audio.id.count().with_alias('n_audio'),
                              left=db.audio.on(db.audio.site_id == db.sites.id),
                              groupby=db.sites.id)
    
    # package more sensibly
    _ = [rec['sites'].update(n_audio=rec['n_audio']) for rec in sitedata]
    sitedata = [rec.pop('sites') for rec in sitedata]
    
    if sitedata is None:
        return []
    else:
        return sitedata


@service.json
def get_site(site):

    # Get the site row
    site_data = db.sites[site]

    if site_data is None:
        return {}
    else:
        # Get the audio availability and package into array
        min_size = int(myconf.take('audio.min_size'))
        qry = (db.audio.site_id == site) & (db.audio.file_size > min_size)
        audio_counts = db(qry).select(db.audio.time_window,
                                      db.audio.id.count().with_alias('n_audio'),
                                      groupby=db.audio.time_window)

        n_window = (24 * 60 * 60) / int(myconf.take('audio.window_width'))
        avail = [0] * n_window

        for row in audio_counts:
            avail[row.audio.time_window] = row.n_audio

        site_data.window_counts = avail
        return site_data


@service.json
def get_status():

    # number of sites with audio
    n_sites = len(db(db.audio).select(db.audio.site_id, distinct=True))

    # number of recordings
    min_size = int(myconf.take('audio.min_size'))
    n_audio = db(db.audio.file_size > min_size).count()

    # last scan
    last_scan = db(db.box_scans).select(db.box_scans.ALL,
                                        orderby=~db.box_scans.scan_datetime,
                                        limitby=(0, 1)).first()

    return {'n_sites': n_sites, 'n_audio': n_audio, 'last_scan': last_scan.scan_datetime}


@service.json
def get_habitats():

    return HABITATS


@service.json
def get_recorder_types():

    return RECORDER_TYPES


@service.json
def get_dl_access_token():

    """
    Provides an access token downscoped to provide download only access to files
    within the root audio folder. This token expires.

    :return:
    """

    return {'access_token': dl_token.access_token,
            'expires_in': dl_token.expires_in}


