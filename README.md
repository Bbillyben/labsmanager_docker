# labsmanager
<p align="center">
  <img width="100" src="/data/static/img/labsmanager/labsmanager_icon_fav.png">
  </br>
  ***a django app to manage public science labs for lab manager.***
</p>


________________________________________


### features

* employee
* team
* contract
* projects
* fund
* budget
* expense
* leave
* dashboard



## Reports

Models to upload and store Word template. It uses (docxtpl)[https://docxtpl.readthedocs.io/en/latest/] to generate word documents.
Each model is specific of it's reported models (aka employee, projects, ...)

#### General tags

* date : AAAA-MM-DD
* datetime :
* report_description : 
* report_name
* report_revision
* request
* user : username of the user that has requests the report


#### Employee tags

* employee : instance of Employee
* info :  Generic Info if available - iterable / instances list
* status :  Employee Status if available - iterable / instances list
* contract : Contract linked to the user - iterable / instances list
* project :  Projects linked to the user - iterable / instances list
* leave : Leaves linked to the user - iterable / instances list 
* teams :  Teams where the user is leader or participant - iterable / instances list

#### Projects tags

* project : instance of current project
* institution : Institution involved in project if available - iterable / instances list
* participant : Participant involved in project if available - iterable / instances list
* contract : Contracts in project if available - iterable / instances list
* budget : Budgets declared in project if available - iterable / instances list
* milestones : Milestones of the project if available - iterable / instances list
* Fund : Fund of the project if available - iterable / dictionnary (see reports.serializers)
    * pk
    * funder (pk, short_name, name)
    * institution (pk, short_name, name)
    * ref
    * start_date
    * end_date
    * amount
    * expense
    * available
    * list of fund items :
        * pk
        * type (pk, short_name, name)
        * amount
        * expense
        * available
        * value_date
        * entry_date
________________________________
#### credits

inspired by [Inventree](https://github.com/inventree/InvenTree)
(some code come directly from them)

using [fullcalendar](https://fullcalendar.io/)

##### Menu images from 

- https://www.freevector.com
- https://fr.vecteezy.com

