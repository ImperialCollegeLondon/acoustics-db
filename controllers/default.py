# -*- coding: utf-8 -*-
import os
from gluon.serializers import json
import json as json_package
import module_admin_functions
import time

# common set of export classes to suppress
EXPORT_CLASSES = dict(csv_with_hidden_cols=False,
                      xml=False,
                      html=False,
                      tsv_with_hidden_cols=False,
                      tsv=False)

# ---
# Pure HTML pages that just need a controller to exist
# ---


def index():
    
    last_scan = db(db.box_scans).select(db.box_scans.scan_datetime,
                                        orderby=~db.box_scans.scan_datetime,
                                        limitby=(0,1)).first()
    n_rec = db(db.audio).count()
    
    return dict()

# ---
# Map of sites with counts
# ---

def map():

    """
    Controller creates a JSON dict of sites and links to add markers to the map
    """

    # select the site locations, counting the audio at each
    sitedata = db().select(db.sites.ALL,
                           db.audio.id.count().with_alias('n_audio'),
                           left=db.audio.on(db.audio.site_id == db.sites.id),
                           groupby=db.sites.id)
    
    [site.pop("_extra") for site in sitedata]
    sitedata = json(sitedata)

    return dict(sitedata=sitedata)

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
                                db.audio.start_time,
                                db.audio.recorder_type],
                        links=links,
                        editable=False,
                        create=False,
                        deletable=False,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


def availability():
    
    last_scan = db(db.box_scans).select(db.box_scans.scan_datetime,
                                        orderby=~db.box_scans.scan_datetime,
                                        limitby=(0,1)).first()
    n_rec = db(db.audio).count()
    
    form = SQLFORM.grid(db.box_scans.scan_datetime,
                        db.box_scans.known_total,
                        db.box_scans.known_new,
                        limitby=(0,20),
                        orderby=~db.box_scans.scan_datetime,
                        searchable=False,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        csv=False,
                        showid=False)
    
    return dict(last_scan=last_scan.scan_datetime,
                n_rec=n_rec,
                form=form)

# ---
# Data management tables to expose sites, deployments, scans, audio and taxa
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
def audio_matching():

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


