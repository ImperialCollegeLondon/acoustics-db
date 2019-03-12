# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

# response.logo = A(B('Rainforest Rhythm'),
#                   _class="navbar-brand")
response.logo = A(IMG(_src=URL('static','images/logo-rainforest-rhythms-dark.png'), 
                      _style='padding:4px 0px'))
response.title = request.application.replace('_',' ').title()
response.subtitle = ''

## read more at http://dev.w3.org/html5/markup/meta.name.html
response.meta.author = 'Your Name <you@example.com>'
response.meta.description = 'a cool new app'
response.meta.keywords = 'web2py, python, framework'
response.meta.generator = 'Web2py Web Framework'

## your http://google.com/analytics id
response.google_analytics_id = None

#########################################################################
## this is the main application menu add/remove items as required
#########################################################################

response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
    (T('About'), False, URL('default', 'about'), []),
    (T('Audio'), False, URL('default', 'audio'), []),
    ]

if auth.is_logged_in():

    # Get data to populate the scan info
    qry = current.db(current.db.box_scans)
    last_scan = qry.select(orderby= ~ current.db.box_scans.scan_datetime,
                           limitby=(0,1)).first()
    if last_scan is None:
        last_scan = 'None'
    else:
        last_scan = last_scan.scan_datetime.isoformat()
    
    admin_menu  = (T('Admin'), False, '', [
                      (T('Deployments'), False, URL('default', 'deployments'), []),
                      (T('Sites'), False, URL('default', 'sites'), []),
                      (T('Taxa'), False, URL('default', 'taxa'), []),
                      (T('Audio'), False, URL('default', 'audio_admin'), []),
                      (T('Audio matches'), False, URL('default', 'audio_matching'), []),
                      (T('Box Scans'), False, URL('default', 'box_scans'), []),
                      (T('Admin functions'), False, URL('default', 'admin_functions'), []),
                      (HR(), False, '', []),
                      (T('Last scan: ' + last_scan), False, '', [])
                  ])
    
    response.menu.append(admin_menu)


    login_icon = LI(A(SPAN(_class='glyphicon glyphicon-lock', _style='color:darkred'),
                _href=URL('user', args='logout')))

else:
    
    login_icon = LI(A(SPAN(_class='glyphicon glyphicon-lock'),
                _href=URL('user', args='login')))



if "auth" in locals(): auth.wikimenu()
