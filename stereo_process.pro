function stereo_process, directory

;   compile_opt idl2
;   spawn, 'git rev-parse --show-toplevel', git_repo
;   data = read_csv(git_repo + '/month_day_pair.csv')
;   ;len = fix(sqrt(n_elements(forward_pb_image)))
;   ;dens_2d = reform(dens.field1,len,len)

  ; spawn, 'mkdir -p /Volumes/Seagate/Chris/2010_Images_match'  
  ; fname = '/Volumes/Seagate/Chris/2010_Images_match/process_error_log_2010.log'
  ; fname2 = '/Volumes/Seagate/Chris/2010_Images_match/process_log_2010.log'
  ; OPENW,1,fname
  ; OPENW,2,fname2

;   list1 = data.field1
;   list2 = data.field2


;   foreach element, list1 do begin
;     daylist = []
;     j = fix(element) ;month

;    foreach element2, list2[element-list1[0]] do begin

;     arr = linspace(1,element2,element2)
;     foreach element3, arr do begin ;daylist = [daylist, fix(element3)]
;     i = fix(element3) ;day
;     ;print, 'month: ', j, 'day: ', i

;     IF (j LT 10) THEN BEGIN
;     monthstring = '0'+ string(j)
;     monthstring = monthstring.Compress()
;     ENDIF ELSE BEGIN
;     monthstring = string(j)
;     monthstring = monthstring.Compress()
;     ENDELSE

;     IF (i LT 10) THEN BEGIN
;     istring = '0'+ string(i)
;     istring_tmw = '0'+ string(i+1)
;     istring_ytd = '0'+ string(i-1)
;     istring = istring.Compress()
;     istring_tmw = istring_tmw.Compress()
;     istring_ytd = istring_ytd.Compress()
;     ENDIF ELSE BEGIN
;     istring = string(i)
;     istring_tmw = string(i+1)
;     istring_ytd = string(i-1)
;     istring = istring.Compress()
;     istring_tmw = istring_tmw.Compress()
;     istring_ytd = istring_ytd.Compress()
;     ENDELSE

;     outstring = SCC_DATA_PATH('a',TYPE='seq',TEL='cor1',date='2010'+ monthstring +istring)
;     try1 = vso_search(date='2010/' + monthstring + '/' + istring + 'T16:35:00-2010/' + monthstring + '/' + istring_tmw + 'T00:45:25', inst='COR1',source='STEREO-A',info=0,out_dir=outstring)
;     try2 = vso_search(date='2010/' + monthstring + '/' + istring + 'T16:35:09-2010/' + monthstring + '/' + istring_tmw + 'T00:45:25', inst='COR1',source='STEREO-A',sample=600,info=120,out_dir=outstring)
;     try3 = vso_search(date='2010/' + monthstring + '/' + istring + 'T16:35:18-2010/' + monthstring + '/' + istring_tmw + 'T00:45:25', inst='COR1',source='STEREO-A',sample=600,info=240,out_dir=outstring)

;     IF (ISA(try1,/array) EQ 1) THEN BEGIN ; check that vso_search returns array indicating images were found
;     con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 512x512')
;     con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 512x512')
;     con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 512x512')

;     IF (ISA(con1,/array) NE 1) THEN BEGIN ; check that vso_search returns array indicating images were found
;     con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 1024x1024')
;     con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 1024x1024')
;     con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 1024x1024')
;     ENDIF

;     IF (ISA(con1,/array) EQ 1) THEN BEGIN ; check that the condition returns array indicating images were found
;     spawn, 'mkdir -p /Volumes/Seagate/Chris/2010_Images_match/A/2010' + monthstring +istring
;     spawn, 'mkdir -p ' + outstring

