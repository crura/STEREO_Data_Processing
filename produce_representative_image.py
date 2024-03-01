import os
from os import walk
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import scipy as sci
import matplotlib
from tqdm import tqdm
import sunpy.version
import sunpy.map
from pathlib import Path

from scipy.fft import fft2 # 2-D discrete Fourier Transform
from scipy.fft import fftshift # Shift the zero-frequency component to the center of the spectrum.
#from radialProfile.py import azimuthalAverage
# import radialProfile
from scipy.io import readsav
import yaml

file_path = Path(__file__).resolve()
repo_path = file_path.parent
 
with open(Path(os.path.join(repo_path, "config.yaml")), "r") as stream:
    try:
        yaml_parse = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

input_path = yaml_parse['input_path']

import logging
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def process_images(control_path):
    
    import os
    paths = [x[0] for x in walk(control_path)]

    processed_paths = []

    for x in paths:
        if "processed" in x and "Representative_Images" not in x:
            processed_paths.append(x)


    for i in tqdm(processed_paths):

    # day = str(i)
    #"/Users/Chris/Desktop/Goddard Research/sequential_images/processed/201407{}/".format(day)
        process_path = i
        path = process_path + '/'
        parent_list = os.listdir(process_path)
        if not parent_list:
            print('no files in directory')
            pass
        else:
            imagelist = []
            headlist = []
            for child in parent_list:
                # Ignore .DSStore file (common formatting with mac, easier to ignore than delete)
                if child == '.DS_Store':
                    print('no')
                    pass            #pass
                elif child == 'Representative_Images':
                    pass
                elif child.endswith('0_0P4c1A.fts') ==False and child.endswith('0_0P4c1B.fts') ==False:
                    print('file: {} incorrectly processed, logging and aborting processing'.format(child))
                    # first file logger
                    logger = setup_logger('process_logger', '/Volumes/Seagate/Chris/2010_Images_match/process_events.log')
                    logger.info('file: {} incorrectly processed'.format(child))
                    logger.handlers.clear()
                    break
                # elif child == 'rep_avg.fts':
                #     print('no')
                #     pass            #pass
                # elif child == 'rep_max.fts':
                #     print('no')
                #     pass            #pass
                # elif child == 'rep_med.fts':
                #     print('no')
                #     pass           # pass
                # elif child == '201208{}_rep_avg.fts'.format(day):
                #     print('no')
                #     pass
                # elif child == '201208{}_rep_med.fts'.format(day):
                #     print('no')
                #     pass            #pass
                # elif child == '201208{}_rep_max.fts'.format(day):
                #     print('no')
                #     pass            #pass
                else:
                # For each file in directory, pull up fits header and search for polarization variable
                #print out to ensure each file has same polarization angle


                    file = os.path.join(process_path,child)
                    image_data = fits.getdata(file, ext=0)

                    # rectify nan values in image arrays
                    if np.isnan(np.sum(image_data)) == True:    # if there are NaN values in array
                        where_nan = np.where(np.isnan(image_data) ==True)   # find where in array NaN values exist
                        nan_pairs = np.asarray(where_nan).T     # transform np.where array to index coordinate pairs of pixels
                        for i,j in nan_pairs:
                            image_data[i,j] = image_data[np.where(np.isnan(image_data) ==False)].min()    # set NaN values of data to minimum value of finite pixels in array

                    imagelist.append(image_data)
                    head_data = fits.getheader(file)
                    headlist.append(head_data)
                    fits.getheader(file)
                    hdul = fits.open(file)#imagelist.append(image_data)
                    plt.figure()
                    plt.imshow(image_data, cmap='viridis',vmin=0,interpolation='nearest')
                    plt.colorbar()
                    plt.clim(np.mean(image_data),np.mean(image_data)+2*np.std(image_data))
                    current_cmap = matplotlib.cm.get_cmap()
                    current_cmap.set_bad(color='red')
                    plt.title('{}'.format(child))
                    plt.close()

            imcombmean = np.mean(imagelist, axis=0)
            imcombmed = np.median(imagelist, axis=0)


            timelist = []
            for i in headlist:
                timelist.append(i['DATE-OBS'])
            timelist.sort()

            head = headlist[int(len(headlist)/2)]
            # old = head['DATE-OBS']
            # head['DATE-OBS'] = (old, '{} - {}'.format(timelist[0],timelist[-1]))
            # head['DATE-OBS'] = '{} - {}'.format(timelist[0],timelist[-1])


            pathnew = process_path + '/Representative_Images'

            if not os.path.exists(pathnew):
                os.makedirs(pathnew)

            year_month_day_print = process_path.split('/')[-2]

            hdumean = fits.PrimaryHDU(data=imcombmean,header=head)
            #hdumean.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_avg.fts',overwrite=True)
            hdumean.writeto(pathnew+'/{}_rep_avg.fts'.format(year_month_day_print),overwrite=True)

            hdumed = fits.PrimaryHDU(data=imcombmed,header=head)
            #hdumed.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_med.fts',overwrite=True)
            hdumed.writeto(pathnew+'/{}_rep_med.fts'.format(year_month_day_print),overwrite=True)

            # hdumax = fits.PrimaryHDU(data=imcombmax,header=head)
            # #hdumax.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_max.fts',overwrite=True)
            # hdumax.writeto(pathnew+'/{}_rep_max.fts'.format(year_month_day_print),overwrite=True)



            path_rep = Path(os.path.join(control_path, 'Representative_Images'))
            path_rep.mkdir(parents=True, exist_ok=True)

            hdumean = fits.PrimaryHDU(data=imcombmean,header=head)
            #hdumean.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_avg.fts',overwrite=True)
            hdumean.writeto('{}/{}_rep_avg.fts'.format(path_rep,year_month_day_print),overwrite=True)

            hdumed = fits.PrimaryHDU(data=imcombmed,header=head)
            #hdumed.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_med.fts',overwrite=True)
            hdumed.writeto('{}/{}_rep_med.fts'.format(path_rep,year_month_day_print),overwrite=True)
            #
            # hdumax = fits.PrimaryHDU(data=imcombmax,header=head)
            # #hdumax.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_max.fts',overwrite=True)
            # hdumax.writeto('/Volumes/Seagate/Chris/2012_Images_match/Representative_Maximum_Images/{}_rep_max.fts'.format(year_month_day_print),overwrite=True)


    print('finished')


main_path_a = Path(input_path + '/A')
process_images(main_path_a)

main_path_b = Path(input_path + '/B')
process_images(main_path_b)
# fits_dir = pathnew+'/{}_rep_med.fts'.format(year_month_day_print)


# data = fits.getdata(fits_dir)
# head = fits.getheader(fits_dir)

# fitsmap = sunpy.map.Map(data, head)

# fits_dir_mlso = pathnew.parent.parent.joinpath(str(idl_save['fits_directory'],'utf-8'))
#
# fig = plt.figure(figsize=(12, 5))
# # ax1 = fig.add_subplot(1, 2, 1, projection=fitsmap)
# fitsmap.plot(norm=matplotlib.colors.LogNorm())
# plt.show()
