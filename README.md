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
* info : Generic Info if available - iterable
* status : Employee Status if available - iterable
* contract : Contract linked to the user - iterable
* project : Projects linked to the user - iterable
* leave : Leaves linked to the user - iterable 





________________________________
#### credits

inspired by [Inventree](https://github.com/inventree/InvenTree)

using [fullcalendar](https://fullcalendar.io/)

##### Menu images from 

- https://www.freevector.com
- https://fr.vecteezy.com

