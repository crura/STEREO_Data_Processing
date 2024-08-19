from datetime import datetime, timedelta
from sunpy.net import vso, attrs as a
import astropy.units as u
import subprocess
from pathlib import Path
import git
import os
import shutil
import yaml
from sunpy.net import Fido
import urllib.request
import ssl
 
with open("config.yaml", "r") as stream:
    try:
        yaml_parse = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

input_path = yaml_parse['input_path']
specific_dates = yaml_parse['specific_dates']  # Expecting a list of dates in 'YYYY-MM-DD' format
start_time = yaml_parse.get('start_time', '09:35:00')  # Default to 09:35:00 if not specified
end_time = yaml_parse.get('end_time', '18:35:00')      # Default to 18:35:00 if not specified

repo = git.Repo('.', search_parent_directories=True)
repo_path = repo.working_tree_dir

main_path = Path(input_path)

client = vso.VSOClient()

# Parse the start and end times, now including seconds
start_hour, start_minute, start_second = map(int, start_time.split(':'))
end_hour, end_minute, end_second = map(int, end_time.split(':'))

# Convert the specific dates from strings to datetime objects
specific_dates = [datetime.strptime(date_str, '%Y-%m-%d') for date_str in specific_dates]

for date in specific_dates:
    # Set the start and end times for each specific date
    time1 = date.replace(hour=start_hour, minute=start_minute, second=start_second)
    time2 = date.replace(hour=end_hour, minute=end_minute, second=end_second)

    str_time = time1.strftime('%m-%d-%Y')

    path_a = Path(os.path.join(main_path, 'A', str_time))
    path_a.mkdir(parents=True, exist_ok=True)
    path_b = Path(os.path.join(main_path, 'B', str_time))
    path_b.mkdir(parents=True, exist_ok=True)
    path_download = Path(os.path.join(main_path, 'temp'))
    path_download.mkdir(parents=True, exist_ok=True)
    path_processed_a = Path(os.path.join(path_a, 'processed'))
    path_processed_a.mkdir(parents=True, exist_ok=True)
    path_processed_b = Path(os.path.join(path_b, 'processed'))
    path_processed_b.mkdir(parents=True, exist_ok=True)

    query_table2 = Fido.search(
        a.Time(time1, time2), 
        a.Instrument.secchi, a.Detector.cor1)

    for x in query_table2[0]:
        # If not a sequential image, remove from query table
        if "seq" not in x['fileid']:
            query_table2[0].remove_row(x.index)
    
    downloaded_files = Fido.fetch(query_table2, path=path_download)

    # Create an unverified SSL context
    context = ssl._create_unverified_context()

    if len(downloaded_files.errors) > 0:
        print('Errors found in download, retrying on failed files')
    for error in downloaded_files.errors:
        url = error.url
        file_path = os.path.join(path_download, url.split('/')[-1])
        
        # Use urlopen to retrieve the file with the unverified context
        try:
            with urllib.request.urlopen(url, context=context) as response, open(file_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Successfully downloaded {url}")
        except urllib.error.URLError as e:
            print(f"URL error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    # Iterate through files in download directory
    for filename in os.listdir(path_download):
        # Check if the file contains the string pattern 's4c1a' (sequential polarized image from STEREO A)
        if 's4c1a' or 's4c1A' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(path_download, filename)
            destination_path = os.path.join(path_a, filename)

            # Move the file to directory A
            shutil.move(source_path, destination_path)
        # Check if the file contains the string pattern 's4c1b' (sequential polarized image from STEREO B)
        elif 's4c1b' or 's4c1B' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(path_download, filename)
            destination_path = os.path.join(path_b, filename)

            # Move the file to directory B
            shutil.move(source_path, destination_path)

    # time1 = datetime(2010, 4, 29, 0, 0, 9)
    # time2 = time1 + timedelta(hours=1)
    # client.fetch(client.search(
    #     a.Time(time1, time2), a.Sample(5*u.minute),
    #     a.Instrument.secchi, a.Detector.cor1,
    #     response_format="table"), path='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/Test_Download')

    # time1 = datetime(2010, 4, 29, 0, 0, 18)
    # time2 = time1 + timedelta(hours=1)
    # client.fetch(client.search(
    #     a.Time(time1, time2), a.Sample(5*u.minute),
    #     a.Instrument.secchi, a.Detector.cor1,
    #     response_format="table"), path='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/Test_Download')

    # time1 = datetime(2010, 4, 29, 0, 0, 1)
    # time2 = time1 + timedelta(hours=1)
    # client.fetch(client.search(
    #     a.Time(time1, time2), a.Sample(5*u.minute),
    #     a.Instrument.secchi, a.Detector.cor1,
    #     response_format="table"), path='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/Test_Download')