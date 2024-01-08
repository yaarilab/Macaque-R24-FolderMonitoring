import time
import os
import warnings
import json
from dropbox.exceptions import AuthError
from FolderMonitor import FolderMonitor
from ServerDropbox import ServerDropbox
#from watchdog.observers import Observer

# Ignore warnings
warnings.simplefilter("ignore")

# Define the file paths and Dropbox-related settings
#SOURCE_PATH = r"C:\Users\yaniv\Desktop\Dropbox" # this is for testing
SOURCE_PATH = r"/misc/work/Dropbox"
FOLDER_FOR_DOWNLOADS = os.path.join(SOURCE_PATH, "Macaque R24/sequencing/")
DROPBOX_FOLDER_PATH = '/macaque r24/sequencing'.lower() #where the folder you want to monitor lacated in dropbox
DROPBOX_MISSING_FILE_PATH = '/macaque r24/results/missing.xlsx'.lower()
SERVER_MISSING_FILE_PATH = os.path.join(SOURCE_PATH, 'Macaque R24/results/missing.xlsx')
ALL_SAMPLES_PATH = os.path.join(SOURCE_PATH, 'Macaque R24/sequencing/all_samples_file.txt') 
RESULT_FOLDER_PATH = os.path.join(SOURCE_PATH, 'Macaque R24/results')
DROPBOX_RESULT_PATH = '/macaque r24/results'.lower()
ANNOTATED_CURRENT_RESULTS = r'/misc/work/sequence_data_store/Macaque_R24/runs/current/annotated/'

# Function to monitor Dropbox folder
def monitor_dropbox_folder():
    if not os.path.exists(ALL_SAMPLES_PATH):
        # If the file doesn't exist, create it and write some initial content
            with open(ALL_SAMPLES_PATH, "w") as new_file:
                print(ALL_SAMPLES_PATH + " created")
    server_dropbox = ServerDropbox()  # Initialize ServerDropbox class
    folder_monitor = FolderMonitor()  # Initialize FolderMonitor class
    start_new_check(server_dropbox, folder_monitor)
    print("finish daily run")
    print("start to upload result folder")
    server_dropbox.start_upload_results(RESULT_FOLDER_PATH, ANNOTATED_CURRENT_RESULTS, DROPBOX_RESULT_PATH)

# Function to initiate a new Dropbox folder check
def start_new_check(server_dropbox, folder_monitor):
    past_day_subjects = []
    server_dropbox.connect_to_dropbox()  # Connect to Dropbox
    result = server_dropbox.get_files_without_cursor(DROPBOX_FOLDER_PATH)

    try:
        past_day_subjects = download_new_data_from_past_day(result, server_dropbox)
        folder_monitor.past_24_sample = server_dropbox.sample_list
        all_samples = update_samples_file(past_day_subjects)

        for subject_path in all_samples:
            if subject_path != '':
                folder_monitor.check_new_subject(subject_path) 
        
        folder_monitor.end_of_day_summary()
        folder_monitor.update_pipeline_table()

    except Exception as e:
        print(e)


def download_new_data_from_past_day(result, server_dropbox):
    past_day_subjects = []
    if result.entries != []:
            for entry in result.entries:
                file_path = entry.path_display
                local_path = os.path.join(FOLDER_FOR_DOWNLOADS, entry.name)
                server_dropbox.download_entry(entry, local_path)
                
                if file_path in server_dropbox.download_list:
                    print(f"Finished download {file_path}")
                    past_day_subjects.append((SOURCE_PATH + file_path))

            print("Successfully downloaded all files")

    else:
        print("No new data from past day")
    
    return past_day_subjects

def update_samples_file(past_day_subjects):
    all_samples = open(ALL_SAMPLES_PATH, 'r').readlines()
    all_samples = [sample.replace('\n', '') for sample in all_samples]
    with open(ALL_SAMPLES_PATH, 'a') as all_samples_file:
        for subject_path in past_day_subjects:
            # Check if subject_path not in lines
            if subject_path not in all_samples:
                all_samples.append(subject_path)
                all_samples_file.write(subject_path + '\n')
    
    return all_samples


# Main function
if __name__ == "__main__":
    monitor_dropbox_folder()

