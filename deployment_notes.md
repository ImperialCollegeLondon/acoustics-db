# Deploying the SAFE Acoustics system

The SAFE acoustics system provides a workflow to collect, index and provide a public view on environmental acoustic data. The system is described in [this manuscript](https://www.biorxiv.org/content/10.1101/2020.02.27.968867v1) and these notes provide information on deploying the system components. 

The components are:

1. The recording devices, automatically recording and retrieving acoustic data from the field.
2. A file storage system used to store all recordings.
3. A web application used to maintain a database of recordings, record species information and provide an API for the database.
4. A static website that uses the API to populate the public facing website.

The notes below provide more detail on deploying the system. 

## Acoustic recorders

Building, customising and deploying the acoustic recorders is described in detail here:  

[https://sarabsethi.github.io/autonomous_ecosystem_monitoring/](https://sarabsethi.github.io/autonomous_ecosystem_monitoring/)

There is no particular reason why these devices have to be used - essentially any recording system that saves files to web-accessible remote storage could be used, but would require rewriting of the database web application.

## File storage system

For pragmatic reasons (an institutional subscription!), we are currently using the commercial [Box service](https://www.box.com) as file storage for acoustic data. This has some advantages - it has a mature API that provides methods to easily find new files - but also some disadvantages. Notably, there is access control, so authentication steps are required and access tokens need to be provided for public access.

The interface from the file storage system to the `acoustics-db` web application is currently  hard-coded, making it harder to switch the file storage used. Our long-term roadmap is to move the file storage interface to a class-based system, which would make it easier to provide new storage implementations without having to change the rest of the web application.

## `acoustics-db` web application

The `acoustics-db`  web application is written using the open source [Web2Py Framework](http://www.web2py.com/). The application code is in this git repository, which is also the home of this document:

[https://github.com/ImperialCollegeLondon/acoustics-db](https://github.com/ImperialCollegeLondon/acoustics-db)


This is a _dynamic_ website: requests to the website often need to run code to generate the HTML response and the application also uses code to maintain the underlying database. For this reason, it needs to be deployed to a server. We have deployed the web application to an [Amazon Web Services EC2 virtual server](https://aws.amazon.com/ec2). It does not need a particularly fast server or lots of memory: our instance is running on a `t2.micro` instance running Ubuntu 18.04 LTS Bionic Beaver. Running costs are ~10 GBP per month and the `t2.micro` server instance class is one that AWS provide free for a year for development and evaluation:

[https://aws.amazon.com/free/](https://aws.amazon.com/free/)

There is however no particular need to use AWS - any virtual server providing a Python environment should be fine. Once you have created your server instance and can access it via SSH - this will be documented by your server provider - then deploying the application consists of the following steps:

Note that `web2py` actually supports Python 3. Having said that, the web application is currently written in Python 2.7. We are aware that this is now deprecated and updating to Python 3 is in the roadmap for this code.

### Deploy web2py

The Web2Py framework provides several recipes for deploying the Web2Py code to a server:

[http://web2py.com/books/default/chapter/29/13/deployment-recipes](http://web2py.com/books/default/chapter/29/13/deployment-recipes)

We used an existing script to deploy Web2Py using the `nginx` web server and `uWSGI`: these are the parts of the server setup that link the application code to the outside world, handling incoming web requests and returning the requested resources.  Note that you can use different operating systems and web servers (e.g. Apache) and there are scripts available for other combinations.

The following `bash` commands should get this up and running for you - the script walks through the process. Note that you do require super-user access (`sudo`) for most of this deployment.

```sh
# download the setup script
sudo wget https://raw.githubusercontent.com/web2py/web2py/master/scripts/setup-web2py-nginx-uwsgi-ubuntu.sh
# make it runable
sudo chmod +x setup-web2py-nginx-uwsgi-ubuntu.sh
# run it
sudo ./setup-web2py-nginx-uwsgi-ubuntu.sh
```

As part of this process, you should be asked to provide an admin password. This gives access to the web2py admin pages _and_ to the admin pages of web applications running under Web2Py. Note this down carefully and do not share it!

### Python packages

The web application require a few Python packages that are not in the standard library that should have been installed. The following code will install them:

```sh
sudo pip install boxsdk[jwt]
sudo pip install pillow
sudo pip install pandas
```

The `pillow` and `pandas` packages are used to generate a graph of audio recordings through time by site and `boxsdk[jwt]` is python code used to communicate with Box, with the extra JSON web token authentication.

### Deploy `acoustics-db`

You can now clone the `acoustics-db` application to the web server:

```sh
# Move to the folder holding the Web2Py applications
cd /home/www-data/web2py/applications
# Clone from the git repository
sudo git clone https://github.com/ImperialCollegeLondon/acoustics-db.git
# Change the owner of the application folder to www-data
sudo chown -R www-data:www-data acoustics-db
```

### Application configuration

The file `private/appconfig.json` is used to configure the web application. It sets the database to be used: the version in the repository just uses a local SQLite file, which is flexible and easy for relatively small datasets.

In our current setup, the config file is also used to store the configuration of the Box archive used to store the audio files. This involves identifying which Box folders to scan for audio files and identifying two files needed to authenticate the connection to the Box API (see `modules/box.py` for the implementation of this). If you also use Box, you need to create an app configuration on your Box administration and provide these details here to allow the two systems to talk to each other ([see here](https://developer.box.com/guides/authentication/jwt/)).


### Website access

You should now have a live Web2Py application running the `acoustics-db` application. If you are using AWS (or probably pretty much any virtual server provider), you should now be able to access the website using the Public IP address of your virtual server. 

However, your server provider may need additional steps to make the IP address accessible. In AWS, for example, you will need to adjust the security groups of your server instance to allow inbound traffic on HTTP (port 80) and HTTPS (port 443).

#### Setting up the domain name

You are going to want users to access the site via a domain name, not an IP address, so buy a domain name and then point it to your server IP address. If you are using AWS, then it is a good idea to set up an Elastic IP address. These do have a cost but an Elastic IP address provides a permanent IP address that can be linked to different virtual servers. This way, if your server instance does crash or need changing, you don't have to update your DNS entry, just change which virtual server is linked to the Elastic IP address.

#### Set the default application

A single Web2Py installation can serve multiple web applications. The following step will make the web server go to the `acoustics-db` application by default. Basically this step changes the URL from:

    http://my.webserver.com/acoustics-db/index.html

to

    http://my.webserver.com/index.html


You will need to add a file `routes.py` in the Web2Py root folder. 

```sh
cd /home/www-data/
touch routes.py
```

Now open `routes.py` in your text editor of choice and enter the following text:

```
routers = dict(
    BASE = dict(
        default_application='acoustics_db',
    )
)
```

#### Deploying HTTPS

It is also good practice to use HTTPS for all web traffic and you can use [LetsEncrypt](https://letsencrypt.org/) to do this for free. You will need to have registered a domain name for your website and then it is simple to get a LetsEncrypt certificate for that site.

```sh
# Ensure packages are up to date
sudo apt-get update
# Add the certbot repository, containing installation scripts
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update
# Install certbot and certbot code for nginx 
sudo apt-get install certbot python-certbot-nginx
# Install certbot and restart the web server
sudo certbot --nginx
sudo /etc/init.d/nginx restart
```

#### Creating the application admin user

Many of the functions in the web application are only available when you are logged in to the application. Web2Py has a built-in registration process but we have deliberately turned this off as only a single admin user is ever needed.

You will need to go to the `appadmin` page for your web application. If you haven't set the default application, this would be:

    http://my.webserver.com/acoustics-db/appadmin

If you have set the default application, it will be:

    http://my.webserver.com/appadmin

You should see a list of database tables and at the top is `db.auth_user`. Click on the New Record button and fill in first and last names, email, username and password and click submit. Do not use the Web2Py admin password again!

If you go to your web application page, you should now be able to click on the little lock icon in the top right and enter that username and password to access the admin functionality.

### Database

The web application needs some tables in the database to be populated. You will need to be logged in to do this and should then be able to see the Admin menu, which has links to these tables. Each table page has a new record button at the top to add data.

It is also possible to bulk import data to these tables. You will need to go to the `appadmin` site and then go to the link for a table (e.g. sites is `db.sites`). At the bottom of each of these pages is a button to import data from a CSV file. This is a little trickier as you need to provide the correct headers for a table - basically `tablename.fieldname`.
 
#### Sites and deployments. 

Recorders are initialised before being taken to the field (and a GPS locator is a big battery drain), so the recorders don't know where they are in the field. Incoming audio files are therefore only identified by the recording device ID and the date and time of the recording. To locate recordings in space, you need to populate:

1. The sites table. The key fields are the latitude, longitude and site name, but there are other fields to provide images and descriptions.

2. The deployments table. This ties a particular recorder ID to an existing entry in the site table and give the dates of deployment (and some other simple data).

With these two tables, an incoming audio file can be placed in space. The Box Scans admin menu item shows how incoming recordings have been matched to deployements and the Audio Matching admin menu item identifies recordings that do not match a deployment.

#### Taxa and taxon observations

The public facing website shows taxa that might be heard at a particular site. The data behind this comes from the `taxa` table and the `taxon_observations` table. Both of these can again be inspected and populated from the admin menu. There are some options to link taxa to GBIF id (and hence to GBIF occurrence images) but these are not currently documented in detail.

#### Audio data

The 'Admin functions' option in the admin menu provides the option 'Scan box for new audio', which will add file details in to the audio table and match them up to deployments. It is also possible to set up a scheduled scan but this functionality is still in development.


## Deploying the public acoustics website

The public facing website is a static site designed using ReactJS and other software. The HTML loaded from the site then uses the client browser to connect to the API of the `acoustics-db` web application and retrieve the most recent set of audio data to present. 

Because this is a static website, a server is not needed and you simply need to find somewhere to serve the files. We have used an AWS S3 bucket configured to run as a website:

[https://docs.aws.amazon.com/AmazonS3/latest/dev/WebsiteHosting.html](https://docs.aws.amazon.com/AmazonS3/latest/dev/WebsiteHosting.html)

Obviously, this code is designed around the use case of the SAFE Project, so would need substantial modification of logos, text and other project specific content for a new use case, but the core changes are relatively simple and the deployment process is:

1. Clone the static site repository: [https://github.com/aaronSig/rainforest-rhythms](https://github.com/aaronSig/rainforest-rhythms)
1. Change the  API URL - this is set in the file `src/settings.json`. 
1. Change the map overlay. The file `public/map_data.geojson` defines the region of interest and shows any key features. It is also used to automatically set the map extent in the website.
1. Customisation - there is a markdown file to generate the 'about' page at `src/markdown/about.mdx` and there is a Google Analytics tracker at the top of `master/public/index.html`. Obviously there is some other branding to change too!
1. Follow the instructions on the repository to use `yarn`  to test and then build the site.
1. Deploy the built files to your static web server.
