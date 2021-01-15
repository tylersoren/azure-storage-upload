# Introduction 
This app runs a simple Python Flask web server for uploading files to an Azure Storage container and listing the contents of that container.  It is configured to authenticate users against Azure AD and checks that they have been granted the proper roles.  Based on role, the user is granted access to certain folders in the container.

If not authenticated the user will see the following logon prompt when opening the site

![alt_text][login]

Once logged in they will be able to select the folders that they have access to from the drop-down, any existing files in that folder, and a drag and drop area that they can drop files into or click to enter a selection dialog. They can also enter an optional subfolder path to drop the file in.

![alt_text][main_page]

# Roles

The User roles and associated paths they have access to in the storage account are configured in app_config.py.

These roles are mapped to the Azure AD Groups under the "Enterprise Applications" view in Azure AD.

Mappings to the other roles in dev can be made manually if needed for testing. AD groups are mapped to Azure AD application roles in the Azure Portal under Azure AD --> Enterprise Applications.  Select the "Azure Storage Upload" app for the appropriate environment and then add assignments under "Users and Groups"

![alt_text][permissions]

# Getting Started
This app was built with Python3.  Install Python3 and PIP prior to working with this repo.  The Python package dependencies can be installed with:

`python -m pip install -r requirements.txt`

Alternately use pipenv to create a virtual environment.  This project contains a Pipfile for creating new pipenv environments.  Create the environment with:

`pipenv install`

If changes are made to the pipenv, export any changed dependencies to the requirements.txt wiht:

`pipenv lock --requirements > requirements.txt`

The application requires an application registration to be create in Azure AD.  The callback URL should be set to <appUrl>/getAToken to match the REDIRECT_PATH configured in appconfig.py.  The app checks that the authenticated user has been assigned the role "user".  Follow this [guide to configure app roles](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-add-app-roles-in-azure-ad-apps) .

The app expects environment variables to be set for config purposes
* AZURE_STORAGE_ACCOUNT_URL - The URL of the Storage account to upload to
* AZURE_STORAGE_CONTAINER_NAME - set this to the name of the storage container that you want your app to upload to
* AZURE_TENANT_ID - The Azure AD Tenant ID
* AZURE_CLIENT_ID - set this to the the Application ID for your application registration
* AZURE_CLIENT_SECRET - set this to the the secret key for your application registration

There are additional configurations to be made in the app_config.py file including the roles and related container paths.

# Local Build and Test
The app can be run locally by running the following command and will run a local web server on port 5000

`python app.py`

To run the app in the pipenv environment:

`pipenv run python app.py` or use `pipenv shell` to start an interactive session.

There is also a Dockerfile that will package all dependencies in a container which can be built with:

`docker build -t azstorage-upload:latest .`

# Kubernetes Deployment

There is a Helm chart for deploying to a kubernetes environment.

To install the Helm chart run the following command and supply the Azure client secret.  The container name can also be supplied at install time or updated via values.yaml file.

`helm upgrade test deploy/azstorage-upload --set azure.clientSecret="<ClientSecret>" --install`

The requirements file includes a the Green Unicorn (gunicorn) WSGI server for serving the Flask app.  This is preferred in production over the built in Flask dev server.  The Dockerfile includes the launch command for the application using gunicorn.

# Reference

This app relies heavily on the Azure Python SDK for storage and Microsoft Authentication Library (MSAL). Pages are generated and served using the Python Flask web framework and the Gunicorn WSGI HTTP server. The Drag and Drop functionality is provided by the open-source Dropzone project and is handled client-side (files are included in the static assets). The following links are provided for reference.

* [Azure Python SDK](https://azure.github.io/azure-sdk-for-python/)
* [Azure Python Storage Blobs library](https://azuresdkdocs.blob.core.windows.net/$web/python/azure-storage-blob/12.3.1/index.html)
* [Azure Storage API refernce](https://docs.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob?view=azure-python)
* [MSAL](https://github.com/AzureAD/microsoft-authentication-library-for-python)
* [MSAL Flask Sample](https://github.com/Azure-Samples/ms-identity-python-webapp)
* [Flask](https://flask.palletsprojects.com/en/1.1.x/)
* [Gunicorn](https://docs.gunicorn.org/en/stable/)
* [Dropzone](https://www.dropzonejs.com/#) 


[login]: ./docs/images/login.png "User Login"
[main_page]: ./docs/images/main_page.png "Main page view"
[permissions]: ./docs/images/permissions.png "Assigning user permissions in Azure AD"