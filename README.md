# labsmanager_docker
Labs Manager Django App to help getting track of public lab projects



# installation : 
Use docker compose (test in v2.12)

### .env file : 
LAB_EXT_VOLUME : define where to store static files for django, should be mounted in volume for both labsmanager service and nginx service.



### command to run once containers are setted :

docker compose run lab-server python3 labsmanager/manage.py migrate               # create database scheme

docker compose run lab-server python3 labsmanager/manage.py createsuperuser       # create the super user to access django at first


docker compose run lab-server python3 labsmanager/manage.py collectstatic         # to collect static file from django to share in static


