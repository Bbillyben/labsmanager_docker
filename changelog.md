## Changelog LabsManager

### 2024-07-26
note : this version need an update with static. 


* [enhance] Change password form to hide hints 
* [Fix] Contract's Icon in Organisation info panel 
* [Fix] Double password reset link on login page
* [Fix] CSS issue on provisionnal contract tab
* [ADD] permission system at object level (django-rules), lots of modification and additions
    * in employee, project and team view, user can change item only if user'emlployee is himself or superior, project leader or team leader
* [ADD] Parameters to let user :
    * modify his/her subordinates info
    * modify project where they are co leader
* [ADD] In finder, fund and budget are restricted for user that don't have right on items to only project where user's employee is leader or co leader 
* [ADD] Group permission Fixture, installed at "install" task
    * can be loaded by : python manage.py loaddata group-fixture
    * or docker compose run lab-server invoke loadfixture group-fixture

### 2024/07/11
* [Fix] remove favorite button for user's employee
* [enhanced] switch to nh3 sanitization of user input field
* [enhanced] for calendar bimensual view switch from weeks label to numeric day
* [enhanced] Add mixin for BSmodalDeleteView to help with GenericForeignKey model (note : to be broadly implemented through view modals)

* [UPDATE] update to Django 4.2
* [UPDATE] update to python 3.11.9

* [ADD] Contract status : effective or provisionnal to be able to plan futur contract on fund line
* [ADD] note system to add whatever note is needed, with "textbook" style with tab and html clean. Added to employee, project, team, organisations



