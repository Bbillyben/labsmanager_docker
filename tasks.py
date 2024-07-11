
import json
import os
import sys
from pathlib import Path

from invoke import task

def localDir() -> Path:
    """Returns the directory of *THIS* file.
    Used to ensure that the various scripts always run
    in the correct directory.
    """
    return Path(__file__).parent.resolve()


def managePyDir():
    """Returns the directory of the manage.py file."""
    return localDir().joinpath('labsmanager')

def managePyPath():
    """Return the path of the manage.py file."""
    return managePyDir().joinpath('manage.py')

def manage(c, cmd, pty: bool = False):
    """Runs a given command against django's "manage.py" script.
    Args:
        c: Command line context.
        cmd: Django command to run.
        pty (bool, optional): Run an interactive session. Defaults to False.
    """
    c.run('cd "{path}" && python3 manage.py {cmd}'.format(
        path=managePyDir(),
        cmd=cmd
    ), pty=pty)
    

@task
def superuser(c):
    """Create a superuser/admin account for the database."""
    manage(c, 'createsuperuser', pty=True)
    
    
    
@task
def static(c):
    """Copies required static files to the STATIC_ROOT directory, as per Django requirements."""
    manage(c, "collectstatic --no-input")

@task
def static_js_reverse(c):
    """collect static files for django js reverse app, to be updated when url changes."""
    manage(c, "collectstatic_js_reverse")
    
@task
def backup(c):
    print("Backing up database...")
    manage(c, "dbbackup --noinput --clean --compress")
    print("Backing up media files...")
    manage(c, "  --noinput --clean --compress")
    
@task
def restore(c):
    print("Restoring database...")
    manage(c, "dbrestore --noinput --uncompress")
    print("Restoring media files...")
    manage(c, "mediarestore --noinput --uncompress")


@task
def migrate(c, sync_db=False):
    print("Running database migrations...")
    print("-------------------------------------")

    manage(c, "makemigrations")
    manage(c, "migrate --noinput")
    if sync_db:
        manage(c, "migrate --run-syncdb")
    manage(c, "check")

    print("-------------------------------------")
    print("database migrations completed")
    
@task
def update(c):
    migrate(c)
    static(c)

@task(help={
    'super_user': "launch superuser creation dialog at the end of the install",
    })
def install(c, super_user = False):
    """
    Set up tables, and load initial datas :
      - default report files
    
    can launch the superuser creation dialog
    """
    update(c)
    print(" load initial report datas...")
    print("-------------------------------------")
    manage(c, "loaddata initial-report-data")
    print("-------------------------------------")
    
    if super_user:
        superuser(c)
    else:
        print("> run invoke superuser to create admin user for your Labsmanager Instance")
    print(">----------- Install Process Complete -----------<")
    
   
@task
def etpmigrate(c):
    """Migrate older Expense Point ."""
    manage(c, "etp_migrate --delete")

@task
def updatefund(c):
    """Update Exepnse calculation ."""
    manage(c, "update_fund --force")   

@task
def removeduplicate(c):
    """Remove Duplicate from AmountHistory ."""
    manage(c, "remove_duplicate")   

@task
def fimigrate(c):
    """Add fund item to base AmountHistory ."""
    manage(c, "fi_history")   
    
# Data tasks
def content_excludes(
    allow_auth: bool = True,
):
    """Returns a list of content types to exclude from import/export.

    Arguments:
        allow_auth (bool): Allow auth to be exported/importe
    """
    excludes = [
        'contenttypes',
        'auth.permission',
        'django_q.schedule',
        'django_q.task',
        'django_q.ormq',
        'common.rightssupport',
    ]

    # Optionally exclude user auth data
    if not allow_auth:
        excludes.append('auth.group')
        excludes.append('auth.user')

    output = ''

    for e in excludes:
        output += f'--exclude {e} '

    return output

def contentorder():
    app_list = [
        "admin.LogEntry",
        "auth.Permission",
        "auth.Group",
        "auth.User",
        "contenttypes.ContentType",
        "sites.Site",
        "account.EmailAddress",
        "account.EmailConfirmation",
        "staff.Employee",
        "staff.Employee_Type",
        "staff.GenericInfoType",
        "project.Institution",
        "project.Project",
        "project.GenericInfoTypeProject",
        "fund.Cost_Type",
        "fund.Fund_Institution",
        "expense.Contract_type",
        "leave.Leave_Type",
        "reports.EmployeeWordReport",
        "reports.EmployeePDFReport",
        "reports.ProjectWordReport",
        "reports.ProjectPDFReport",
        # "common.RightsSupport",
        "settings.LabsManagerSetting",  
        "infos.OrganizationInfosType",
        "infos.ContactType",
        "infos.ContactInfoType",
        "infos.GenericNote", # generic foreing key
         
        "staff.Employee_Status",# require Employee_type, Employee
        "staff.Employee_Superior",# require Employee

        "staff.Team",# require Employee
        "staff.TeamMate",# require Employee, Team

        "staff.GenericInfo",# require Employee, GenericInfoType

        "project.Institution_Participant",# require Project, Institution
        "project.Participant",# require Project, staff.Employee

        "project.GenericInfoProject",# require Project
        "fund.Fund", # require Project, Fund_Institution
        "fund.Fund_Item", # require Fund
        
        "fund.Budget",# require Fund, staff.Employee_type, expense.Contract_type, staff.Employee
        "fund.Contribution",# require Fund, staff.Employee_type, expense.Contract_type, staff.Employee
        "fund.AmountHistory",# require Fund, Fund_item, ??
        "expense.Expense",# require fund.Cost_Type, fund.Fund
        "expense.Contract",# require staff.Employee, fund.Fund, Contract_type
        "expense.Contract_expense",# require Contract
        "expense.Expense_point",# require fund.Cost_Type, fund.Fund

        "endpoints.Milestones",# require project.Project

        "leave.Leave",# require staff.Employee, Leave_Type

        "common.favorite",# require User, ContentType
        "common.subscription",# require User ContentType

        "settings.LMUserSetting",# require User

        "infos.OrganizationInfos",# require ContentType, institution fund_institution

        "infos.Contact",# require ContentType, institution fund_institution
        "infos.ContactInfo",# require Contact       
    ]
    cmd_list = " ".join(app_list)
    return cmd_list
    
    # return app_list
    
    
