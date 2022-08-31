import os
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import scipy as sci
import matplotlib
from tqdm import tqdm_notebook
import sunpy.version
import sunpy.map

from scipy.fft import fft2 # 2-D discrete Fourier Transform
from scipy.fft import fftshift # Shift the zero-frequency component to the center of the spectrum.
#from radialProfile.py import azimuthalAverage
# import radialProfile
from scipy.io import readsav
idl_save = readsav('/Volumes/Seagate/Chris/2017_Images/parameters_safe.sav')
process_path = idl_save['spath'].decode()#str(idl_save['spath'],'utf-8')
year_month_day_print = idl_save['year_month_day_print'].decode()
#importlib.reload(radialProfile)
# azimuthalAverage = radialProfile.azimuthalAverage

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

# for i in tqdm_notebook(range(21,22)):

# day = str(i)
#"/Users/Chris/Desktop/Goddard Research/sequential_images/processed/201407{}/".format(day)
path = process_path + '/'
parent_list = os.listdir(process_path)
imagelist = []
headlist = []
for child in parent_list:
    # Ignore .DSStore file (common formatting with mac, easier to ignore than delete)
    if child == '.DS_Store':
        print('no')
        pass            #pass
    elif child == 'Representative_Images':
        pass
    elif child.endswith('0_0P4c1A.fts') ==False:
        print('file: {} incorrectly processed, logging and aborting processing'.format(child))
        # first file logger
        logger = setup_logger('process_logger', '/Volumes/Seagate/Chris/2017_Images/process_events.log')
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
    # elif child == '201708{}_rep_avg.fts'.format(day):
    #     print('no')
    #     pass
    # elif child == '201708{}_rep_med.fts'.format(day):
    #     print('no')
    #     pass            #pass
    # elif child == '201708{}_rep_max.fts'.format(day):
    #     print('no')
    #     pass            #pass
    else:
    # For each file in directory, pull up fits header and search for polarization variable
    #print out to ensure each file has same polarization angle


        file = str(path + child)
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
        # if child == '20140705_133500_0P4c1A.fts':
        #     plt.savefig('2017081_133500_0P4c1A.png')
        #plt.show()
        plt.close()
#         imagelist.append(image_data)
#         plt.figure()
#         plt.imshow(image_data, cmap='viridis',vmin=0,interpolation='nearest')
#         plt.colorbar()
#         plt.clim(np.mean(image_data),np.mean(image_data)+2*np.std(image_data))
#         current_cmap = matplotlib.cm.get_cmap()
#         current_cmap.set_bad(color='red')
#         plt.title('image_data')
#         plt.show()


# plt.figure()
imcombmean = np.mean(imagelist, axis=0)
# plt.imshow(imcombmean, cmap='viridis',vmin=0,interpolation='nearest')
# plt.colorbar()
# plt.clim(np.mean(imcombmean),np.mean(imcombmean)+2*np.std(imcombmean))
# current_cmap = matplotlib.cm.get_cmap()
# current_cmap.set_bad(color='red')
# plt.title('representative mean {} 09:35:00 - 17:35:00'.format(year_month_day_print))
# #plt.savefig('representative_mean201708{}.png'.format(day))
# # plt.show()
# plt.close()


# plt.figure(1)
# plt.clf()
# plt.imshow( np.log10( imcombmean ), cmap=plt.cm.Greys)
# plt.title('representative mean {} 09:35:00 - 17:35:00 log scale'.format(year_month_day_print))
# plt.colorbar()

# plt.figure()
imcombmed = np.median(imagelist, axis=0)
# plt.imshow(imcombmed, cmap='viridis',vmin=0,interpolation='nearest')
# plt.colorbar()
# plt.clim(np.mean(imcombmed),np.mean(imcombmed)+2*np.std(imcombmed))
# current_cmap = matplotlib.cm.get_cmap()
# current_cmap.set_bad(color='red')
# plt.title('representative median {} 13:35:00 - 17:35:00'.format(year_month_day_print))
# #plt.savefig('representative_median201708{}.png'.format(day))
# # plt.show()
# plt.close()


# plt.figure(1)
# plt.clf()
# plt.imshow( np.log10( imcombmed ), cmap=plt.cm.Greys)
# plt.title('representative median {} 13:35:00 - 17:35:00 log scale'.format(year_month_day_print))
# plt.colorbar()
#
#
# plt.figure()
# imcombmax = np.max(imagelist, axis=0)
# plt.imshow(imcombmax, cmap='viridis',vmin=0,interpolation='nearest')
# plt.colorbar()
# plt.clim(np.mean(imcombmax),np.mean(imcombmax)+2*np.std(imcombmax))
# current_cmap = matplotlib.cm.get_cmap()
# current_cmap.set_bad(color='red')
# plt.title('representative maximum {} 13:35:00 - 17:35:00'.format(year_month_day_print))
# #plt.savefig('representative_maximum201708{}.png'.format(day))
# # plt.show()
# plt.close()


# plt.figure(1)
# plt.clf()
# plt.imshow( np.log10( imcombmax ), cmap=plt.cm.Greys)
# plt.colorbar()

