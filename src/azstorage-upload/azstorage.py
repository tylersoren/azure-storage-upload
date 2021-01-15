from azure.storage.blob import BlobServiceClient
from azure.storage.blob._models import BlobPrefix
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError
from werkzeug.utils import secure_filename
import time
import logging

logger = logging.getLogger('azure_storage_app')

class Response:

    # Default response object is success with blank message
    # error flag 0 = use base.html
    # error flag 1 = use error.html
    # error flag 2 = return message only
    def __init__(self, message="", status_code=200, error_flag=0):
        self.message=message
        self.status_code=status_code
        self.error_flag=error_flag


class UserStorageSession:

    def __init__(self, path, user):
        self.path = path
        self.user = user
        self.blob_table = []
        self.folder_list = []


# Class for storing a connection to an Azure storage account and container
# Provides methods for listing blobs and folders, uploading and deleting blobs
# All methods return a Response object which contains a message, response code, and a flag 
# to indicates if the error template page should be used instead of the base template
class AzureStorage:

    def __init__(self, app_config):
        
        self.app_config = app_config
        self.account_url = self.app_config['STORAGE_URL']
        self.container_name = self.app_config['CONTAINER_NAME']
        
        # Get a token credential for authentication
        token_credential = ClientSecretCredential(
            self.app_config['TENANT_ID'],
            self.app_config['CLIENT_ID'],
            self.app_config['CLIENT_SECRET']
        )
        
        # Create the BlobServiceClient and connect to the storage container
        try:
            self.blob_service_client = BlobServiceClient(account_url=self.account_url, credential=token_credential)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        except Exception as e:
            logger.error(e)

    # Validates the user is authorized and returns user and access information along with the Response object
    def validate_user(self, session, request):
        user = session["user"]["preferred_username"].lower()

        # Check if user token contains the proper role
        if 'roles' not in session["user"]:
            logger.warning(user + " not assigned any roles for this application")
            return dict(response=Response(message="User not assigned any roles for this application", status_code=401, error_flag=1))
        if not any(x in self.app_config['ROLES'].keys() for x in session["user"]["roles"]):
            logger.warning(user + " not assigned the proper role for access")
            return dict(response=Response(message="User not assigned the proper role for access", status_code=401, error_flag=1))

        

        # Get folders that user has access to
        folder_access = []
        for role in session["user"]["roles"]:
            folder_access += self.app_config["ROLES"][role]
        # Remove duplicate entries
        folder_access = unique(folder_access)

        # Get selected folder path or default to first available folder
        current_folder = request.args.get('folder')
        if current_folder is None:
            current_folder = folder_access[0]
        else:
            # Validate that user has access to the selected folder
            if current_folder not in folder_access:
                logger.warning(user + " not assigned access to folder: " + current_folder)
                return dict(response=Response(message="User not assigned access to this folder", status_code=401, error_flag=1))

        path = self.app_config["PATHS"][current_folder]
        logger.debug(user + " has been authorized on folder: " + current_folder)
        return dict(response=Response("User has been authorized"), 
                    user=user, 
                    folder_access=folder_access, 
                    current_folder=current_folder, 
                    path=path)

    # Function to walk an Azure Storage path and get all blobs and subdirectories
    def walk_blobs(self, user_session: UserStorageSession, sub_folder=""):
        # Initiate blob iterator on the search path
        search_path = user_session.path + sub_folder
        try:
            blob_list = self.container_client.walk_blobs(name_starts_with=search_path, include='metadata',
                                                         delimiter='/')
        except Exception as e:
            logger.error(e)
            return Response(message="Failed to get Blob List", status_code=400)

        new_folders = []
        for blob in blob_list:
            # Check if item is a directory and add to list of additional folders to walk
            if isinstance(blob, BlobPrefix):
                new_folders.append(remove_prefix(blob.name, user_session.path).rstrip("/"))
            else:
                # Try to get metadata for blob if it exists and check if user matches the
                # original upload user
                try:
                    metadata = getattr(blob, 'metadata')
                    if metadata is None:
                        logger.warning("Metadata missing from blob: " + blob.name + " Setting user to null")
                        uploaded_by = ""
                    else:
                        uploaded_by = metadata['uploaded_by'].lower()
                except AttributeError:
                    logger.warning("Metadata missing from blob: " + blob.name + " Setting user to null")
                    uploaded_by = ""

                # If blob uploaded by current user, enable deleteion
                if uploaded_by == user_session.user:
                    delete_enabled = True
                else:
                    delete_enabled = False

                # Convert size to KB
                size = int(blob.size / 1024)
                if size == 0:
                    size = "<1"

                # Add blob info to blob_table
                user_session.blob_table.append(dict(filename=blob.name.split("/")[-1],
                                                            path=blob.name.rsplit("/", 1)[0],
                                                            name=blob.name,
                                                            size=size,
                                                            uploaded_by=uploaded_by,
                                                            delete_enabled=delete_enabled))

        # Append discovered subfolders to folder list and recursively walk any new directories
        user_session.folder_list += new_folders
        for folder in new_folders:
            self.walk_blobs(user_session, folder + "/")

        return Response()

    # Upload blob to Azure Storage
    def upload_blob(self, file, subfolder, user_session: UserStorageSession):
        # Check if file was included in the Post, if not return warning
        filename = secure_filename(file.filename)
        if not filename:
            return Response(message="Must select a file to upload first!",status_code=400)

        if subfolder == '':
            upload_path = user_session.path
        else:
            upload_path = user_session.path + subfolder + "/"

        try:
            # Create a blob client using the local file name as the name for the blob
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name,
                                                                   blob=(upload_path + filename))
            try:
                # Check if blob already exists
                if blob_client.get_blob_properties()['size'] > 0:
                    logger.warning(filename + " already exists in the selected path. Skipping upload.")
                    return Response(message=filename +" already exists in the selected path",status_code=409,error_flag=2)
            except ResourceNotFoundError as e:
                # catch exception that indicates that the blob does not exist and we are good to upload file
                pass
            logger.info(user_session.user + " uploading " + filename + " to Azure Storage on path: " + upload_path)

            # create metadata including the uploading user's id
            metadata = {'uploaded_by': user_session.user}
            # Upload the file and measure upload time
            elapsed_time = time.time()
            blob_client.upload_blob(file, metadata=metadata)
            elapsed_time = round(time.time() - elapsed_time, 2)
            logger.info("Upload succeeded after " + str(elapsed_time) + " seconds for: " + filename)

            # Update the table display with the new blob
            user_session.blob_table.append(dict(name=blob_client.get_blob_properties().name,
                                                        size=blob_client.get_blob_properties().size,
                                                        uploaded_by=user_session.user,
                                                        delete_enabled=True))

        except Exception as e:
            logger.error(e)
            return Response(message="Failed to upload file",status_code=400,error_flag=1)


        return Response(message="Uploaded File Successfully",status_code=200)

    # Delete specified blob
    def delete_blob(self, user_session: UserStorageSession, blob_name):
        if blob_name is None:
            logger.warning(user_session.user + " sent delete request without specified blob name")
            return Response(message="No file specified for deletion",status_code=400)
        else:
            delete_count = 0
            for blob in user_session.blob_table:
                if blob['name'] == blob_name and blob['uploaded_by'] == user_session.user:
                    delete_count += 1
                    blob_client = self.blob_service_client.get_blob_client(container=self.container_name,
                                                                           blob=blob_name)
                    logger.info(user_session.user + " deleting blob: " + blob_name)
                    blob_client.delete_blob(delete_snapshots=False)
                    user_session.blob_table.remove(blob)

            if delete_count < 1:
                logger.warning(user_session.user + " sent delete request for: " + blob_name + " but blob was not found")
                return Response(message="File to delete was not found in the specified location",status_code=400)

        return Response(message="File deleted successfully",status_code=200)


# function to get unique values
def unique(list1):
    # insert the list to the set 
    list_set = set(list1)
    # convert the set to the list and return
    return (list(list_set))


# Remove prefix from string
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text
