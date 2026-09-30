# labsmanager\_docker
Labs Manager Django App to help getting track of public lab projects



# installation :
Use docker compose (test in v2.12)

### .env file :

LAB\_EXT\_VOLUME : define where to store static files for django, should be mounted in volume for both labsmanager service and nginx service.
SECRET\_KEY : the django secrete key
DJANGO\_ALLOWED\_HOSTS : list of allowed host

# db parameters

SQL\_ENGINE=django.db.backends.postgresql
LAB\_DB\_NAME=django\_db
LAB\_DB\_USER=djangoUser
LAB\_DB\_PASSWORD=djangoUserPass
LAB\_DB\_HOST=localhost
LAB\_DB\_PORT=5432

LAB\_WEB\_PORT=80

# define image tag


LAB\_TAG=latest

CSRF\_TRUSTED\_ORIGINS=<https://labsmanager.legendre-ratajczak.fr>

SECRET\_KEY='hujihyyuadjkcù^$qpspîonjbhuiagghéh12314d156'
DEBUG='true'
LABS\_LOG\_LEVEL='DEBUG'

# Email Settings




LAB\_EMAIL\_BACKEND='django.core.mail.backends.smtp.EmailBackend'
LAB\_EMAIL\_HOST='' # eg smtp server
LAB\_EMAIL\_PORT=''
LAB\_EMAIL\_USERNAME=''
LAB\_EMAIL\_SENDER=''
LAB\_EMAIL\_PASSWORD=''
LAB\_EMAIL\_PREFIX=''
LAB\_EMAIL\_TLS=false
LAB\_EMAIL\_SSL=true

LAB\_SITE\_ID=1

DJANGO\_ADMINS='username1,<user1email@somewher.com>  username2,<user2email@somewhereelse.com>' # list of admin couple of username and adresse email coma separated and split by space

## Admin Site Customisation

ADMIN\_HEADER='LabsManager'
ADMIN\_SITE\_TITLE='LabsManager'
ADMIN\_INDEX\_TITLE='Menu'

LABSMANAGER\_STATIC\_ROOT='/home/labsmanager/data/static/' # set static path
LABSMANAGER\_MEDIA\_ROOT='/home/labsmanager/data/media/'  # set media path



### command to run once containers are setted :

<br />

```
docker compose run lab-server invoke update
```

### License

LabsManager is licensed under the GNU Affero General Public License v3.0.




