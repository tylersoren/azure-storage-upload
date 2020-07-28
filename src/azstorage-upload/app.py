# Requires Python 3.8

import os, uuid, requests
from flask import Flask, request, session, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import msal
import app_config

app = Flask(__name__, instance_relative_config=True)
app.config.from_object(app_config)
Session(app)

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Get a token credential for authentication
token_credential = ClientSecretCredential(
    app.config['TENANT_ID'],
    app.config['CLIENT_ID'],
    app.config['CLIENT_SECRET']
)

# Create the BlobServiceClient and connect to the storage container
try:
    blob_service_client = BlobServiceClient(account_url=app.config['STORAGE_URL'], credential=token_credential)
    container_name = app.config['CONTAINER_NAME']
    container_client = blob_service_client.get_container_client(container_name)
except Exception as e:
    print(e)

# Main page handling
@app.route('/', methods=['GET', 'POST'])
# @auth('user')
def index():
  # check if user logged in, if not redirect to login
  if not session.get("user"):
        return redirect(url_for("login"))
  
  # Check if user token contains the proper role
  if 'roles' not in session["user"]:
        return render_template("not_authorized.html", message="User not assigned any roles for this application")
  if not any(x in app.config['ROLES'].keys() for x in session["user"]["roles"]):
        return render_template("not_authorized.html", message="User not assigned the proper role for access")

  # Get folders that user has access to
  folder_access = []
  for role in session["user"]["roles"]:
    folder_access += app.config["ROLES"][role]

  # Get selected folder path or default to first available folder
  current_folder = request.args.get('folder')
  if not current_folder:
      current_folder = folder_access[0]
  else:
    # Validate that user has access to the selected folder
    if current_folder not in folder_access:
      return render_template("not_authorized.html", message="User not assigned access to this folder")
  path = app.config["PATHS"][current_folder]
  
  
  
  try:      
      # List the blobs in the container from the specified folder
      blob_list = container_client.list_blobs(name_starts_with=path, include='metadata')
      blob_table = []
      # Create table entries
      for blob in blob_list:
        relative_path = os.path.relpath(blob.name, path)
        if not blob.metadata:
          uploaded_by = ""
        else:
          uploaded_by = blob.metadata['uploaded_by']
        if not '/' in relative_path:
          blob_table.append(dict(name=blob.name, size=blob.size, uploaded_by=uploaded_by))

  except Exception as e:
      print(e)

  # If request is a Post, handle the file upload
  if request.method == 'POST':
    
    # Check if file was included in the Post, if not return warning
    file = request.files['file']
    filename = secure_filename(file.filename)
    if not filename:
          return render_template("file_error.html", title="File Not Selected for Upload", 
                message="Must select a file to upload first!", blobs=blob_table, 
                user=session["user"], folders=folder_access, current_folder=current_folder)

    try:
        # Create a blob client using the local file name as the name for the blob
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=(path + filename))
        try:
            # Check if blob already exists
            if blob_client.get_blob_properties()['size'] > 0:
                print(filename + " already exists in the selected path. Skipping upload.")
                return render_template("file_error.html", title="File already exists", 
                    message="File already exists!", blobs=blob_table, 
                    user=session["user"], folders=folder_access, current_folder=current_folder)
        except ResourceNotFoundError as e:
            # catch exception that indicates that the blob does not exist and we are good to upload file
            pass

        print("Uploading " + filename + " to Azure Storage on selected path.")
        
        # create metadata including the uploading user's name
        metadata = {'uploaded_by': session["user"]["name"]}
        # Upload the created file
        blob_client.upload_blob(file, metadata=metadata)

        # Update the table display with the new blob
        blob_table.append(dict(name=blob_client.get_blob_properties().name, size=blob_client.get_blob_properties().size, 
            uploaded_by=session["user"]["name"]))
      
    except Exception as e:
      print(e)

    return render_template('file_uploaded.html', title="File Uploaded", blobs=blob_table, 
      user=session["user"], folders=folder_access, current_folder=current_folder)

  return render_template('base.html', title="Upload New File", blobs=blob_table, 
    user=session["user"], folders=folder_access, current_folder=current_folder)

@app.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
    return render_template("login.html", auth_url=auth_url, version=msal.__version__)

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))  # No-OP. Goes back to Index page
    if "error" in request.args:  # Authentication/Authorization failure
        return render_template("auth_error.html", result=request.args)
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app_config.SCOPE,  # Misspelled scope would cause an HTTP 400 error here
            redirect_uri=url_for("authorized", _external=True))
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    return redirect(url_for("index"))

# Following functions are for interacting with Azure AD and handling token in cache
@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_url=_build_auth_url)  # Used in template

# Start the application
if __name__ == '__main__':
  app.run()