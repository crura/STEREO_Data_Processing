function test, directory

  spawn, 'git rev-parse --show-toplevel', git_repo
  data = read_csv(git_repo + '/month_day_pair.csv')


  ; Download each file given by cor1_pbseries
  secchi_path = getenv('secchi') + '/lz'
  time_1_string = '2012-' + monthstring + '-' + istring +' 16:35:00'
  time_2_string = '2012-' + monthstring + '-' + istring +' 16:35:00'
  time_1_string = timestamp(year = 2012, month = 7, day = 1, hour = 16, minute = 35, second = 15)
  time_2_string = timestamp(year = 2012, month = 7, day = 2, hour = 0, minute = 45, second = 25)
  CAT = COR1_PBSERIES( [time_1_string, time_2_string], 'Ahead')
  file = cat.filename
  foreach hi, file do begin
  local_path = hi
  soho_path = 'https://stereo-ssc.nascom.nasa.gov/data/ins_data/secchi'
  online_file_path = repstr(local_path,secchi_path,soho_path)
  command_string = 'wget -O ' + local_path + ' ' + online_file_path
  spawn, command_string
  endforeach

  secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB





  return, data

END
