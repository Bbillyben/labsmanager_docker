
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
    manage(c, "mediabackup --noinput --clean --compress")
    
@task
def restore(c):
    print("Restoring database...")
    manage(c, "dbrestore --noinput --uncompress")
    print("Restoring media files...")
    manage(c, "mediarestore --noinput --uncompress")


@task
def migrate(c):
    print("Running database migrations...")
    print("-------------------------------------")

    manage(c, "makemigrations")
    manage(c, "migrate --noinput")
    manage(c, "migrate --run-syncdb")
    manage(c, "check")

    print("-------------------------------------")
    print("database migrations completed")
    
@task
def update(c):
    migrate(c)
    static(c)
    
    
    
# Data tasks
@task(help={
    'filename': "Output filename (default = 'data.json')",
    'overwrite': "Overwrite existing files without asking first (default = off/False)",
    'include_permissions': "Include user and group permissions in the output file (filename) (default = off/False)",
    'delete_temp': "Delete temporary files (containing permissions) at end of run. Note that this will delete temporary files from previous runs as well. (default = off/False)"
})
def export_records(c, filename='data.json', overwrite=False, include_permissions=False, delete_temp=False):
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

    cmd = f"dumpdata --indent 2 --output '{tmpfile}' {content_excludes()}"

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
    

@task()
def worker(c):
    """Run the InvenTree background worker process."""
    manage(c, 'qcluster', pty=True)
