function stereo_process, directory

  ;month string
  FOR j =2, 2 DO BEGIN
    monthstring = '0'+ string(j)
    monthstring = monthstring.Compress()
  ;day string
  FOR i = 1, 9 DO BEGIN
    istring = STRTRIM(i,2)
    istring2 = '2007/' + monthstring + '/' + istring + 'T09:35:00-2007/' + monthstring + '/' + istring + 'T17:45:25'
    istring3 = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring
    try1 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:00-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',info=0,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)
    try2 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:09-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=120,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)
    try3 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:18-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=240,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)

    IF (ISA(try1,/array) EQ 1) THEN BEGIN ; check that vso_search returns array indicating images were found
    con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 1056x1088')
    con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 1056x1088')
    con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 1056x1088')

    IF (ISA(con1,/array) EQ 1) THEN BEGIN ; check that the condition returns array indicating images were found
    spawn, 'mkdir -p /Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring

    a = vso_get(try1[con1],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring,/force)
    b = vso_get(try1[con2],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring,/force)
    c = vso_get(try1[con3],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring,/force)

    cd, '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring
    setenv, "SECCHI_BKG=/Users/crura/stereo/secchi/backgrounds"
    ; /Users/crura/stereo/secchi/backgrounds/a/monthly_min/200612/mc1A_p120_061231.fts
    spath = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring + '/processed'
    spawn, 'rm *s5c1B.fts'
    spawn, 'mkdir -p /Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring + '/processed'
    filelist = FILE_SEARCH('*.fts')
    k=0
    while (k LT n_elements(filelist)) do begin
      print, filelist[k:k+2]
      file = string(filelist[k:k+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      k= k+3
    endwhile

    spath = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring + '0'+istring + '/processed'
    year_month_day_print = '2007_' + monthstring + '_0' + istring
    save,spath,year_month_day_print,filename='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav'
    spawn, 'cp /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters_safe.sav'
    ;while (i eq 2) do begin
      ;spawn, 'cp /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters_safe.sav'
      ;i= i+1
    ;endwhile
    spawn, 'python /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/produce_representative_image.py'

    ENDIF ELSE BEGIN
    IF (ISA(con1,/array) NE 1) THEN PRINT, 'vso_search returned no results, moving to next iteration'
    ENDELSE

    ENDIF ELSE BEGIN
    IF (ISA(try1,/array) NE 1) THEN PRINT, 'vso_search returned no results, moving to next iteration'
    ENDELSE
  ENDFOR



  day string
  FOR i = 27, 31 DO BEGIN
    istring = STRTRIM(i,2)
    istring2 = '2007/' + monthstring + '/' + istring + 'T09:35:00-2007/' + monthstring + '/' + istring + 'T17:45:25'
    istring3 = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring
    try1 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:00-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',info=0,out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring)
    try2 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:09-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=120,out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring)
    try3 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:18-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=240,out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring)

    IF (ISA(try1,/array) EQ 1) THEN BEGIN ; check that vso_search returns array indicating images were found
    con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 1056x1088')
    con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 1056x1088')
    con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 1056x1088')

    IF (ISA(con1,/array) EQ 1) THEN BEGIN ; check that the condition returns array indicating images were found
    spawn, 'mkdir -p /Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring

    a = vso_get(try1[con1],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring,/force)
    b = vso_get(try1[con2],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring,/force)
    c = vso_get(try1[con3],out_dir='/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring,/force)

    cd, '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring
    setenv, "SECCHI_BKG=/Users/crura/stereo/secchi/backgrounds"
    ; /Users/crura/stereo/secchi/backgrounds/a/monthly_min/200612/mc1A_p120_061231.fts
    spath = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring + '/processed'
    spawn, 'rm *s5c1B.fts'
    spawn, 'mkdir -p /Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring + '/processed'
    filelist = FILE_SEARCH('*.fts')
    k=0
    while (k LT n_elements(filelist)) do begin
      print, filelist[k:k+2]
      file = string(filelist[k:k+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      k= k+3
    endwhile

    spath = '/Users/crura/Desktop/Research/2007_Images/B/2007' + monthstring +istring + '/processed'
    year_month_day_print = '2007_' + monthstring + '_' + istring
    save,spath,year_month_day_print,filename='/Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav'
    spawn, 'cp /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters_safe.sav'
    ;while (i eq 2) do begin
      ;spawn, 'cp /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters.sav /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/parameters_safe.sav'
      ;i= i+1
    ;endwhile
    spawn, 'python /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/produce_representative_image.py'

    ENDIF ELSE BEGIN
    IF (ISA(con1,/array) NE 1) THEN PRINT, 'vso_search returned no results, moving to next iteration'
    ENDELSE

    ENDIF ELSE BEGIN
    IF (ISA(try1,/array) NE 1) THEN PRINT, 'vso_search returned no results, moving to next iteration'
    ENDELSE
  ENDFOR

  ENDFOR




END