@auth.requires_login()
def taxa():

    """
    Provides a data table of the taxon data
    """

    db.taxa.image.readable = False

    db.taxa.thumb.represent = lambda val, row: IMG(_src=URL('default', 'download', args=row.thumb))

    form = SQLFORM.grid(db.taxa,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

@auth.requires_login()
def taxon_observations():

    """
    Provides a data table of the taxon observation data
    """

    form = SQLFORM.grid(db.taxon_observations,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

@auth.requires_login()
def site_images():

    """
    Provides a data table of the sites data
    """

    db.site_images.thumb.readable = False

    links = [dict(header=T('Image'),
                  body=lambda row: IMG(_src=URL('default', 'download', args=row.thumb)))]

    form = SQLFORM.grid(db.site_images,
                        fields=[db.site_images.habitat,
                                db.site_images.thumb],
                        create=False,
                        editable=True,
                        details=True,
                        deletable=False,
                        links=links,
                        csv=False)

    return dict(form=form)


@auth.requires_login()
def audio_admin():

    """
    Provides a data table of the audio data
    """

    form = SQLFORM.grid(db.audio,
                        create=False,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)

@auth.requires_login()
def gbif_sound_occurrences():

    """
    Provides a data table of the GBIF sounds loaded
    """

    form = SQLFORM.grid(db.gbif_sound_occurrences,
                        fields=[db.gbif_sound_occurrences.id,
                                db.gbif_sound_occurrences.taxon_id,
                                db.gbif_sound_occurrences.gbif_occurrence_accepted_name,
                                db.gbif_sound_occurrences.gbif_occurrence_behavior],
                        maxtextlength=100,
                        create=False,
                        editable=False,
                        deletable=True,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def gbif_image_occurrences():

    """
    Provides a data table of the GBIF images and a linkout to set the gbif
    image to be used for a particular taxon, when local shutterstock images are
    not available.
    """

    links = [dict(header='',
                    body=lambda row: A(SPAN('', _class='glyphicon glyphicon-check'), XML('&nbsp'),
                                       SPAN('Use for taxon', _class="buttontext button"),
                                       _class="button btn btn-default",
                                       _href=URL('default', 'set_gbif_image_for_taxon', vars={'id': row.id}),
                                       _style='padding: 3px 5px 3px 5px;background: green;' if row.use_for_taxon
                                       else 'padding: 3px 5px 3px 5px;'))]

    db.gbif_image_occurrences.use_for_taxon.readable = False

    db.gbif_image_occurrences.gbif_media_identifier.represent = lambda val, row: IMG(_src=val, _width=100)
    form = SQLFORM.grid(db.gbif_image_occurrences,
                        fields=[db.gbif_image_occurrences.id,
                                db.gbif_image_occurrences.taxon_id,
                                db.gbif_image_occurrences.gbif_occurrence_accepted_name,
                                db.gbif_image_occurrences.gbif_media_identifier,
                                db.gbif_image_occurrences.use_for_taxon],
                        maxtextlength=100,
                        create=False,
                        editable=False,
                        deletable=True,
                        links=links,
                        exportclasses=EXPORT_CLASSES)

    return dict(form=form)


@auth.requires_login()
def set_gbif_image_for_taxon():

    """
    Endpoint to set the GBIF image for a particular taxon

    :return:
    """

    if 'id' not in request.vars or db.gbif_image_occurrences[request.vars.id] is None:
        redirect(URL('gbif_image_occurrences'))

    image = db.gbif_image_occurrences[request.vars.id]

    # scrub any existing set image and set the new one
    db(db.gbif_image_occurrences.taxon_id == image.taxon_id).update(use_for_taxon=False)
    image.update_record(use_for_taxon=True)

    # set the taxon table
    taxon = db.taxa[image.taxon_id]
    taxon.update_record(gbif_media_identifier=image.gbif_media_identifier,
                        gbif_media_creator=image.gbif_media_creator,
                        gbif_occurrence_key=image.gbif_occurrence_key)

    redirect(request.env.http_referer)


@auth.requires_login()
def upload_image():

    form = SQLFORM(db.site_images)

    if form.accepts(request.vars, session):
        response.flash = 'form accepted'
        module_admin_functions.make_thumb(form.vars.id)
    elif form.errors:
        response.flash = 'form has errors'

    return dict(form=form)


# ---
# Actions: currently run as a callback on a button but 
# should probably get passed to run in the background 
# ---

@auth.requires_login()
def admin_functions():

    form = SQLFORM.factory(Field('action', label='Select an admin function to run:',
                                 requires=IS_IN_SET(['Scan box for new audio',
                                                     'Rescan missing deployments',
                                                     'Rescan _all_ deployments',
                                                     'Reindex audio streams',
                                                     'Reassign time windows',
                                                     'Update GBIF image occurrences',
                                                     'Update GBIF sound occurrences',
                                                     'Create availability plot',
                                                     ],
                                                     zero=None),
                                 default='Scan box for new audio'))
    report = DIV()

    if form.process().accepted:

        if form.vars.action == 'Scan box for new audio':
            report = module_admin_functions.scan_box()
        elif form.vars.action == 'Rescan missing deployments':
            report = module_admin_functions.rescan_deployments()
        elif form.vars.action == 'Rescan _all_ deployments':
            report = module_admin_functions.rescan_deployments(rescan_all=True)
        elif form.vars.action == 'Reindex audio streams':
            report = module_admin_functions.index_day_streams()
        elif form.vars.action == 'Reassign time windows':
            report = module_admin_functions.assign_time_windows()
        elif form.vars.action == 'Update GBIF image occurrences':
            report = module_admin_functions.populate_gbif_image_occurrences()
        elif form.vars.action == 'Update GBIF sound occurrences':
            report = module_admin_functions.populate_gbif_sound_occurrences()
        elif form.vars.action == 'Create availability plot':
            report = module_admin_functions.make_availability_png()
        else:
            pass

    elif form.errors:
        response.flash = 'form has errors'

    return dict(form=form, report=report)


def _shared_link():

    audio = db(db.audio.shared_link == None).iterselect()
    t = datetime.datetime.now()

    for idx, row in enumerate(audio):

        if (idx % 100) == 0:
            print('{}: {} seconds'.format(idx, (datetime.datetime.now() - t).seconds))

        row.update_record(shared_link=os.path.basename(box_client.file(row.box_id).get_shared_link_download_url()))



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

    # Set response headers
    response.headers['Pragma'] = None
    response.headers['X-Clacks-Overhead'] = 'Ben Collen'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'

    # Dump the session to remove Set-Cookie
    session.forget(response)

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
            'site': row.site_id,
            'type': row.recorder_type}

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
        raise HTTP(400, payload['error'])
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
def get_site_image(site, time=None):
    """
    This provides a download link for a file to represent a site at a
    particular time. At the moment, site is only used to match an image
    by habitat not to a specific site and time is ignored completely - but
    the endpoint is set up like this so that the API call will remain stable
    if we do provide specific site time/images.

    :param site:
    :param time:
    :return:
    """

    # Get the site row
    site_data = db.sites[site]

    # Get an image
    image = db((db.site_images.habitat == site_data.habitat) &
               (db.site_images.hidden == False)).select(
                    limitby=(0, 1),
                    orderby='<random>').first()

    if image:
        return URL('default', 'download', args=image.image, host=True)
    else:
        raise HTTP(404, 'No images found')


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

    expiry_time = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                time.gmtime(cache.ram.storage['dl_token'][0] + 3600))

    response.headers['Cache-Control'] = None
    response.headers['Expires'] = expiry_time

    return dl_token.access_token


@service.json
def get_taxa(site, obs_time=None):

    if not db(db.sites.id == site).select():
        raise HTTP(404, 'Unknown site id')

    if not db(db.taxon_observations.site_id == site).select():
        raise HTTP(404, 'No taxon observations recorded at this site')

    # number of taxa at the site
    qry = ((db.taxa.id == db.taxon_observations.taxon_id) &
           (db.taxon_observations.site_id == site))

    if obs_time is not None:
        try:
            window_width = int(myconf.take('audio.window_width'))
            obs_win = (float(obs_time) *  60 * 60) / window_width
            qry &= (db.taxon_observations.time_window == obs_win)
        except ValueError:
            raise HTTP(404, 'Failed to parse observation time')

    taxa = db(qry).select(db.taxa.ALL, distinct=True)

    return taxa


@service.json
def get_taxon_image(taxon_id):

    # get a taxon image - currently from a pool of GBIF images

    image = db((db.gbif_image_occurrences.taxon_id == taxon_id)
               ).select(db.gbif_image_occurrences.gbif_media_identifier,
                        db.gbif_image_occurrences.gbif_occurrence_key,
                        limitby=(0, 1),
                        orderby='<random>')

    if image:
        return image.render().next()
    else:
        raise HTTP(404, 'No taxon image found')


@service.json
def get_taxon_sounds(taxon_id):

    # get taxon sounds from GBIF occurrence files
    sounds = db((db.gbif_sound_occurrences.taxon_id == taxon_id)
                ).select(db.gbif_sound_occurrences.gbif_media_identifier,
                         db.gbif_sound_occurrences.gbif_occurrence_behavior,
                         db.gbif_sound_occurrences.gbif_occurrence_key)

    if sounds:
        return list(sounds.render())
    else:
        raise HTTP(404, 'No taxon sounds found')


@service.json
def get_taxon_sound(taxon_id):

    # get taxon sounds from GBIF occurrence files
    sounds = db((db.gbif_sound_occurrences.taxon_id == taxon_id)
                ).select(db.gbif_sound_occurrences.gbif_media_identifier,
                         db.gbif_sound_occurrences.gbif_occurrence_behavior,
                         db.gbif_sound_occurrences.gbif_occurrence_key,
                         limitby=(0, 1),
                         orderby='<random>')

    if sounds:
        return sounds.render().next()
    else:
        raise HTTP(404, 'No taxon sounds found')


@service.json
def api_response():

    """
    Implementation of Aaron's 'mega' API to populate the front end with a single
    large payload rather than a set of independent calls to individual components.
    The output of this is largely static, rolling updates of the audio and admin
    updates to the content will happen infrequently, so the response is cached to
    reduce response time.

    See static/api_response.ts for description

    :return:
        A JSON object containing all the data needed to populate the front end.
    """

    response.headers['Cache-Control'] = 'public, max-age=86400'
    response.headers['Expires'] = None
    
    # create and cache the api_response. This never expires, it is just replaced when the 
    # box scan updates the available files.
    content = cache.ram('api_response', lambda: module_admin_functions.api_response(), time_expire=None)
    
    return content


@service.json
def get_files():

    ret = db(db.audio.recorder_type == 'rpi-eco-monitor'
             ).select(db.audio.id,
                      db.audio.box_id,
                      db.audio.record_datetime,
                      db.audio.site_id)

    return ret
