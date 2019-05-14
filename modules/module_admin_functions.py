import requests
from itertools import tee, izip
import box
import datetime
from gluon import current
from PIL import Image
import io
import pandas
import numpy as np


def populate_gbif_image_occurrences():

    """
    A function to populate the gbif image occurrences table with images
    to provide to the frontend via the API.

    :return: A string containing a report of the scanning process
    """

    taxa = current.db(current.db.taxa).select()

    # An API call to GBIF occurrences limited to human observations with sound or image
    # media that falls within Borneo (otherwise we get swamped by widespread species)
    gbif_api = ("http://api.gbif.org/v1/occurrence/search"
                "?taxonKey={}&mediaType=StillImage&limit={}&offset={}"
                "&geometry=Polygon((108.2 2.9, 108.2 -2.0, 110.2 -4.6, 117.0 -5.9, "
                "121 4.1, 119.5 7.7, 115.1 7.6, 108.2 2.9))"
                "&basisOfRecord=HUMAN_OBSERVATION")

    report = ""
    row_hdr = "{0.scientific_name} ({0.gbif_key}): "

    for this_taxon in taxa:

        # Call the GBIF occurrences API, which has paged output, so iterate
        # over limit sized blocks if needed to get all information.

        end_of_records = False
        limit = 300
        offset = 0
        results = []

        while not end_of_records:
            api_call = gbif_api.format(this_taxon.gbif_key, limit, offset)
            response = requests.get(api_call)

            if response.status_code != 200:
                report += (row_hdr + "GBIF scan failed\n").format(this_taxon)
                end_of_records = True
            else:
                data = response.json()
                report += (row_hdr + "{1} records returned\n").format(this_taxon, len(data['results']))
                results += data['results']
                end_of_records = data['endOfRecords']
                offset += limit

        # Each result is an occurrence, which may reference one more more image or sound files.

        for this_result in results:

            # Do we already have this occurrence?
            if current.db(current.db.gbif_image_occurrences.gbif_occurrence_key == this_result['key']).select():
                continue

            # Does the media include a Sound file? If so, any images are (probably) Sonograms
            media_types = {media['type'] for media in this_result['media']}
            if 'Sound' in media_types:
                continue

            # First, get the occurrence level data, including the species of the occurrence
            # as our taxa can be genus level, and we want to provide precise ids on images.
            insert_data = {'taxon_id': this_taxon.id,
                           'gbif_occurrence_taxon_key': this_taxon.gbif_key,
                           'gbif_occurrence_accepted_name': this_result['acceptedScientificName'],
                           'gbif_occurrence_key': this_result['key'],
                           'gbif_occurrence_license': this_result['license']}

            # Some fields are not always present
            opt_fields = {'gbif_occurrence_behavior': 'behavior',
                          'gbif_occurrence_references': 'references',
                          'gbif_occurrence_rights_holder': 'rightsHolder',
                          'gbif_occurrence_rights': 'rights'}

            for key, val in opt_fields.iteritems():
                if val in this_result:
                    insert_data[key] = this_result[val]

            # loop over the media files
            for this_media in this_result['media']:

                media_data = insert_data.copy()

                media_fields = {'gbif_media_identifier': 'identifier',
                                'gbif_media_format': 'format',
                                'gbif_media_creator': 'creator',
                                'gbif_media_description': 'description'}

                for key, val in media_fields.iteritems():
                    if val in this_media:
                        media_data[key] = this_media[val]

                current.db.gbif_image_occurrences.insert(**media_data)

    # save those inserts
    current.db.commit()

    return report