#
# F1max = fft2(imcombmax)
#
# # Now shift the quadrants around so that low spatial frequencies are in
# # the center of the 2D fourier transformed image.
# F2max = fftshift( F1max )
#
# # Calculate a 2D power spectrum
# psd2Dmax = np.abs( F2max )**2
#
# # Calculate the azimuthally averaged 1D power spectrum
# psd1Dmax = azimuthalAverage(psd2Dmax)
#
#
# F1med = fft2(imcombmed)
#
# # Now shift the quadrants around so that low spatial frequencies are in
# # the center of the 2D fourier transformed image.
# F2med = fftshift( F1med )
#
# # Calculate a 2D power spectrum
# psd2Dmed = np.abs( F2med )**2
#
# # Calculate the azimuthally averaged 1D power spectrum
# psd1Dmed = azimuthalAverage(psd2Dmed)
#
#
# F1mean = fft2(imcombmean)
#
# # Now shift the quadrants around so that low spatial frequencies are in
# # the center of the 2D fourier transformed image.
# F2mean = fftshift( F1mean )
#
# # Calculate a 2D power spectrum
# psd2Dmean = np.abs( F2mean )**2
#
# # Calculate the azimuthally averaged 1D power spectrum
# psd1Dmean = azimuthalAverage(psd2Dmean)
#
#
#
# F1 = fft2(image_data)
#
# # Now shift the quadrants around so that low spatial frequencies are in
# # the center of the 2D fourier transformed image.
# F2 = fftshift( F1 )
#
# # Calculate a 2D power spectrum
# psd2D = np.abs( F2 )**2
#
# # Calculate the azimuthally averaged 1D power spectrum
# psd1D = azimuthalAverage(psd2D)


# import seaborn as sns
# sns.set()

#
# plt.clf()
# plt.semilogy( psd1D ,color='green',label='polarized brightness image')
# plt.semilogy( psd1Dmed ,color='blue',label='median filtered stack')
# plt.semilogy( psd1Dmax ,color='red',label='max filtered stack')
# plt.semilogy( psd1Dmean ,color='orange',label='average filtered stack')
# plt.xlabel('Spatial Frequency')
# plt.ylabel('Power')
# plt.title('Power Spectrum 2014-05-0{} 17:40:00 - 21:40:00'.format(day))
# plt.legend()
#
# #plt.savefig('Power_Spectrum 2014-05-0{}'.format(day))
#
#
# plt.show()

timelist = []
for i in headlist:
    timelist.append(i['DATE-OBS'])
timelist.sort()

head = headlist[int(len(headlist)/2)]
# old = head['DATE-OBS']
# head['DATE-OBS'] = (old, '{} - {}'.format(timelist[0],timelist[-1]))
# head['DATE-OBS'] = '{} - {}'.format(timelist[0],timelist[-1])


pathnew = process_path + '/Representative_Images'

import os
if not os.path.exists(pathnew):
    os.makedirs(pathnew)

hdumean = fits.PrimaryHDU(data=imcombmean,header=head)
#hdumean.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_avg.fts',overwrite=True)
hdumean.writeto(pathnew+'/{}_rep_avg.fts'.format(year_month_day_print),overwrite=True)

hdumed = fits.PrimaryHDU(data=imcombmed,header=head)
#hdumed.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_med.fts',overwrite=True)
hdumed.writeto(pathnew+'/{}_rep_med.fts'.format(year_month_day_print),overwrite=True)

# hdumax = fits.PrimaryHDU(data=imcombmax,header=head)
# #hdumax.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_max.fts',overwrite=True)
# hdumax.writeto(pathnew+'/{}_rep_max.fts'.format(year_month_day_print),overwrite=True)



hdumean = fits.PrimaryHDU(data=imcombmean,header=head)
#hdumean.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_avg.fts',overwrite=True)
hdumean.writeto('/Volumes/Seagate/Chris/2017_Images/Representative_Average_Images/{}_rep_avg.fts'.format(year_month_day_print),overwrite=True)

hdumed = fits.PrimaryHDU(data=imcombmed,header=head)
#hdumed.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_med.fts',overwrite=True)
hdumed.writeto('/Volumes/Seagate/Chris/2017_Images/Representative_Median_Images/{}_rep_med.fts'.format(year_month_day_print),overwrite=True)
#
# hdumax = fits.PrimaryHDU(data=imcombmax,header=head)
# #hdumax.writeto('/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/All images/rep_max.fts',overwrite=True)
# hdumax.writeto('/Volumes/Seagate/Chris/2017_Images/Representative_Maximum_Images/{}_rep_max.fts'.format(year_month_day_print),overwrite=True)


print('finished')


fits_dir = pathnew+'/{}_rep_med.fts'.format(year_month_day_print)


data = fits.getdata(fits_dir)
head = fits.getheader(fits_dir)

fitsmap = sunpy.map.Map(data, head)

# fits_dir_mlso = pathnew.parent.parent.joinpath(str(idl_save['fits_directory'],'utf-8'))
#
# fig = plt.figure(figsize=(12, 5))
# # ax1 = fig.add_subplot(1, 2, 1, projection=fitsmap)
# fitsmap.plot(norm=matplotlib.colors.LogNorm())
# plt.show()
