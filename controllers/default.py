# -*- coding: utf-8 -*-

from gluon.serializers import json
import itertools
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
# These controllers expose simple tables of the various options, and login
# exposes the edit controllers, which are otherwise suppressed.
# ---

def sites():

    """
    Provides a data table of the sites data
    """

    form = SQLFORM.grid(db.sites,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

def recorders():

    """
    Provides a data table of the recorders data
    """

    form = SQLFORM.grid(db.recorders,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

def deployments():

    """
    Provides a data table of the deployments
    """

    form = SQLFORM.grid(db.deployments,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

def box_scans():

    """
    Provides a data table of the deployments
    """

    form = SQLFORM.grid(db.box_scans,
                        orderby=~db.box_scans.scan_datetime,
                        searchable=False,
                        deletable=False,
                        editable=False,
                        create=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

def audio():
    
    """
    Provides a data table of the audio data
    """
    
    db.audio.record_datetime.represent = lambda val, row: val.date().isoformat()
    
    form = SQLFORM.grid(db.audio,
                        fields=[db.audio.site_id, 
                                db.audio.record_datetime,
                                db.audio.start_time],
                        create=False,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)
    

# ---
# Controller to run the box scan - this should be a background task
# ---

@auth.requires_login()
def scan_box():
    """
    This controller runs the scanning process. This should probably
    be run a cron job but for the moment this URL runs it for Admins
    """
    
    root = myconf.take('box.data_root')
    
    box.scan_box(box_client, root)

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


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@service.json
def get_latest_recording(site_id):
    
    
    qry = db(db.audio.site_id == site_id)
    row = qry.select(db.audio.ALL,
                     orderby=~db.audio.record_datetime,
                     limitby=(0,1)).first()
    
    if row is None:
        return json({})
    else:
        return row.as_json()


@service.json
def get_previous_recording(audio_id):
    
    audio_record = db.audio[audio_id]
    
    qry = db((db.audio.site_id == audio_record.site_id) &
             (db.audio.record_datetime < audio_record.record_datetime))
    row = qry.select(db.audio.ALL,
                     orderby=~db.audio.record_datetime,
                     limitby=(0,1)).first()
    
    if row is None:
        return json({})
    else:
        return row.as_json()


@service.json
def get_next_recording(audio_id):
    
    audio_record = db.audio[audio_id]
    
    qry = db((db.audio.site_id == audio_record.site_id) &
             (db.audio.record_datetime > audio_record.record_datetime))
    row = qry.select(db.audio.ALL,
                     orderby=db.audio.record_datetime,
                     limitby=(0,1)).first()
    
    if row is None:
        return json({})
    else:
        return row.as_json()


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
    
    # select the site locations, counting the audio at each
    sitedata = db().select(db.sites.id,
                           db.sites.site_name,
                           db.sites.short_desc,
                           db.sites.long_desc,
                           db.sites.latitude,
                           db.sites.longitude,
                           db.audio.id.count().with_alias('n_audio'), 
                           left=db.audio.on(db.audio.site_id == db.sites.id),
                           groupby=db.sites.id)
    
    # package more sensibly
    _  = [rec['sites'].update(n_audio=rec['n_audio']) for rec in sitedata]
    sitedata = [rec.pop('sites') for rec in sitedata]
    
    if sitedata is None:
        return json([])
    else:
        return json(sitedata)