def populate_gbif_sound_occurrences():

    """
    A function to populate the gbif sound occurrences table  with sounds
    to provide to the frontend via the API.

    :return: A string containing a report of the scanning process
    """

    taxa = current.db(current.db.taxa).select()

    # An API call to GBIF occurrences limited to human observations with sound
    # media that falls within Borneo (otherwise we get swamped by widespread species)
    gbif_api = ("http://api.gbif.org/v1/occurrence/search"
                "?taxonKey={}&mediaType=Sound&limit={}&offset={}"
                "&geometry=Polygon((108.2 2.9, 108.2 -2.0, 110.2 -4.6, 117.0 -5.9, "
                "121 4.1, 119.5 7.7, 115.1 7.6, 108.2 2.9))"
                "&basisOfRecord=HUMAN_OBSERVATION")

    report = ""
    row_hdr = "{0.scientific_name} ({0.gbif_key}): "

    for this_taxon in taxa:

        # Call the GBIF occurrences API, which has paged output, so iterate
        # over limit sized blocks if needed to get all information.

        end_of_records = False
        limit = 300
        offset = 0
        results = []

        while not end_of_records:
            api_call = gbif_api.format(this_taxon.gbif_key, limit, offset)
            response = requests.get(api_call)

            if response.status_code != 200:
                report += (row_hdr + "GBIF scan failed\n").format(this_taxon)
                end_of_records = True
            else:
                data = response.json()
                report += (row_hdr + "{1} records returned\n").format(this_taxon, len(data['results']))
                results += data['results']
                end_of_records = data['endOfRecords']
                offset += limit

        # Each result is an occurrence, which may reference one more more image or sound files.

        for this_result in results:

            # Do we already have this occurrence?
            if current.db(current.db.gbif_sound_occurrences.gbif_occurrence_key == this_result['key']).select():
                continue

            # First, get the occurrence level data, including the species of the occurrence
            # as our taxa can be genus level, and we want to provide precise ids on images.
            insert_data = {'taxon_id': this_taxon.id,
                           'gbif_occurrence_taxon_key': this_taxon.gbif_key,
                           'gbif_occurrence_accepted_name': this_result['acceptedScientificName'],
                           'gbif_occurrence_key': this_result['key'],
                           'gbif_occurrence_license': this_result['license']}

            # Some fields are not always present
            opt_fields = {'gbif_occurrence_behavior': 'behavior',
                          'gbif_occurrence_references': 'references',
                          'gbif_occurrence_rights_holder': 'rightsHolder',
                          'gbif_occurrence_rights': 'rights'}

            for key, val in opt_fields.iteritems():
                if val in this_result:
                    insert_data[key] = this_result[val]

            # loop over the media files
            for this_media in this_result['media']:

                # media entries for sounds include sonogram pngs, so screen them out
                if this_media['type'] == 'Sound':

                    media_data = insert_data.copy()

                    media_fields = {'gbif_media_identifier': 'identifier',
                                    'gbif_media_format': 'format',
                                    'gbif_media_creator': 'creator',
                                    'gbif_media_description': 'description'}

                    for key, val in media_fields.iteritems():
                        if val in this_media:
                            media_data[key] = this_media[val]

                    current.db.gbif_sound_occurrences.insert(**media_data)

    # save those inserts
    current.db.commit()

    return report


def scan_box():
    """
    This action runs the scanning process. This should probably be run a
    cron job but for the moment this action provides the functionality
    """

    box.scan_box(current.box_client)

    # index_audio()

    assign_time_windows()

    index_day_streams()

    # If this runs from within a controller, then db.commit happens
    # automatically, but if it is run by a scheduler it doesn't
    current.db.commit()

    return "Scan complete"


def rescan_deployments(rescan_all=False):
    """
    This action assigns audio to deployments. They are automatically
    matched when imported but this allows them to be updated when
    deployments are changed. Setting rescan_all rescans all audio, not
    just the audio which didn't match at import.
    """

    # TODO - I suspect this might be faster using the DAL but the code
    #        here can be ripped straight from the box.scan_box() code.

    deployments = current.db((current.db.recorders.id == current.db.deployments.recorder_id) &
                             (current.db.sites.id == current.db.deployments.site_id)).select()

    if rescan_all:
        audio = current.db(current.db.audio).select()
    else:
        audio = current.db(current.db.audio.site_id == None).select()

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

    index_audio()

    assign_time_windows()

    current.db.commit()

# ---
# Indexing: functions to identify the next audio 'in stream' for each recording
# ---


def index_audio():
    """
    Controller to run the site by site indexing used to calculate
    next in stream for each recording
    """

    for site in current.db(current.db.sites).select():
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

    db = current.db

    window_width = int(current.myconf.take('audio.window_width'))

    # # These should work and are much faster but SQLite has an issue with the time extractors
    # # and pure time fields - would work for datetime.

    # db(db.audio).update(time_window=(db.audio.start_time.hour() * 60 * 60 +
    #                                  db.audio.start_time.minutes() * 60 +
    #                                  db.audio.start_time.seconds()) / window_width)
    #
    # db(db.taxon_observations).update(time_window=(db.taxon_observations.start_time.hour() * 60 * 60 +
    #                                               db.taxon_observations.start_time.minutes() * 60 +
    #                                               db.taxon_observations.start_time.seconds()) / window_width)

    # Grabbing the value into python turns it into a time object
    for row in db(db.audio).iterselect():
        t_sec = row.start_time.hour * 60 * 60 + row.start_time.minute * 60 + row.start_time.second
        row.update_record(time_window=t_sec / window_width)

    for row in db(db.taxon_observations).iterselect():
        row.update_record(obs_hour=row.obs_time.hour)


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
    min_size = int(current.myconf.take('audio.min_size'))
    records = current.db((current.db.audio.site_id == site_id) &
                         (current.db.audio.file_size > min_size)).select(orderby=current.db.audio.record_datetime)

    # need at least two records
    if len(records) < 2:
        return None

    similarity_window = int(current.myconf.take('audio.window_width'))

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
            sim_where = ((current.db.audio.start_time > sim_min) &
                         (current.db.audio.start_time < sim_max))
        else:
            sim_where = ((current.db.audio.start_time > sim_min) |
                         (current.db.audio.start_time < sim_max))

        # search the current.db for the next later recording within the similarity window
        later = current.db((current.db.audio.site_id == site_id) &
                           (current.db.audio.record_datetime > rec.record_datetime) &
                           sim_where).select(orderby=current.db.audio.record_datetime)

        if later:
            return later[0].id
        else:
            # if no later recordings in the slot, look for an earlier one
            earlier = current.db((current.db.audio.site_id == site_id) &
                                 (current.db.audio.record_datetime < rec.record_datetime) &
                                 sim_where).select(orderby=~current.db.audio.record_datetime)
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

