from datetime import datetime, timedelta
from sunpy.net import vso, attrs as a
import astropy.units as u
import subprocess
from pathlib import Path
import git
import os
import shutil
import yaml
 
with open("config.yaml", "r") as stream:
    try:
        yaml_parse = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

input_path = yaml_parse['input_path']

repo = git.Repo('.', search_parent_directories=True)
repo_path = repo.working_tree_dir

main_path = Path(input_path)

client = vso.VSOClient()

def determine_datetime_from_decimal_day(year, month, day_dec):
    start = day_dec
    day = int(start)
    rem = start - day

    base = datetime(year, month, day)
    result = base + timedelta(seconds=(base.replace(day=base.day + 1) - base).total_seconds() * rem)
    return result


start_datetime = determine_datetime_from_decimal_day(2010,5,20.0002) # CR 2097 begin
end_datetime = determine_datetime_from_decimal_day(2010,6,16.2041) # CR 2098 begin
CR_length = end_datetime - start_datetime


for i in range(CR_length.days):
    time1 = start_datetime + timedelta(days=i)
    time2 = time1 + timedelta(hours=8, seconds=18)
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
    
    query_table = client.search(
        a.Time(time1, time2), 
        a.Instrument.secchi, a.Detector.cor1,
        response_format="table")
    
    for x in query_table:
        # If not a sequential image, remove from query table
        if "seq" not in x['fileid']:
            query_table.remove_row(x.index)
    client.fetch(query_table, path='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/test_path')
    # subprocess.run(["mkdir", "-p", time1.strftime('%m-%d-%Y')])
    # subprocess.run(["cd", time1.strftime('%m-%d-%Y')])
    # subprocess.run(["mkdir", "-p", 'A'])
    # subprocess.run(["mkdir", "-p", 'B'])
    # subprocess.run(["mv", Path.joinpath(path_download, '*s4c1a*'), path_a])
    # subprocess.run(["mv", Path.joinpath(path_download, '*s4c1b*'), path_b])


    # Iterate through files in download directory
    for filename in os.listdir(path_download):
        # Check if the file contains the string pattern 's4c1a' (sequential polarized image from STEREO A)
        if 's4c1a' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(path_download, filename)
            destination_path = os.path.join(path_a, filename)

            # Move the file to directory A
            shutil.move(source_path, destination_path)
        # Check if the file contains the string pattern 's4c1b' (sequential polarized image from STEREO B)
        elif 's4c1b' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(path_download, filename)
            destination_path = os.path.join(path_b, filename)

            # Move the file to directory A
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