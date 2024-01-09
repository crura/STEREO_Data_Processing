function stereo_process_new, directory


    cd, directory

    spath = directory + '/processed'
    ; spawn, 'rm *s5c1A.fts'
    ; spawn, 'mkdir -p /Volumes/Seagate/Chris/2010_Images_match/A/2010' + monthstring +istring + '/processed'
    filelist = FILE_SEARCH('*.fts')
    k=0
    success_condition = 0
    CATCH, Error_status
    while (k LT n_elements(filelist)) do begin

      IF Error_status NE 0 THEN BEGIN
        PRINT, 'Error index: ', Error_status
        PRINT, 'Error message: ', !ERROR_STATE.MSG
        ; printf,1,'file ' + '2010'+monthstring +istring+' incorrectly produced rep image'
        ; Handle the error by breaking
        break
        CATCH, /CANCEL
      ENDIF

      IF ((filelist[k].EndsWith('0_s4c1a.fts') EQ 1) AND (filelist[k+1].EndsWith('0_s4c1a.fts') EQ 1) AND (filelist[k+2].EndsWith('0_s4c1a.fts') EQ 1)) OR ((filelist[k].EndsWith('0_s4c1b.fts') EQ 1) AND (filelist[k+1].EndsWith('0_s4c1b.fts') EQ 1) AND (filelist[k+2].EndsWith('b_s4c1a.fts') EQ 1)) THEN BEGIN
          printf,1,'file ' +' produced no rep images'
        ;   break
      ENDIF ELSE IF ((filelist[k].EndsWith('0_s4c1a.fts') EQ 1) AND (filelist[k+1].EndsWith('9_s4c1a.fts') EQ 1) AND (filelist[k+2].EndsWith('8_s4c1a.fts') EQ 1)) OR ((filelist[k].EndsWith('0_s4c1b.fts') EQ 1) AND (filelist[k+1].EndsWith('9_s4c1b.fts') EQ 1) AND (filelist[k+2].EndsWith('8_s4c1b.fts') EQ 1)) THEN BEGIN

        file = string(filelist[k:k+2])
        secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
        k= k+3
        success_condition = 1

      ENDIF ELSE BEGIN
        k= k+1
      ENDELSE
    endwhile

    if (success_condition EQ 1) then begin
      process_count = string(n_elements(filelist)/3)
      cd, spath
      file_list_2 = FILE_SEARCH('*.fts')
      fitsnew = readfits(file_list_2[-1])
      image_size = size(fitsnew,/dimensions)
      str = string(image_size[0])
      str1 = string(image_size[1])
      image_shape = str.Compress() + 'x' + str1.Compress()
      printf,2,'file' + ' rep image represents ' + process_count.Compress() + ' images and has size of ' + image_shape
    endif

END
