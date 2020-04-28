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

There is no particular reason why these devices have to be used - essentially any recording system that saves files to web-accessible remote storage could be used, but would require some rewriting of the database web application.

## File storage system

For pragmatic reasons (an institutional subscription!), we are currently using the commercial [Box service](www.box.com) as file storage for acoustic data. This has some advantages - it has a mature API that provides methods to easily find new files - but also some disadvantages. Notably, there is access control, so authentication steps are required and access tokens need to be provided for public access.

## `acoustics-db` web application

The `acoustics-db`  web application is written using the open source [Web2Py Framework](http://www.web2py.com/).  The application code is in this git repository, which is also the home of this document:

[https://github.com/ImperialCollegeLondon/acoustics-db](https://github.com/ImperialCollegeLondon/acoustics-db)

We have deployed the web application to an [Amazon Web Services EC2 virtual server](https://aws.amazon.com/ec2). It does not need a particularly fast server or lots of memory: our instance is running on a `t2.micro` instance running Ubuntu 18.04 LTS Bionic Beaver. Running costs are ~10 GBP per month and the `t2.micro` server instance class is one that AWS provide free for a year for development and evaluation:

[https://aws.amazon.com/free/](https://aws.amazon.com/free/)

There is however no particular need to use AWS - any virtual server providing a Python environment should be fine. Once you have created your server instance and can access it via SSH - this will be documented by your server provider - then deploying the application consists of the following steps:

### Deploy web2py

The Web2Py framework provides several recipes for deploying the Web2Py code to a server:

[http://web2py.com/books/default/chapter/29/13/deployment-recipes](http://web2py.com/books/default/chapter/29/13/deployment-recipes)

We used an existing script to deploy Web2Py using the `nginx` web server and `uWSGI`: these are the parts of the server setup that link the application code to the outside world, handling incoming web requests and returning the requested resources. 

The following `bash` commands should get this up and running for you - the script walks through the process. Note that you do require super-user access (`sudo`) for most of this deployment.

```sh
# download the setup script
sudo wget https://raw.githubusercontent.com/web2py/web2py/master/scripts/setup-web2py-nginx-uwsgi-ubuntu.sh
# make it runable
sudo chmod +x setup-web2py-nginx-uwsgi-ubuntu.sh
# run it
sudo ./setup-web2py-nginx-uwsgi-ubuntu.sh
```

# DB

cd /home/www-data/web2py/applications
sudo git clone https://github.com/ImperialCollegeLondon/acoustics-db.git
cd ../
sudo chown -R www-data:www-data acoustics-db

# copy in the database folder and private files

sudo pip install boxsdk[jwt]
sudo pip install pillow
sudo pip install pandas

# letsencrypt
sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update


sudo apt-get install certbot python-certbot-nginx
sudo certbot --nginx


# copy in the database folder, the config files and download contents

sudo /etc/init.d/nginx restart


# set scheduler worker running

    Create the file `/etc/systemd/system/web2py-scheduler.service` with the contents

	    [Unit]
	    Description=Web2Py scheduler service
    
	    [Service]
	    ExecStart=/usr/bin/python /home/www-data/web2py/web2py.py -K <yourapp>
	    Type=simple
	    Restart=always
	    RestartSec=3
    
	    [Install]
	    WantedBy=multi-user.target

    Then install the service and restart/stop/ etc via:

        sudo systemctl enable /etc/systemd/system/web2py-scheduler.service 
		sudo systemctl restart web2py-scheduler.service 