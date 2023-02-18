function test, directory

  spawn, 'git rev-parse --show-toplevel', git_repo
  data = read_csv(git_repo + '/month_day_pair.csv')

  fname = '/Volumes/Seagate/Chris/2012_Images_match/process_error_log_2012.log'
  fname2 = '/Volumes/Seagate/Chris/2012_Images_match/process_log_2012.log'
  OPENW,1,fname
  OPENW,2,fname2

  list1 = data.field1
  list2 = data.field2


  foreach element, list1 do begin
    daylist = []
    j = fix(element) ;month

   foreach element2, list2[element-list1[0]] do begin

    arr = linspace(1,element2,element2)
    foreach element3, arr do begin ;daylist = [daylist, fix(element3)]
      i = fix(element3) ;day

      ; Download each file given by cor1_pbseries
      secchi_path = getenv('secchi') + '/lz'
      ; if last day of the month, second timestamp is first day of next month
      if (i EQ fix(arr[-1])) then begin
        time_1_string = timestamp(year = 2012, month = j, day = i, hour = 16, minute = 35, second = 15)
        time_2_string = timestamp(year = 2012, month = j+1, day = 1, hour = 0, minute = 45, second = 25)
      endif else begin
        time_1_string = timestamp(year = 2012, month = j, day = i, hour = 16, minute = 35, second = 15)
        time_2_string = timestamp(year = 2012, month = j, day = i+1, hour = 0, minute = 45, second = 25)
      ENDELSE
      print,j
      print,i
      savestring = timestamp(year = 2012, month = j, day = i)
      CAT = COR1_PBSERIES( [time_1_string, time_2_string], 'Ahead')
      file = cat.filename
      foreach hi, file do begin
        local_path = hi
        soho_path = 'https://stereo-ssc.nascom.nasa.gov/data/ins_data/secchi'
        online_file_path = repstr(local_path,secchi_path,soho_path)
        command_3 = 'mkdir -p ' + strmid(local_path,0,61)
        spawn, command_3
        command_string = 'wget -O ' + local_path + ' ' + online_file_path
        spawn, command_string
      endforeach
      spath = '/Volumes/Seagate/Chris/2012_Images_match/A/' + savestring
      comand_string_2 = 'mkdir -p ' + spath
      spawn, comand_string_2
      year_month_day_print = savestring
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB

      process_count = string(n_elements(file)/3)
      cd, spath
      file_list_2 = FILE_SEARCH('*.fts')
      fitsnew = readfits(file_list_2[-1])
      image_size = size(fitsnew,/dimensions)
      str = string(image_size[0])
      str1 = string(image_size[1])
      image_shape = str.Compress() + 'x' + str1.Compress()
      printf,2,'file ' + savestring + ' rep image represents ' + process_count.Compress() + ' images and has size of ' + image_shape

      save,spath,year_month_day_print,filename='/Volumes/Seagate/Chris/2012_Images_match/parameters.sav'
      spawn, 'cp /Volumes/Seagate/Chris/2012_Images_match/parameters.sav /Volumes/Seagate/Chris/2012_Images_match/parameters_safe.sav'

      spawn, 'python /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/produce_representative_image.py'
      endforeach

    endforeach

  endforeach

  close,1
  close,2
  return, data

END