;     a = vso_get(try1[con1],out_dir=outstring,/force)
;     b = vso_get(try1[con2],out_dir=outstring,/force)
;     c = vso_get(try1[con3],out_dir=outstring,/force)

    cd, directory

    spath = directory + '/processed'
    ; spawn, 'rm *s5c1A.fts'
    ; spawn, 'mkdir -p /Volumes/Seagate/Chris/2010_Images_match/A/2010' + monthstring +istring + '/processed'
    spawn, 'mkdir -p ' + spath
    filelist = FILE_SEARCH('*.fts')
    nfiles = N_ELEMENTS(filelist)

    IF nfiles LT 3 THEN BEGIN
      PRINT, 'Not enough files for a polarization sequence.'

    ENDIF


    ;------------------------------------------------------
    ; Read metadata from FITS headers
    ;------------------------------------------------------

    date_obs = STRARR(nfiles)
    polar    = DBLARR(nfiles)
    obs_id   = LONARR(nfiles)

    FOR i = 0L, nfiles-1 DO BEGIN

        hdr = HEADFITS(filelist[i], /SILENT)

        date_obs[i] = FXPAR(hdr, 'DATE-OBS')
        polar[i]    = FXPAR(hdr, 'POLAR')
        obs_id[i]   = FXPAR(hdr, 'OBS_ID')

    ENDFOR


    ;------------------------------------------------------
    ; Sort files chronologically using DATE-OBS
    ;------------------------------------------------------

    tai = ANYTIM2TAI(date_obs)

    order = SORT(tai)

    filelist = filelist[order]
    date_obs = date_obs[order]
    polar    = polar[order]
    obs_id   = obs_id[order]
    tai      = tai[order]


    ;------------------------------------------------------
    ; Look for valid 0,120,240 polarization sequences
    ;------------------------------------------------------

    k = 0L
    success_condition = 0

    WHILE k LE nfiles-3 DO BEGIN

        pols = polar[k:k+2]

        sorted_pols = pols[SORT(pols)]

        p0 = sorted_pols[0]
        p1 = sorted_pols[1]
        p2 = sorted_pols[2]

        ; Time relative to first image
        dt1 = tai[k+1] - tai[k]
        dt2 = tai[k+2] - tai[k]

        ; Standard COR1 sequence
        valid_angles = $
            (ABS(p0 -   0.0D) LT 0.1D) AND $
            (ABS(p1 - 120.0D) LT 0.1D) AND $
            (ABS(p2 - 240.0D) LT 0.1D)

        ; Same timing criteria used by COR1_PBSERIES
        valid_time = $
            (dt1 LE 60.0D) AND $
            (dt2 LT 120.0D)


        IF valid_angles AND valid_time THEN BEGIN

            file = filelist[k:k+2]

            PRINT, 'Found polarization sequence:'
            PRINT, file
            PRINT, 'POLAR = ', polar[k:k+2]
            PRINT, 'OBS_ID = ', obs_id[k:k+2]

            secchi_prep, file, headd, imd, $
                /CALIMG_OFF, $
                /NOCALFAC, $
                /ROTATE_ON, $
                /WRITE_FTS, $
                SAVEPATH=spath, $
                /POLARIZ_ON, $
                /pB

            k = k + 3
            success_condition = 1

        ENDIF ELSE BEGIN

            k = k + 1

        ENDELSE

    ENDWHILE



    ; try1 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:00-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',info=0,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)
    ; try2 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:09-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=120,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)
    ; try3 = vso_search(date='2007/' + monthstring + '/' + istring + 'T09:35:18-2007/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-B',sample=600,info=240,out_dir='/Users/crura/Desktop/Research/2007_Images/B/20070' + monthstring + '0'+istring)

    ; if (success_condition EQ 1) then begin
    ;   process_count = string(n_elements(filelist)/3)
    ;   cd, spath
    ;   file_list_2 = FILE_SEARCH('*.fts')
    ;   fitsnew = readfits(file_list_2[-1])
    ;   image_size = size(fitsnew,/dimensions)
    ;   str = string(image_size[0])
    ;   str1 = string(image_size[1])
    ;   image_shape = str.Compress() + 'x' + str1.Compress()
    ;   printf,2,'file ' + directory + ' rep image represents ' + process_count.Compress() + ' images and has size of ' + image_shape
    ;   success_condition = 0
    ;   k= k+1
    ; endif

