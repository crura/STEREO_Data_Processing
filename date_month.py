import numpy as np
import os
import csv
import git


repo = git.Repo('.', search_parent_directories=True)
repo_path = repo.working_tree_dir

days_in_month = {
  1: 31,
  2: 28,
  3: 31,
  4: 30,
  5: 31,
  6: 30,
  7: 31,
  8: 31,
  9: 30,
  10: 31,
  11: 30,
  12: 31
}

def is_leap_year(year):
    if year % 4 == 0:
        if year % 100 == 0:
            if year % 400 == 0:
                return True
            else:
                return False
        else:
            return True
    else:
        return False

def get_days_in_month(month, year):
    if month == 2:
        if is_leap_year(year):
            return 29
        else:
            return 28
    else:
        return days_in_month[month]

month_day_dict = {}
for i in range(4,9):
    daylist = []
    for j in range(1,get_days_in_month(i, 2012)+1):
        daylist.append(j)
        # print('month: {} day: {}'.format(i, j))
    month_day_dict[i] = daylist[-1]

month_day_list = list(month_day_dict.items())
month_day_arr = np.array(month_day_list)
outpath = os.path.join(repo_path,'month_day_pair.csv')
# np.savetxt(outpath, month_day_arr.ravel(), delimiter=',')
with open (outpath, 'w') as f:
    w = csv.writer(f)
    # w.writeheader()
    # w.writerow(month_day_dict)
    w.writerows(month_day_dict.items())
