# -*- coding: utf-8 -*-

from gluon.serializers import json
import itertools
import matplotlib.colors as colors


def index():

    return dict()


def sites():

    """
    Returns a JSON dict of sites and links to add markers to the map
    """

    # select the site locations, counting the audio at each
    sitedata = db(db.sites).select(db.sites.ALL,
                                   db.audio.id.count().with_alias('n_audio'),
                                   left=db.sites.on(db.sites.id == db.audio.site_id),
                                   groupby=db.sites.id)

    sitedata = json(sitedata)

    return dict(sitedata=sitedata)


def player():

    """
    Exposes the wavesurfer player, loading a particular audio file
    and the calls associated with it
    """

    if request.vars['audio_id']:
        record = db.audio(request.vars['audio_id'])
        if record is None:
            # session.flash('Invalid audio ID')
            redirect(URL('recordings'))
    else:
        # session.flash('No audio ID')
        redirect(URL('recordings'))

    # Get a link to the audio on box
    audio_url = get_audio_url(record.box_id)
    #audio_url = get_shared_audio_url(record.id)

    # get the calls associated with this audio
    calls_block, regions = calls_data(record.id)


    # pass summary data of identifications to allow javascript
    # to load ids for a selected call on the client side
    return dict(record=record, calls_block=calls_block,
                regions=regions, audio_url=audio_url)


def calls_data(id):

    """
    Function to return html for the calls associated with a given recording,
    which can be called to load player() and to update the call_block container
    via AJAX when calls are added, to avoid reloading audio.

    :param id:
    :return:
    """

    # query using left joins to get calls and - if any - the proposed
    # identifications associated with each call.
    left_joins = [db.identifications.on(db.calls.id == db.identifications.call_id),
                  db.taxa.on(db.identifications.taxon_id == db.taxa.id)]

    query = (db.calls.audio_id == id)

    data = db(query).select(db.calls.id,
                            db.calls.start_time,
                            db.calls.end_time,
                            db.identifications.id,
                            db.identifications.current_score,
                            db.identifications.n_scores,
                            db.taxa.ALL,
                            left=left_joins,
                            orderby=db.calls.start_time)

    # Build the data into a list of call list items with collapsible blocks of
    # identification list items

    if len(data) > 0:
        # build the data into a dictionary of identifications by call id
        # NB: This groupby relies on DB query above ordering by the key!
        data = {k: list(g) for k, g in itertools.groupby(data, lambda x: x.calls.id)}

        # now get an order of call ids by start time
        st_time = {k: v[0].calls.start_time for k, v in data.iteritems()}
        st_order = sorted(st_time, key=lambda k: st_time[k])

        # The structure here is a list-group of the call information, each of which is followed
        # by its own nested list group of the identifications, which are collapsible. So, users
        # will always see a list of calls, but the ids are controllable.
        items = []

        for cid in st_order:
            # call header row, showing play and link to call page. There is always
            # at least one row associated with a call but it may have no ident info
            cinfo = data[cid][0]

            # format some information for the call bar
            if cinfo.identifications.id is None:
                n_ident = B('No identifications proposed')
            else:
                n_ident = len(data[cid])
                n_ident = B(
                    str(n_ident) + ' identification' + 's' * bool(n_ident - 1) + ' proposed')

            # get the time range as minutes and seconds
            def ms_format(seconds):
                delta = datetime.timedelta(seconds=seconds)
                return (datetime.datetime(2000,1,1) + delta).strftime('%M:%S')

            start_time = ms_format(cinfo.calls.start_time)
            end_time = ms_format(cinfo.calls.end_time)
            diff = cinfo.calls.end_time - cinfo.calls.start_time
            # convert to datetime to use formatting
            tm_string = I(start_time, XML('&nbsp;&ndash;&nbsp;'),
                          end_time, ' ({:.1f} seconds)'.format(diff))

            # create the call bar
            call_info = LI(SPAN(_class="glyphicon glyphicon-lg glyphicon-play-circle",
                                _id='play_call_' + str(cid)),
                           XML('&nbsp'), n_ident, XML('&nbsp'), tm_string,
                           A(SPAN(_class="glyphicon glyphicon-lg glyphicon-info-sign pull-right"),
                             _href=URL('call_player', vars={'call_id': cid})),
                           _class='list-group-item call_info',
                           _onmouseover='highlight_call(this)',
                           _onmouseout='dehighlight_call(this)',
                           _id='call_' + str(cid))

            items.append(call_info)

            # Compile identification information for this call if there is any
            idents = data[cid]
            if data[cid][0].identifications.id is None:
                ids_list = [
                    LI("No identification proposed", _class='list-group-item small call_id')]
            else:
                # append all the idents onto a list
                ids_list = []
                for rw in data[cid]:
                    ids_list.append(LI(DIV(DIV(rw.taxa.common_name, ' (',
                                               I(rw.taxa.genus, ' ', rw.taxa.species), ')',
                                               _class='col-sm-6'),
                                           _votebar(rw.identifications.current_score,
                                                    rw.identifications.n_scores,
                                                    rw.identifications.id, ),
                                           _class='row'),
                                       _class='list-group-item small call_id'))

            # append the identifications as a collapiblelist group
            items.append(DIV(ids_list, _class='list-group collapse', _id='idents_' + str(cid)))

        calls_block = DIV(DIV("{} calls marked in this recording".format(len(data)),
                              _class="panel-heading panel-warning"),
                          DIV(*items, _class="panel list-group"),
                          _class="panel panel-default")

        # Create a JSON object to send to wavesurfer_js region properties
        # # - start is a reserved word in the web2py framework so can't be used directly
        # # - add an attribute to identify new regions from existing ones.
        regions = []
        for cl in data.values():
            regions.append({'start': cl[0].calls.start_time,
                            'end': cl[0].calls.end_time,
                            'id': cl[0].calls.id,
                            'attributes': {'type': 'fixed'}})

        regions = json(regions)
    else:
        calls_block = DIV(DIV(DIV("No calls yet marked this recording",
                                  _class="panel-heading panel-warning"),
                              _class="panel panel-default"),
                          _class="container")
        regions = []

    return calls_block, regions


