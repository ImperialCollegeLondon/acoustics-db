# -*- coding: utf-8 -*-

from gluon.serializers import json
from itertools import tee, izip
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
                         _href=URL("default","simple_player", vars={'audio_id': row.id}))
                        
    ply2 = lambda row: A(SPAN(_class='glyphicon glyphicon-equalizer'), 
                         _class='btn btn-sm btn-default',
                         _href=URL("default","player", vars={'audio_id': row.id}))
    
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


@auth.requires_login()
def index_audio():
    """
    Controller to run the site by site indexing used to calculate
    next in stream for each recording
    """

    for site in db(db.sites).select():

        _index_site(site.id)


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def start_time_to_seconds(t):
    "datetime.time to seconds since midnight"
    return t.hour * 60 * 60 + t.minute * 60 + t.second


def _index_site(site_id, rec_length=1200, similarity_window=1800):
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
        similarity_window (int): the width of the window in seconds to be
            used to look for recordings with a similar start.
    """

    # get audio records for the site sorted in ascending order
    records = db(db.audio.site_id == site_id).select(orderby=db.audio.record_datetime)

    # need at least two records
    if len(records) < 2:
        return None

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

def player():

    """
    Exposes the wavesurfer player for a given audio id
    """

    if request.vars['audio_id']:
        record = db.audio(request.vars['audio_id'])
        if record is None:
            #session.flash('Invalid audio ID')
            redirect(URL('index'))
    else:
        #session.flash('No audio ID')
        redirect(URL('index'))

    if request.vars['start']:
        start = float(request.vars['start'])
    else:
        start = 0

    # Get a link to the audio on box
    audio_url = box.get_download_url(box_client, record.box_id)

    # pass summary data of identifications to allow javascript
    # to load ids for a selected call on the client side
    return dict(record=record, audio_url=audio_url, start=start)

def simple_player():

    """
    Exposes an audio player for a given audio id
    """

    if request.vars['audio_id']:
        record = db.audio(request.vars['audio_id'])
        if record is None:
            #session.flash('Invalid audio ID')
            redirect(URL('index'))
    else:
        #session.flash('No audio ID')
        redirect(URL('index'))

    if request.vars['start']:
        start = float(request.vars['start'])/record.length_seconds
    else:
        start = 0

    # Get a link to the audio on box
    audio_url = box.get_download_url(box_client, record.box_id)

    # pass summary data of identifications to allow javascript
    # to load ids for a selected call on the client side
    return dict(record=record, audio_url=audio_url, start=start)


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


@service.json
def stream_start():

    """
    Given a start time, returns the details of a recording from which
    to start streaming audio.

    API variables:
        time (float): The time requested by the user.
        most_recent (bool): Use the most recent recording in the time window.
        similarity_window: Width of the window to be used around the start time
            """
    
    if 'time' not in request.vars:
        return

    # build the query
    qry = (db.audio.site_id == site_id)
    
    # Add any filters
    if filters is not None:
        qry &= filters
    
    row = db(qry).select(db.audio.ALL,
                         orderby=~db.audio.record_datetime,
                         limitby=(0,1)).first()
    
    if row is None:
        return json({})
    else:
        return row.as_json()

@service.json
def get_previous_recording(audio_id):
    
    success, filters = _vars_to_filters(request.vars)
    
    ret = _get_next_previous(audio_id, success, filters, 'previous')
    
    return ret


@service.json
def get_next_recording(audio_id):
    
    success, filters = _vars_to_filters(request.vars)
    
    ret = _get_next_previous(audio_id, success, filters, 'next')

    return ret


def _get_next_previous(audio_id, success, filters, direction):

    """
    Function to provide the common function used by the
    get_next_recording and get_previous_recording services.
    """

    # handle failures from filter parsing
    if not success:
        return json(filters)
    
    # build the query
    audio_record = db.audio[audio_id]
    
    if audio_record is None:
        return json(['Unknown record ID'])
    
    # i) recordings from the same site
    qry = (db.audio.site_id == audio_record.site_id)
    
    # ii) next or previous
    if direction == 'next':
        qry &= (db.audio.record_datetime > audio_record.record_datetime)
        ord = ~ db.audio.record_datetime
    else:
        qry &= (db.audio.record_datetime < audio_record.record_datetime)
        ord = db.audio.record_datetime
    
    # iii) Add any filters
    if filters is not None:
        qry &= filters
    
    # Get the first result
    row = db(qry).select(db.audio.ALL,
                         orderby=ord,
                         limitby=(0,1)).first()
    
    if row is None:
        return json({})
    else:
        return row.as_json()


@service.json
def get_paging(audio_id):

    """
    Function to return the ids for the previous and next recording
    and skipping backwards or forwards a day.
    """

    success, filters = _vars_to_filters(request.vars)
    
    # handle failures from filter parsing
    if not success:
        return json(filters)
    
    # Check the focal audio
    audio_record = db.audio[audio_id]
    
    if audio_record is None:
        return json(['Unknown record ID'])
    
    # Build the query
    # - recordings from the same site
    qry = (db.audio.site_id == audio_record.site_id)
    # ii) Add general filters
    if filters is not None:
        qry &= filters
    
    # TODO - currently using four queries. There may be a quicker way!
    
    # Get strict forwards and backwards
    back_qry = qry & (db.audio.record_datetime < audio_record.record_datetime)
    
    back =db(back_qry).select(db.audio.id,
                              orderby=db.audio.record_datetime,
                              limitby=(0,1)).first()

    forw_qry = qry & (db.audio.record_datetime > audio_record.record_datetime)
    
    forw =db(forw_qry).select(db.audio.id,
                              orderby=~db.audio.record_datetime,
                              limitby=(0,1)).first()
    
    # Get similar time forwards and backwards - need a calculation of the similarity 
    # of recording start time to this audio. Annoyingly, datetime.time does not have 
    # a difference method - can promote to datetimes to use timedelta but probably
    # faster just to use quick local function
    
    def tdec(a):
        
        return (a.hour + float(a.minute)/60 + float(a.second)/3600)
    
    def tdiff(a, b):
        diff = abs(tdec(a) - tdec(b))
        
        # wrap around midnight
        if diff > 12:
            diff = 24 - diff
        
        return diff
    
    
    db.audio.tdiff = Field.Virtual('tdiff', lambda row: tdiff(audio_record.start_time, 
                                                              row.audio.start_time))
    
    # Get nearest start time at least one day into the future
    back_24_qry = qry & (db.audio.record_datetime < (audio_record.record_datetime.date() - datetime.timedelta(days=1)))
    
    
    back_24 = db(back_24_qry).select(db.audio.id,
                                     orderby=db.audio.record_datetime,
                                     limitby=(0,1)).first()
    
    
    forw_24_qry = qry & \
                  (db.audio.record_datetime > (audio_record.record_datetime.date() + datetime.timedelta(days=1))) & \
                  (db.audio.tdiff > (tdec(audio_record.start_time) -1 )) & \
                  (db.audio.tdiff < (tdec(audio_record.start_time) + 1 ))
    
    forw_24 =db(forw_24_qry).select(db.audio.id,
                                    orderby=~db.audio.record_datetime,
                                    limitby=(0,1)).first()
    
    ids = [rw.id if rw is not None else None for rw in [back_24, back, forw, forw_24]]
    
    return json(ids)


@service.json
def get_box_link(audio_id):
    
    audio_record = db.audio[audio_id]
    url = box.get_download_url(box_client, audio_record.box_id)
    
    if url is None:
        return json([])
    else:
        return json(url)


@service.json
def get_sites():
    
    success, filters = _vars_to_filters(request.vars)

    if not success:
        return json(filters)
    
    # add any filters for the vars to the left join query
    # on the sites table
    left_join = (db.audio.site_id == db.sites.id)
    
    if filters is not None:
        left_join &= filters
    
    # select the site locations, counting the audio at each
    # TODO - also return ID of most recent recording for each site.
    sitedata = db().select(db.sites.id,
                           db.sites.site_name,
                           db.sites.short_desc,
                           db.sites.long_desc,
                           db.sites.latitude,
                           db.sites.longitude,
                           db.sites.habitat,
                           db.audio.id.count().with_alias('n_audio'),
                           left=db.audio.on(left_join),
                           groupby=db.sites.id)
    
    # package more sensibly
    _  = [rec['sites'].update(n_audio=rec['n_audio']) for rec in sitedata]
    sitedata = [rec.pop('sites') for rec in sitedata]
    
    if sitedata is None:
        return json([])
    else:
        return json(sitedata)

@service.json
def get_habitats():

    return json(HABITATS)

@service.json
def get_recorder_types():

    return json(RECORDER_TYPES)