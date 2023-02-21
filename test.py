import unittest
import os
from astropy.io import fits
from datetime import datetime, timedelta
from dateutil import parser

class TestHeaderDate(unittest.TestCase):
    def setUp(self):
        self.process_path = '/Volumes/Seagate/Chris/2012_Images_match/Representative_Median_Images'
        self.parent_list = os.listdir(self.process_path)
    def test_dates_match(self):
        for index, element in enumerate(self.parent_list):
            if element == '.DS_Store':
                pass
            else:
                # test headers of all fits files match date listed on filename
                fits_path = os.path.join(self.process_path,element)
                head = fits.getheader(fits_path)
                headerdate = parser.parse(head['DATE-OBS'])
                filedate = parser.parse(element.split('_')[0])
                self.assertLess(headerdate-filedate, timedelta(days=1))

# main function
if __name__ == '__main__':
    unittest.main()
