## Changelog LabsManager



### v0.9.0 / 2024-09
note : require full update (migration and static)

* [FIX] : Issue with delete form for superior/subordinate delete view
* [ADD] : color type setting with RGBvalidator
* [ADD] : **Major Addition** : add plugin system. (Implement from Inventree.plugin)
    * add SettingMixin for a plugin to add setting for admin
    * add ScheduleMixin for a plugin to add task to schedule
    * add CalendarEventMixin for a plugin to provide event to be display in calendar view
* [UPDATE] : item creation (project/employee) automatic leader attribution fix if user has right to change items afterwards (global right)
### 2024-09-05
note : require static update
* [UPDATE] : Information on user/employee setting page for admin
* [ADD] : address type for info (contact and organisation)
* [ADD] : User parameter to set default map provider to build location link for adress type info
* [ADD] : Copy buytton for information in employee, project, contact, organisation's infos.
* [FIX] : bug for admin button in organisation panel
* [FIX] : prevent index card from overlapping and addigin minimum size
* [ADD] : Notification popup for email actions in setting panel.
* [UPDATE] : translation

### 2024-08-24
note : this version need an update for group fixture. 

* [ADD] for Cost Type model, add is_hr paramter to specify wether a cost type is related to human resource, to switch on that to constrain Budget Form.
* [ADD] Project Setting, to add project settings
   * base calculation for project's fund, either 'Simple' (as before,only timepoint), 'Expense' : base on single expense sum for timepoint expense, or hybrid : can refer expenses, but no expense timepoint calculation, except by forcing syncing
   * Co leader can change project : True/False : define wether a co leader of a project as the same right for project modification
* [ADD] Single expense import / export, constrain to project's setting
* [UPDATE] timepoint import : constrain to project's setting (mirroring expense import)
* [UPDATE] User rules and permission
* [UPDATE] Tasks.py to fit order with new models
* [ADD] Version number and update login screen with footer
* [UPDATE] Default expense status to Realised

### 2024-07-27

* [FIX] import issue with expense on error no fund id
* [enhance] import form layout 


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



