# Requires Python 3.8
from flask import Flask, request, session, redirect, url_for, render_template
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import logging
import msal
import uuid
# Import local files
from azstorage import UserStorageSession, AzureStorage
import app_config

# Configure Default Logger - used by some imported modules like msal
root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)

# Configure App Logger
logger = logging.getLogger('azure_storage_app')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

app = Flask(__name__, instance_relative_config=True)
app.config.from_object(app_config)
Session(app)

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Create the Azure Storage connection object based on the app_config.py
azure_storage = AzureStorage(app.config)


# Main page handling
@app.route('/', methods=['GET', 'POST'])
# @auth('user')
def index():
    # check if user logged in, if not redirect to login
    if not session.get("user"):
        return redirect(url_for("login"))

    auth = azure_storage.validate_user(session, request)
    response = auth['response']
    # If authorization was successful
    if response.status_code==200:
    
        # Create user session object
        user_session = UserStorageSession(auth['path'], auth['user'])

        # Get blobs and folders for selected path and user
        response = azure_storage.walk_blobs(user_session)

        # If request is a Post, handle the file upload
        if request.method == 'POST':
            file = request.files['file']
            subfolder = request.form['subfolder']
            response = azure_storage.upload_blob(file, subfolder, user_session)

        # Check for delete flag and handle blob deletion
        delete = request.args.get('delete')
        if delete:
            response = azure_storage.delete_blob(user_session, request.args.get('blob'))

    # If response is empty or error_flags are set return the appropriate error,
    # else return the valid response
    if response is None:
        return render_template("error.html", message="Unknown Error"), 404
    
    elif response.error_flag == 1:
        return render_template("error.html", message=response.message), response.status_code
    elif response.error_flag == 2:
        return response.message, response.status_code
    else:
        return render_template('base.html',
                            message=response.message,
                            blobs=user_session.blob_table,
                            user=auth['user'],
                            folders=auth['folder_access'],
                            current_folder=auth['current_folder'],
                            subfolders=user_session.folder_list), response.status_code


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
