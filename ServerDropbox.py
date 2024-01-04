import requests 
import dropbox
from dropbox.exceptions import AuthError
import os
import json

SOURCE_PATH = r"/misc/work"
#SOURCE_PATH = r"C:\Users\yaniv\Desktop"

class ServerDropbox():
    def __init__(self):
        with open("secrets.json", "r") as json_file: # Read the secrets from the JSON file
            details = json.load(json_file)
        self.DROPBOX_ACCESS_TOKEN = None
        self.REFRESH_TOKEN = details["REFRESH_TOKEN"]
        self.APP_KEY = details["APP_KEY"]
        self.APP_SECRET = details["APP_SECRET"]
        self.connected_dropbox = None
        self.download_list = []
        self.sample_list = []

    
    def refresh_access_token(self):
        token_url = 'https://api.dropboxapi.com/oauth2/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.REFRESH_TOKEN,
            'client_id': self.APP_KEY,
            'client_secret': self.APP_SECRET
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.DROPBOX_ACCESS_TOKEN = token_data['access_token']
            self.REFRESH_TOKEN = token_data.get('refresh_token', self.REFRESH_TOKEN)
            
        else:
            raise Exception("Failed to refresh access token")
        
    def connect_to_dropbox(self):
        self.refresh_access_token()
        self.connected_dropbox = dropbox.Dropbox(self.DROPBOX_ACCESS_TOKEN)


    def get_files_without_cursor(self, folder_path):
        return self.connected_dropbox.files_list_folder(folder_path)

    # def get_files_with_cursor(self, cursor):
    #     return self.connected_dropbox.files_list_folder_continue(cursor)

    def generate_refresh_token(self): #should run only once, refresh token is not expired
        AUTHORIZATION_CODE = ''       #should get it from the url:https://www.dropbox.com/oauth2/authorize?client_id=<APP_KEY>&token_access_type=offline&response_type=code 
                                      #should fill your appkey in the url

        token_url = 'https://api.dropboxapi.com/oauth2/token'
        data = {
            'code': AUTHORIZATION_CODE,
            'grant_type': 'authorization_code'
        }
        auth = (self.APP_KEY, self.APP_SECRET)
        response = requests.post(token_url, data=data, auth=auth)

        if response.status_code == 200:
            token_data = response.json()
            self.DROPBOX_ACCESS_TOKEN = token_data['access_token']
            self.REFRESH_TOKEN = token_data['refresh_token']
        else:
            print("Token request failed:", response.status_code, response.text)
            exit(1)
        print("Access Token:", self.DROPBOX_ACCESS_TOKEN)
        print("Refresh Token:", self.REFRESH_TOKEN)

    
    def download_entry(self,entry, local_path):
        try:
            if isinstance(entry, dropbox.files.FileMetadata):
                if not os.path.exists(local_path):
                    with open(local_path, 'wb') as folder:
                        #download the .gz fiels
                        metadata, res = self.connected_dropbox.files_download(entry.path_display)
                        folder.write(res.content)
                        path_segments = entry.path_display.split('/')
                        subject_path = '/'.join(path_segments[:4])
                        sample_path = '/'.join(path_segments[:6])

                        self.download_list.append(subject_path)
                        self.sample_list.append(sample_path)
                # else:
                #     print(f"The file {local_path} exists.")
                        
            elif isinstance(entry, dropbox.files.FolderMetadata):
                # For folders, create a corresponding local folder
                os.makedirs(local_path, exist_ok=True)
                # Download the contents of the folder recursively
                self.download_folder_contents(entry.path_display, local_path)
                
        except dropbox.exceptions.HttpError as e:
            print(f"Error downloading {entry.path_display}: {e}")

    def download_folder_contents(self, folder_path, local_path):
        # List the contents of the folder
        result = self.connected_dropbox.files_list_folder(folder_path)
        for entry in result.entries:
            entry_local_path = os.path.join(local_path, entry.name)
            self.download_entry(entry, entry_local_path)

    
    def upload_folder(self, local_folder_path, dropbox_folder_path):
        """
        Uploads the contents of a local folder to a Dropbox folder, handling symbolic links.
        """
        for root, dirs, files in os.walk(local_folder_path, followlinks=True):  # followlinks=True to traverse into directories pointed to by symlinks
            for filename in files:
                local_path = os.path.join(root, filename)
                # Handle symbolic links for files
                if os.path.islink(local_path):
                    local_path = '/misc' + os.path.realpath(local_path)
                
                #relative_path = os.path.relpath(local_path, local_folder_path)
                after_substring = extract_after_substring(local_path, '/misc/work/Dropbox/Macaque R24/results')
                dropbox_path = dropbox_folder_path.replace("\\", "/") + after_substring

                self.upload_file(local_path, dropbox_path)

            #for dirname in dirs:
            #    self.create_folder_in_dropbox(os.path.join(dropbox_folder_path, dirname).replace("\\", "/"))

            # Upload contents of resolved directories
            #for resolved_dir, dropbox_resolved_dir in resolved_dirs:
            #    self.upload_folder(resolved_dir, dropbox_resolved_dir)

    def upload_file(self, local_file_path, dropbox_file_path):
        """
        Uploads a single file to Dropbox.
        """
        try:
            if os.path.isdir(local_file_path):
                self.upload_folder(local_file_path, dropbox_file_path)
            else:
                with open(local_file_path, 'rb') as f:
                    self.connected_dropbox.files_upload(f.read(), dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))
        except FileNotFoundError:
            print(f"File not found: {local_file_path}")
        except PermissionError:
            print(f"Permission denied for file: {local_file_path}")
        except dropbox.exceptions.ApiError as e:
            print(f"Dropbox API error: {e} \nfor file: {local_file_path}")
        except Exception as e:
            print(f"An unexpected error occurred: {e} \nfor file: {local_file_path}")

    def create_folder_in_dropbox(self, dropbox_folder_path):
        """
        Creates a folder in Dropbox if it doesn't already exist.
        """
        try:
            print("creating folder - ", dropbox_folder_path)
            self.connected_dropbox.files_create_folder_v2(dropbox_folder_path)
        except dropbox.exceptions.ApiError as e:
            if e.error.is_path() and e.error.get_path().is_conflict():
                print(f"Folder '{dropbox_folder_path}' already exists on Dropbox.")
            else:
                raise

    

def extract_after_substring(full_path, substring):
    # Splitting the path based on the substring and taking the part after it
    parts = full_path.split(substring)
    if len(parts) > 1:
        return parts[1]
    else:
        return ""