;     spath = '/Volumes/Seagate/Chris/2010_Images_match/A/2010' + monthstring +istring + '/processed'
;     year_month_day_print = '2010_' + monthstring + '_' + istring
;     save,spath,year_month_day_print,filename='/Volumes/Seagate/Chris/2010_Images_match/parameters.sav'
;     spawn, 'cp /Volumes/Seagate/Chris/2010_Images_match/parameters.sav /Volumes/Seagate/Chris/2010_Images_match/parameters_safe.sav'

;     spawn, 'python /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/produce_representative_image.py'

;     ENDIF ELSE BEGIN
;     IF (ISA(con1,/array) NE 1) THEN begin
;       printf,1,'file ' + '2010'+monthstring +istring+' produced no rep images'
;       PRINT, 'vso_search returned no results, moving to next iteration'
;     endif
;     ENDELSE

;     ENDIF ELSE BEGIN
;     IF (ISA(try1,/array) NE 1) THEN begin
;       printf,1,'file ' + '2010'+monthstring +istring+' produced no rep images'
;       PRINT, 'vso_search returned no results, moving to next iteration'
;     endif
;     ENDELSE
;   endforeach

;  endforeach

; endforeach

;   ;
;   ; FOR j =1, 12 DO BEGIN
;   ;   IF (j LT 10) THEN BEGIN
;   ;   monthstring = '0'+ string(j)
;   ;   monthstring = monthstring.Compress()
;   ;   ENDIF ELSE BEGIN
;   ;   monthstring = string(j)
;   ;   monthstring = monthstring.Compress()
;   ;   ENDELSE
;   ;
;   ; ;day string
;   ; FOR i = 1, 31 DO BEGIN
;   ;   IF (i LT 10) THEN BEGIN
;   ;   istring = '0'+ string(i)
;   ;   istring = istring.Compress()
;   ;   ENDIF ELSE BEGIN
;   ;   istring = string(i)
;   ;   istring = istring.Compress()
;   ;   ENDELSE
;   ;
;   ;   try1 = vso_search(date='2008/' + monthstring + '/' + istring + 'T09:35:00-2008/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-A',info=0,out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring)
;   ;   try2 = vso_search(date='2008/' + monthstring + '/' + istring + 'T09:35:09-2008/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-A',sample=600,info=120,out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring)
;   ;   try3 = vso_search(date='2008/' + monthstring + '/' + istring + 'T09:35:18-2008/' + monthstring + '/' + istring + 'T17:45:25', inst='COR1',source='STEREO-A',sample=600,info=240,out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring)
;   ;
;   ;   IF (ISA(try1,/array) EQ 1) THEN BEGIN ; check that vso_search returns array indicating images were found
;   ;   con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 512x512')
;   ;   con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 512x512')
;   ;   con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 512x512')
;   ;
;   ;   IF (ISA(con1,/array) NE 1) THEN BEGIN ; check that vso_search returns array indicating images were found
;   ;   con1 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 0deg. ; 1024x1024')
;   ;   con2 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 120deg. ; 1024x1024')
;   ;   con3 = WHERE(try1.info eq 'COR1 ;  ; SERIES ; 240deg. ; 1024x1024')
;   ;   ENDIF
;   ;
;   ;   IF (ISA(con1,/array) EQ 1) THEN BEGIN ; check that the condition returns array indicating images were found
;   ;   spawn, 'mkdir -p /Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring
;   ;
;   ;   a = vso_get(try1[con1],out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring,/force)
;   ;   b = vso_get(try1[con2],out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring,/force)
;   ;   c = vso_get(try1[con3],out_dir='/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring,/force)
;   ;
;   ;   cd, '/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring
;   ;   setenv, "SECCHI_BKG=/Users/crura/stereo/secchi/backgrounds"
;   ;
;   ;   spath = '/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring + '/processed'
;   ;   spawn, 'rm *s5c1A.fts'
;   ;   spawn, 'mkdir -p /Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring + '/processed'
;   ;   filelist = FILE_SEARCH('*.fts')
;   ;   k=0
;   ;   success_condition = 0
;   ;   CATCH, Error_status
;   ;   while (k LT n_elements(filelist)) do begin
;   ;
;   ;     IF Error_status NE 0 THEN BEGIN
;   ;       PRINT, 'Error index: ', Error_status
;   ;       PRINT, 'Error message: ', !ERROR_STATE.MSG
;   ;       ; Handle the error by breaking
;   ;       break
;   ;       CATCH, /CANCEL
;   ;     ENDIF
;   ;
;   ;     IF (filelist[k].EndsWith('0_s4c1A.fts') EQ 1) AND (filelist[k+1].EndsWith('9_s4c1A.fts') EQ 1) AND (filelist[k+2].EndsWith('8_s4c1A.fts') EQ 1) THEN BEGIN
;   ;
;   ;       file = string(filelist[k:k+2])
;   ;       secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
;   ;       k= k+3
;   ;       success_condition = 1
;   ;
;   ;     ENDIF ELSE IF (filelist[k].EndsWith('0_s4c1A.fts') EQ 1) AND (filelist[k+1].EndsWith('0_s4c1A.fts') EQ 1) AND (filelist[k+2].EndsWith('0_s4c1A.fts') EQ 1) THEN BEGIN
;   ;         printf,1,'file ' + '2008'+monthstring +istring+' produced no rep images'
;   ;         break
;   ;     ENDIF ELSE BEGIN
;   ;       k= k+1
;   ;     ENDELSE
;   ;   endwhile
;   ;
;   ;   if (success_condition EQ 1) then begin
;   ;     process_count = string(n_elements(filelist)/3)
;   ;     cd, spath
;   ;     file_list_2 = FILE_SEARCH('*.fts')
;   ;     fitsnew = readfits(file_list_2[-1])
;   ;     image_size = size(fitsnew,/dimensions)
;   ;     str = string(image_size[0])
;   ;     str1 = string(image_size[1])
;   ;     image_shape = str.Compress() + 'x' + str1.Compress()
;   ;     printf,2,'file 2008' + monthstring +istring + ' rep image represents ' + process_count.Compress() + ' images and has size of ' + image_shape
;   ;   endif
;   ;
;   ;   spath = '/Volumes/Seagate/Chris/2008_Images/A/2008' + monthstring +istring + '/processed'
;   ;   year_month_day_print = '2008_' + monthstring + '_' + istring
;   ;   save,spath,year_month_day_print,filename='/Volumes/Seagate/Chris/2010_Images_match/parameters.sav'
;   ;   spawn, 'cp /Volumes/Seagate/Chris/2010_Images_match/parameters.sav /Volumes/Seagate/Chris/2010_Images_match/parameters_safe.sav'
;   ;
;   ;   spawn, 'python /Users/crura/Desktop/Research/idlroutines/STEREO_Data_Processing/produce_representative_image.py'
;   ;
;   ;   ENDIF ELSE BEGIN
;   ;   IF (ISA(con1,/array) NE 1) THEN begin
;   ;     printf,1,'file ' + '2008'+monthstring +istring+' produced no rep images'
;   ;     PRINT, 'vso_search returned no results, moving to next iteration'
;   ;   endif
;   ;   ENDELSE
;   ;
;   ;   ENDIF ELSE BEGIN
;   ;   IF (ISA(try1,/array) NE 1) THEN begin
;   ;     printf,1,'file ' + '2008'+monthstring +istring+' produced no rep images'
;   ;     PRINT, 'vso_search returned no results, moving to next iteration'
;   ;   endif
;   ;   ENDELSE
;   ; ENDFOR
;   ;
;   ; ENDFOR

close,1
close,2


END
