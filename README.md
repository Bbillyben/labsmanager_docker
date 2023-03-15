# labsmanager_docker
Labs Manager Django App to help getting track of public lab projects



# installation : 
Use docker compose (test in v2.12)

### .env file : 
LAB_EXT_VOLUME : define where to store static files for django, should be mounted in volume for both labsmanager service and nginx service.
SECRET_KEY : the django secrete key
DJANGO_ALLOWED_HOSTS : list of allowed host

# db parameters
SQL_ENGINE=django.db.backends.postgresql
LAB_DB_NAME=django_db
LAB_DB_USER=djangoUser
LAB_DB_PASSWORD=djangoUserPass
LAB_DB_HOST=localhost
LAB_DB_PORT=5432

LAB_WEB_PORT=80

# define image tag
LAB_TAG=latest

CSRF_TRUSTED_ORIGINS=https://labsmanager.legendre-ratajczak.fr

SECRET_KEY='hujihyyuadjkcù^$qpspîonjbhuiagghéh12314d156'
DEBUG='true'
LABS_LOG_LEVEL='DEBUG'

# Email Settings
LAB_EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
LAB_EMAIL_HOST='' # eg smtp server
LAB_EMAIL_PORT=''
LAB_EMAIL_USERNAME=''
LAB_EMAIL_SENDER=''
LAB_EMAIL_PASSWORD=''
LAB_EMAIL_PREFIX=''
LAB_EMAIL_TLS=false
LAB_EMAIL_SSL=true

LAB_SITE_ID=1



DJANGO_ADMINS='username1,user1email@somewher.com  username2,user2email@somewhereelse.com' # list of admin couple of username and adresse email coma separated and split by space 

## Admin Site Customisation
ADMIN_HEADER='LabsManager'
ADMIN_SITE_TITLE='LabsManager'
ADMIN_INDEX_TITLE='Menu'

LABSMANAGER_STATIC_ROOT='/home/labsmanager/data/static/' # set static path
LABSMANAGER_MEDIA_ROOT='/home/labsmanager/data/media/'  # set media path 



### command to run once containers are setted :

```
docker compose run lab-server invoke update
```