def _seconds_to_time(val):

    m = int(val // 60)
    s = int(val % 60)
    ts = int(val % 1 * 10)

    return '{}:{}.{}'.format(m,s,ts)


# TODO
# - what to do about extracting calls to a single file? At the moment
#   the client browser loads the audio from Box, so the data is not
#   available to the server to subset.

# @auth.requires_login()
# def create_call():
#
#     audio_id = request.vars['audio_id']
#     call_note = request.vars['call_note']
#
#     source_file = db.audio[audio_id].filename
#     source_path = os.path.join(request.folder, 'static', 'audio', source_file)
#     start = float(request.vars['start'])
#     end = float(request.vars['end'])
#
#     call_id = _extract_call_and_add_to_db(source_path, audio_id, start,
#                                           end, auth.user.id, call_note)

#     redirect(URL('default', 'player', vars={'audio_id': audio_id}))

@auth.requires_login()
def create_call():

    audio_id = int(request.vars['audio_id'])
    note = request.vars['note']
    start = float(request.vars['start'])
    end = float(request.vars['end'])

    # insert the record into the database
    call_id = db.calls.insert(audio_id=audio_id,
                              start_time=start,
                              end_time=end,
                              created_by=auth.user_id,
                              created_on=datetime.datetime.now(),
                              call_note=note)

    # get the updated calls block content
    calls_block, regions = calls_data(audio_id)

    return json(dict(calls_block=XML(calls_block), regions=regions))


@auth.requires_login()
def my_vote():

    """
    Inserts a user vote for a particular ID, note that the system keeps
    a record of previous votes, rather than just updating them, so the
    previous votes are flagged as replaced. Then calculates and updates
    the weighted mean for the identification
    """

    # get the variables from the call
    id_id = request.vars['id']
    score = request.vars['score']

    # get any existing scores by this user for this id
    # and update them as replaced
    db((db.scores.user_id == auth.user_id) &
       (db.scores.identification_id == id_id)).update(replaced=True)

    # put in the new values
    db.scores.insert(identification_id=id_id, user_id=auth.user_id,
                     score=score, datetime=datetime.datetime.now())

    # update the identifications with the new score
    these_scores = db((db.scores.identification_id == id_id) &
                      (db.auth_user.id == db.scores.user_id) &
                      (db.scores.replaced == False))

    # get the scores and skills associated with them
    # and calculate their weighted meanand the number of scores
    id_score  = these_scores.select(((db.auth_user.id_skill * db.scores.score).sum() /
                                     (db.auth_user.id_skill).sum()).with_alias('wt_mean'),
                                    db.scores.score.count().with_alias('n_scores')).first()

    db(db.identifications.id == id_id).update(current_score=id_score['wt_mean'],
                                              n_scores=id_score['n_scores'])

    # format the response as a JSON object to be
    # handled by the my_vote JS function
    n_votes = str(id_score['n_scores']) + ' vote' + ('s' * (not (id_score['n_scores'] == 1)))

    resp = json(dict(width=_score_to_width(id_score['wt_mean']),
                     barcol=colors.rgb2hex(score_sm.to_rgba(id_score['wt_mean'])),
                     n_votes=n_votes))

    return resp


@auth.requires_login()
def update_comments():

    """
    Controller to capture new discussion comments and pass back
    updated content to the client via AJAX
    """

    # insert the new entry
    comment_text = request.post_vars.comment_text
    call_id = request.vars.call_id

    db.discussion.insert(call_id=call_id, user_id=auth.user_id,
                         comment_text=comment_text, datetime=datetime.datetime.now())

    # put together the new content
    discussion = db(db.discussion.call_id == call_id).select()

    if len(discussion) == 0:
        discussion_content = [LI('Start the discussion here', _class='list-group-item call_info')]
    else:
        discussion_content = [LI(B(d.user_id.first_name + ' ' + d.user_id.last_name) + ' ' +
                                    d.datetime.isoformat() +
                                  MARKMIN(d.comment_text), _class='list-group-item call_info')
                             for d in discussion]

    discussion_group = DIV(*discussion_content, _class="list-group call-info", _id='discussion')

    return XML(discussion_group)


def identifications():

    # Create only applies to logged in users
    form = SQLFORM.grid((db.identifications.taxon_id == db.taxa.id),
                        fields = [db.taxa.common_name, db.taxa.genus,
                                  db.taxa.species, db.taxa.subspecies,
                                  db.identifications.current_score,
                                  db.identifications.n_scores],
                        csv=False,
                        create=True,
                        editable=False,
                        details=True,
                        deletable=False)

    return dict(form=form)


def calls():

    links = [dict(header = '',
                  body = lambda row: A(SPAN('',_class="glyphicon glyphicon-play"),
                                       XML('&nbsp;'),
                                       SPAN('Play', _class="buttontext button"),
                                       _class="btn btn-default",
                                       _href=URL("call_player", vars={'call_id':row.id}),
                                       _style='padding: 3px 5px 3px 5px;'))]

    # retrieve the calls
    form = SQLFORM.grid(db.calls.id,
                        fields=[db.calls.audio_id, db.calls.start_time,
                                db.calls.end_time],
                        #left=db.identifications.on(db.calls.id == db.identifications.call_id),
                        #groupby=[db.calls.audio_id, db.calls.start_time, db.calls.end_time],
                        links=links,
                        csv=False,
                        create=False,
                        editable=False,
                        details=False,
                        deletable=False)

    return dict(form=form)


def call_player():

    # retrieve the call id and audio
    if request.vars['call_id']:
        record = db.calls(request.vars['call_id'])
        audio = db.audio(record.audio_id)
    else:
        # TODO - where to redirect to
        redirect('index')

    # get the identifications for this call
    idents_query = db((db.identifications.call_id == record.id) &
                      (db.identifications.taxon_id == db.taxa.id) &
                      (db.identifications.user_id == db.auth_user.id))

    ident_rows = idents_query.select(db.identifications.id,
                                     db.identifications.created_on,
                                     db.identifications.current_score,
                                     db.identifications.n_scores,
                                     db.taxa.ALL,
                                     db.auth_user.first_name,
                                     db.auth_user.last_name)

    # get a list of arguments to set data- options, can't set
    # arguments with a hyphen in the function
    items = []

    if len(ident_rows) == 0:
        items.append(LI("No identifications have been proposed for this call",
                        _class='list-group-item call_info'))

    for r in ident_rows:

        # only logged in userse get vote buttons.
        if auth.is_logged_in():
            voter = DIV(DIV(_vote_options(r.identifications.id), _class='col-sm-8'),
                            DIV('Your vote', _class='col-sm-4'),
                            _class='row')
        else:
            voter = DIV()

        # Identification block showing species, proposer and controls
        ident_info = LI(DIV(DIV(IMG(_src=URL('static', 'taxa', args=r.taxa.thumbnail),
                                    _width="50", _class="media-object"),
                                _class="media-left"),
                            DIV(DIV(H5(A(XML('{} (<i>{} {}</i>)'.format(r.taxa.common_name,
                                           r.taxa.genus,  r.taxa.species)),
                                           _href=URL('default','taxon', vars={'taxon_id': r.taxa.id})),
                                           _class='media-heading'),
                                        TAG.small(' Proposed by {} {} on {}.'.format(r.auth_user.first_name,
                                                  r.auth_user.last_name, r.identifications.created_on)),
                                    _class='col-sm-6'),
                                DIV(DIV(_votebar(r.identifications.current_score,
                                                 r.identifications.n_scores,
                                                 r.identifications.id,
                                                 grid=['col-sm-8', 'col-sm-4']),
                                        _class='row'),
                                    voter,
                                    _class='col-sm-6'),
                                _class='media-body'),
                            _class="media"),
                        _class='list-group-item call_info')

        items.append(DIV(ident_info, _id='ident' + str(r.identifications.id)))

    ident_group = DIV(*items, _class="panel list-group")

    # return any discussion and the form to extend it
    discussion = db(db.discussion.call_id == record.id).select()

    if len(discussion) == 0:
        discussion_content = [LI('Start the discussion here', _class='list-group-item call_info')]
    else:
        discussion_content = [LI(B(d.user_id.first_name + ' ' + d.user_id.last_name) + ' ' +
                                    d.datetime.isoformat() +
                                  MARKMIN(d.comment_text), _class='list-group-item call_info') for d in discussion]

    discussion_group = DIV(*discussion_content, _class="list-group call-info", _id='discussion')

    return dict(record=record, audio=audio, ident_group=ident_group,
                discussion_group=discussion_group)


def recordings():

    links = [dict(header = '',
                  body = lambda row: A(SPAN('',_class="glyphicon glyphicon-play"),
                                       XML('&nbsp;'),
                                       SPAN('Play', _class="buttontext button"),
                                       _class="btn btn-default",
                                       _href=URL("player", vars={'audio_id':row.audio.id}),
                                       _style='padding: 3px 5px 3px 5px;'))]

    form = SQLFORM.grid((db.audio.site_id == db.sites.id),
                        fields=[db.sites.site_name, db.audio.filename, db.audio.record_date,
                                db.audio.start_time, db.audio.length_seconds],
                        csv=False,
                        create=False,
                        editable=False,
                        details=False,
                        deletable=False,
                        links=links)

    return dict(form=form)


def taxa():

    # Create only applies to logged in users
    db.taxa.created_on.writable = False
    db.taxa.created_by.writable = False
    db.taxa.created_on.readable = False
    db.taxa.created_by.readable = False
    #db.taxa.thumbnail.readable = False

    # locally update the representation to style the image and link columns
    # unlike using links, this allows ordering
    db.taxa.thumbnail.represent = lambda id, row: IMG(_src = URL('default', 'download', args = row.thumbnail),
                                        _width = 50, _height = 50)

    db.taxa.id.represent = lambda id, row: A(SPAN('',_class="glyphicon glyphicon-eye-open"),
                           XML('&nbsp;'),
                           SPAN('View', _class="buttontext button"),
                           _class="btn btn-default btn-sm",
                           _href=URL("taxon", vars={'taxon_id': id}))

    form = SQLFORM.grid(db.taxa,
                        fields = [db.taxa.thumbnail, db.taxa.common_name,
                                  db.taxa.binomial, db.taxa.id],
                        headers = {'taxa.thumbnail': "", "taxa.id": 'Link'},
                        csv=False,
                        create=True,
                        editable=False,
                        details=False,
                        deletable=False,
                        maxtextlength=50,
                        onvalidation=validate_taxon)

    return dict(form=form)


def validate_taxon(form):

    """
    Method to let the normal SQLFORM GRID handle
    adding the user id and time to new taxa
    """

    form.vars.created_by = auth.user_id
    form.vars.created_on = datetime.datetime.now()


def taxon():

    """
    Custom viewer for taxa
    """

    # get a valid record
    if request.vars['taxon_id']:
        record = db.taxa(request.vars['taxon_id'])
        if record is None:
            session.flash = 'Unknown taxon id specified'
            redirect(URL('default','taxa'))
    else:
        session.flash = 'No taxon id specified'
        redirect(URL('default','taxa'))


    # get any calls that this has been proposed for
    idents = db(db.identifications.taxon_id == record.id).select()

    if len(idents) == 0:
        id_list = [LI("No identification proposed", _class='list-group-item small call_id')]
    else:
        # append all the idents onto a list
        idnt_list = []
        for rw in idents:
            cl_id = str(rw.call_id)
            audio = TAG.audio(TAG.source(_src=URL('static', 'calls/call_{}.mp3'.format(cl_id)),
                                         _type="audio/mp3"),
                              _onended='playEnd({})'.format(cl_id), _id='audio_' + cl_id)
            idnt_list.append(LI(DIV(DIV(SPAN(audio, _id='play_' + cl_id,
                                            _class='glyphicon glyphicon-play',
                                            _onclick='playCall({});'.format(cl_id)),
                                        _class='col-sm-1'),
                                    DIV(A('Call ID ' + cl_id,
                                        _href=URL('default','call_player',
                                                  vars={'call_id': rw.call_id})),
                                        _class='col-sm-5'),
                                    _votebar(rw.current_score, rw.n_scores, rw.id),
                                    _class='row'),
                                _class='list-group-item call_id'))

    idents = DIV(*idnt_list, _class="panel list-group")

    return dict(record=record, idents=idents)


@auth.requires_login()
def propose_identification():

    """
    This is just a modified version of the taxa SQLFORM to
    provide a searchable interface for assigning new id proposals
    """

    call_id = request.vars.call_id

    links = [dict(header = '',
                  body = lambda row: A(SPAN('',_class="glyphicon glyphicon-ok"),
                                       XML('&nbsp;'),
                                       SPAN('Propose', _class="buttontext button"),
                                       _class="btn btn-default btn-sm",
                                       _href=URL("submit_proposal", vars={'call_id':call_id, 'taxon_id':row.id})))]

    # Create only applies to logged in users
    form = SQLFORM.grid(db.taxa,
                        fields = [db.taxa.common_name, db.taxa.genus,
                                  db.taxa.species, db.taxa.subspecies],
                        csv=False,
                        create=False,
                        editable=False,
                        details=False,
                        deletable=False,
                        links=links)

    return dict(form=form)


@auth.requires_login()
def submit_proposal():

    """
    Takes a select taxon and call_id and adds it into the identifications table
    """

    call_id = request.vars.call_id
    taxon_id = request.vars.taxon_id

    exists = db((db.identifications.call_id == call_id) &
                (db.identifications.taxon_id == taxon_id)).select()

    if len(exists) > 0:
        session.flash = 'That taxon has already been proposed for this call.'
    else:
        db.identifications.insert(call_id = call_id,
                                  taxon_id = taxon_id,
                                  user_id = auth.user_id,
                                  created_on = datetime.datetime.now())

    redirect(URL('default','call_player', vars={'call_id': call_id}))

    return dict()


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


