import datetime
from pydub import AudioSegment
import matplotlib.colors as colors
import matplotlib.cm as cm
import os
import copy

# Table to hold a list of audio files
#  - can't make the previous and next reference the ids as a key
#	 because of insertion order effects!

db.define_table('sites',
	Field('latitude', 'float'),
	Field('longitude', 'float'),
	Field('site_name', 'string'))

db.define_table('audio',
	Field('site_id', 'reference sites'),
	Field('filename', 'string'),
	Field('start_datetime', 'datetime'),
	Field('length_seconds', 'float'),
	Field('static_filepath', 'string'),
	Field('box_id', 'string'))


# Table to identify chunks of audio containing a call
db.define_table('calls',
	Field('audio_id', 'reference audio'),
	Field('start_time', 'float'),
	Field('end_time', 'float'),
	Field('call_note', 'text'),
	Field('created_by', 'reference auth_user'),
	Field('created_on', 'datetime'))


# Table to support identifications
taxa_folder = os.path.join(request.folder,'static','taxa')

# This contains a computed field which is solely used to
# hold a compiled bi/trinomial

db.define_table('taxa',
	Field('created_by', 'reference auth_user'),
	Field('created_on', 'datetime'),
	Field('common_name', 'string'),
	Field('genus', 'string'),
	Field('species', 'string'),
	Field('subspecies', 'string'),
	Field('binomial', 'string', compute = lambda row: ' '.join([row['genus'], 
		row['species'], row['subspecies']]), writable=False),
	Field('thumbnail', 'upload', uploadfolder=taxa_folder, 
		  default= os.path.join(taxa_folder, 'default.jpg')))

# Table to attach identifications to a call
db.define_table('identifications',
	Field('call_id', 'reference calls'),
	Field('user_id', 'reference auth_user'),
	Field('taxon_id', 'reference taxa'),
	Field('created_on', type='datetime'),
	Field('current_score', type='float', default=0),
	Field('n_scores', type='integer', default=0))

# Table to score identifications
db.define_table('scores',
	Field('identification_id', 'reference identifications'),
	Field('user_id', 'reference auth_user'),
	Field('score', type='integer'),
	Field('datetime', 'datetime'),
	Field('replaced', type='boolean', default=False))

# Table for discussion on calls
db.define_table('discussion',
	Field('call_id', 'reference calls'),
	Field('user_id', 'reference auth_user'),
	Field('comment_text', type='string'),
	Field('datetime', 'datetime'))


db.define_table('item',
	Field('image', 'string'),
	Field('votes', 'integer', default=0))


## GLOBAL definitions and functions

# Scores, colours and icons
scores = (-3, -1, 1, 3)
# http://colorbrewer2.org/#type=diverging&scheme=RdYlBu&n=4
score_colors = ['#d7191c','#fdae61','#abd9e9','#2c7bb6']
score_icons = ('glyphicon glyphicon-thumbs-down',
			   'glyphicon glyphicon-hand-left',
			   'glyphicon glyphicon-hand-right',
			   'glyphicon glyphicon-thumbs-up')

# define a colour scale mapped on to the scores, to generate
# hex codes along the colour scale. 
# e.g. colors.rgb2hex(score_sm.to_rgba(3))

score_cmap = colors.ListedColormap(score_colors, name='score_cmap')
score_sm = cm.ScalarMappable(colors.Normalize(vmin=-3, vmax=3), score_cmap)

## COMMON FUNCTIONS

def _extract_call_and_add_to_db(source_path, audio_id, start, end, user_id, call_note):
	
	# function to extract a call to a permanent file, separated so
	# it can be called externally by automatic call location code
	
	try:
		
		source = AudioSegment.from_mp3(open(source_path))
		call = source[int(start*1000):int(end*1000)]
		
		call_id = db.calls.insert(audio_id = audio_id,
								  start_time = start,
								  end_time = end,
								  created_by = user_id,
								  created_on = datetime.datetime.now(),
								  call_note = call_note)
		
		outfile = os.path.join(request.folder, "static", "calls", "call_" + str(call_id) + ".mp3")
		call.export(outfile, format="mp3", 
					tags={'artist': 'Rainforest Rhythm', 
						  'comments': 'Extracted from ' + os.path.basename(source_path)})
		
		return call_id
	
	except:
		raise RuntimeError()

def _votebar(score, votes, id, grid=['col-sm-4','col-sm-2']):
	
	"""
	Function to return a quality score style progress bar 
	for a given identification score. This has an ident specific
	id so the it can be updated via javascript. The colour is set using
	rainbowvis.js on the initial page load on the client side, so
	that it can be updated by voting without reloading the page.
	"""
	
	# set the width and color for the bar
	this_style = "width: {};background-color: {}"
	this_style = this_style.format(_score_to_width(score), 
								   colors.rgb2hex(score_sm.to_rgba(score)))
	
	
	vote_count = DIV(B(str(votes) + ' vote' + ('s' * (not (votes == 1))),
					   _id='votecount_' + str(id)), 
					 _class=grid[1])
		
	bar =	CAT(DIV(DIV(_class="progress-bar progress-bar-success",
							_role="progressbar", _style=this_style,
							_id='votebar_' + str(id)),
						_class="progress id-quality " + grid[0]),
					vote_count)
	
	return bar

def _score_to_width(score):
	
	'''
	Converts the [-3, 3] score into a style width for the votebar
	set the width for the bar - this is deliberately scaled
	so that -3 is at 10% and 3 is at 100% so there is a visible 
	mark for very low scores.
	'''
	
	return str(((score + 3) * (90/6.0)) + 10) + '%'


def _vote_options(ident_id):
	
	"""
	Function to return a set of ratings highlighting the current 
	user selection and providing the onclick function used to do
	AJAX updating of the votes on the client
	"""
	
	# make a copy of the score_icons, with ids to allow halo switching
	symb = {scr: SPAN(SPAN(_class=icn), 
					  _onclick='my_vote({},{})'.format(ident_id, scr),
					  _class='vote', 
					  _style='background:' + clr,
					  _id='vote_option_{}_{}'.format(ident_id, scr))
			for scr, icn, clr in zip(scores, score_icons, score_colors)}
	
	
	# find the current selection
	user_selection = db((db.scores.user_id == auth.user_id) &
						(db.scores.identification_id == ident_id) &
						(db.scores.replaced == False)).select()
	
	# and if there is one, add a halo to the selected score
	if len(user_selection) == 1:
		current = user_selection.first().score
		symb[current].element('.vote').attributes['_class'] += ' halo'
	
	# hand back a div of the set of icons, with the onclick functions set
	return DIV([symb[ky] for ky in scores])