@task(help={
    'filename': "Output filename (default = 'data.json')",
    'overwrite': "Overwrite existing files without asking first (default = off/False)",
    'include_permissions': "Include user and group permissions in the output file (filename) (default = off/False)",
    'delete_temp': "Delete temporary files (containing permissions) at end of run. Note that this will delete temporary files from previous runs as well. (default = off/False)",
    'use_order': "force a specific order for app export (in case of issue in import)"
})
def export_records(c, filename='data.json', overwrite=False, include_permissions=False, delete_temp=False, use_order=False):
    """Export all database records to a file.
    Write data to the file defined by filename.
    If --overwrite is not set, the user will be prompted about overwriting an existing files.
    If --include-permissions is not set, the file defined by filename will have permissions specified for a user or group removed.
    If --delete-temp is not set, the temporary file (which includes permissions) will not be deleted. This file is named filename.tmp
    For historical reasons, calling this function without any arguments will thus result in two files:
    - data.json: does not include permissions
    - data.json.tmp: includes permissions
    If you want the script to overwrite any existing files without asking, add argument -o / --overwrite.
    If you only want one file, add argument - d / --delete-temp.
    If you want only one file, with permissions, then additionally add argument -i / --include-permissions
    """
    # Get an absolute path to the file
    if not os.path.isabs(filename):
        filename = localDir().joinpath(filename).resolve()

    print(f"Exporting database records to file '{filename}'")

    if Path(filename).is_file() and overwrite is False:
        response = input("Warning: file already exists. Do you want to overwrite? [y/N]: ")
        response = str(response).strip().lower()

        if response not in ['y', 'yes']:
            print("Cancelled export operation")
            sys.exit(1)

    tmpfile = f"{filename}.tmp"


    cmd = f"dumpdata {contentorder() if use_order else ''} --indent 2 --output '{tmpfile}' {content_excludes()}"
    print(f'>> cmd : {cmd}')
    # Dump data to temporary file
    manage(c, cmd, pty=True)

    print("Running data post-processing step...")

    # Post-process the file, to remove any "permissions" specified for a user or group
    with open(tmpfile, "r") as f_in:
        data = json.loads(f_in.read())

    if include_permissions is False:
        for entry in data:
            if "model" in entry:

                # Clear out any permissions specified for a group
                if entry["model"] == "auth.group":
                    entry["fields"]["permissions"] = []

                # Clear out any permissions specified for a user
                if entry["model"] == "auth.user":
                    entry["fields"]["user_permissions"] = []

    # Write the processed data to file
    with open(filename, "w") as f_out:
        f_out.write(json.dumps(data, indent=2))

    print("Data export completed")

    if delete_temp is True:
        print("Removing temporary file")
        os.remove(tmpfile)

    
@task(help={'filename': 'Input filename', 'clear': 'Clear existing data before import'})
def import_records(c, filename='data.json', clear=False):
    """Import database records from a file."""
    # Get an absolute path to the supplied filename
    if not os.path.isabs(filename):
        filename = localDir().joinpath(filename)

    if not os.path.exists(filename):
        print(f"Error: File '{filename}' does not exist")
        sys.exit(1)

    if clear:
        delete_data(c, force=True)

    print(f"Importing database records from '{filename}'")

    # Pre-process the data, to remove any "permissions" specified for a user or group
    tmpfile = f"{filename}.tmp.json"

    with open(filename, "r") as f_in:
        data = json.loads(f_in.read())

    for entry in data:
        if "model" in entry:

            # Clear out any permissions specified for a group
            if entry["model"] == "auth.group":
                entry["fields"]["permissions"] = []

            # Clear out any permissions specified for a user
            if entry["model"] == "auth.user":
                entry["fields"]["user_permissions"] = []

    # Write the processed data to the tmp file
    with open(tmpfile, "w") as f_out:
        f_out.write(json.dumps(data, indent=2))

    cmd = f"loaddata '{tmpfile}' -i {content_excludes()}"

    manage(c, cmd, pty=True)

    print("Data import completed")
    
@task
def delete_data(c, force=False):
    """Delete all database records!

    Warning: This will REALLY delete all records in the database!!
    """
    print('Deleting all data from LabsManager database...')

    if force:
        manage(c, 'flush --noinput')
    else:
        manage(c, 'flush')

@task
def reset_db(c):
    print('RESETING THE ENTIRE DB ...')
    manage(c, 'reset_db') 

@task()
def worker(c):
    """Run the LabsManager background worker process."""
    manage(c, 'qcluster', pty=True)