def index_day_streams():

    """
    Populates the day streams index - this is part of the large api_response
    call that loads the front end with all the data it needs to run. The
    payload will change slowly - basically when new audio is loaded - so
    saving this information in the database avoids a lot of overhead.

    This index generates a 72-list (assuming 20 minute recordings) of the
    sequence of audio files to play for each day and site combination.

    :return:
    """

    # TODO  - This feels really clumsy and over the top, but not thinking
    #         too well at the moment

    db = current.db

    for site in db(db.sites).select():

        audio = db(db.audio.site_id == site.id).select(db.audio.id,
                                                       db.audio.time_window,
                                                       db.audio.site_id,
                                                       db.audio.record_datetime)

        # Convert that data into a matrix of ndays x 72 using pandas
        # to turn the db tuples into a dataframe of indices
        audio = pandas.DataFrame.from_records(audio.as_list())
        audio['date'] = audio.record_datetime.apply(datetime.date.toordinal)

        # get the matrix size
        day_one = audio.date.min()
        nrow = audio.date.max() - day_one + 1
        audio['day_index'] = audio['date'] - day_one

        # create the matrix, insert the data and remove completely empty
        # days, noting the date of retained rows
        audio_matrix = np.zeros((nrow, 72), dtype=np.uint16)
        audio_matrix[audio.day_index, audio.time_window] = audio.id
        ordinal_days = np.arange(0, nrow) + day_one
        non_empty_days = (audio_matrix > 0).sum(axis=1) > 0

        audio_matrix = audio_matrix[non_empty_days, ]
        ordinal_days = ordinal_days[non_empty_days]
        nrow = non_empty_days.sum()

        # now we slide one copy of the matrix up and down another padded
        # copy filling in gaps.
        audio_pad = np.pad(audio_matrix, ((nrow, nrow), (0, 0)), 'constant')

        offsets = np.repeat(np.arange(1, nrow), 2) * np.tile((1, -1), nrow - 1)

        for offset in offsets:

            audio_matrix = np.where(audio_matrix == 0,
                                    audio_pad[(nrow + offset):(nrow * 2 + offset), :],
                                    audio_matrix)

        # audio_matrix will now contain a full set of recordings, except
        # where there is no recording at all in a slot, in which case we just
        # repeat the same recording (hack).

        for idx in np.arange(nrow):

            this_stream = db(db.audio.id.belongs(audio_matrix[idx, :])
                             ).select(orderby=db.audio.time_window)

            this_stream = [{'audio': row.id,
                            'box_id': row.box_id,
                            'date': row.record_datetime.date().isoformat(),
                            'time': row.record_datetime.time().isoformat(),
                            'site': row.site_id} for row in this_stream]

            db.audio_streams.insert(site=site.id,
                                    stream_date=datetime.date.fromordinal(ordinal_days[idx]),
                                    stream_data=this_stream)


def make_thumb(image_id, table='site_images', size=(150, 150)):

    """
    Takes a record number and a table name and inserts a thumbnail of
    the 'image' field in the table into the 'thumb' field.

    :param image_id: A record id
    :param table: The name of a table containing image and thumb fields
    :param size: The resolution of the thumbnail
    :return: None
    """

    # Get the record for the image id
    record = current.db(current.db[table].id == image_id).select().first()

    # Get the image from the table and resize it
    nm, file_obj = current.db[table].image.retrieve(record.image)
    im = Image.open(file_obj)
    im.thumbnail(size, Image.ANTIALIAS)

    # Save that Image object to a file-like object
    outfile = io.BytesIO()
    im.save(outfile, im.format)
    outfile.seek(0)

    # Store the image file using the Field methods and then update the record
    outname = current.db[table].thumb.store(outfile, nm)
    record.update_record(thumb=outname)
