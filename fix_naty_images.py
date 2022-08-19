import os
import numpy as np
import scipy as sci
import matplotlib.pyplot as plt
from astropy.io import fits
from tqdm import tqdm

process_path = '/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/Naty_Images'
path = process_path + '/'
parent_list = os.listdir(process_path)
imagelist = []
headlist = []
for child in parent_list:

    if child == 'Corrected_Images':
        pass
    elif child == '.DS_Store':
        pass
    else:
        file = str(path + child)
        image_data = fits.getdata(file, ext=0)

        #print(np.isnan(np.sum(image_data)))

        # rectify nan values in image arrays
        if np.isnan(np.sum(image_data)) == True:    # if there are NaN values in array
            where_nan = np.where(np.isnan(image_data) ==True)   # find where in array NaN values exist
            nan_pairs = np.asarray(where_nan).T     # transform np.where array to index coordinate pairs of pixels
            min_value = image_data[np.where(np.isnan(image_data) ==False)].min()
            for i,j in nan_pairs:
                image_data[i,j] = min_value  # set NaN values of data to minimum value of finite pixels in array

        print(np.isnan(np.sum(image_data)), min_value)
        image_header = fits.getheader(file)
        hdu = fits.PrimaryHDU(data=image_data,header=image_header)
        pathnew = process_path + '/Corrected_Images'
        hdu.writeto(pathnew+'/{}'.format(child),overwrite=True)
