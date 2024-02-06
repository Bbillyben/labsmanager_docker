from django.utils.translation import gettext_lazy as _

from import_export.forms import ImportForm as ImportFormIE

from django import forms
from django.conf import settings

class ImportForm(ImportFormIE):

    def __init__(self, import_formats, *args, **kwargs):
        print(">>>>> ImportForm INIT")
        # print(f' - import_formats:{import_formats}')
        # print(f' - args:{args}')
        # print(f' - kwargs:{kwargs}')
        
        
        super().__init__(import_formats, *args, **kwargs)
        # self.data["input_format"]=args[0]["input_format"]
        # self.data["import_file"]=args[1]["import_file"]
        # print(f' args has import : {args["import_file"]}')
        # print(f' args has input_format : {hasattr(args,"input_format")}')
        # if hasattr(args,'import_file'):
        #     self.initial['import_file'] = args['import_file']
        # if hasattr(args,'input_format'):
        #     self.initial['input_format'] = args['input_format']
        
        
        for p in self.fields:
           print(f' - {p}')
        
    def is_valid(self, *args, **kwargs):
        print("---------------------- ImportForm is valid --------------------------")

        for p in self.fields:
           print(f' - fieldName : {p}')
           print(f' filed : {self.fields[p].__dict__}')
           
        if hasattr(self,'data'):
            print(f' self data :{self.data}')
        else:
            print("No cleaned data")
        isv = super().is_valid()
        print(f"=================================> is valid in Form:{isv}")
        return isv