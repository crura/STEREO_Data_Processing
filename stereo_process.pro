function stereo_process, directory
  FOR j = 7, 7 DO BEGIN
    istring = STRTRIM(j,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    ;b = vso_get(try1[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    ;c = vso_get(try1[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/2010050'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/2010050'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile





    ;istring = STRTRIM(i,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)
    ;b = vso_get(try1[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)
    ;c = vso_get(try1[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)

    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/2010060'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/2010060'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile
    ;CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'


    ;istring = STRTRIM(i,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)
    ;b = vso_get(try2[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)
    ;c = vso_get(try3[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)

    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/2010070'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/2010070'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile
    ;CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'
  ENDFOR


  FOR j = 28, 31 DO BEGIN
    istring = STRTRIM(j,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    ;b = vso_get(try1[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    ;c = vso_get(try1[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201005'+istring,/force)
    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/201005'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/201005'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile
    ;CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'





    ;istring = STRTRIM(i,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)
    ;b = vso_get(try1[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)
    ;c = vso_get(try1[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201006'+istring,/force)

    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/201006'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/201006'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile
    ;CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'


    ;istring = STRTRIM(i,2)

    ;a = vso_get(try1[con1],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)
    ;b = vso_get(try2[con2],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)
    ;c = vso_get(try3[con3],out_dir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B/201007'+istring,/force)

    outdir='/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/201007'+istring
    CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'

    ;CD, directory
    setenv, "SECCHI_BKG=/Users/Chris/Desktop/Goddard Research/FITS Images New/downloaded fits/Background images/Monthly min"
    spath = '/Volumes/Seagate Backup Plus Drive/Chris/Secchi_data/B_10_min/processed/201007'+istring
    filelist = FILE_SEARCH('*.fts')
    i=0
    while (i LT n_elements(filelist)) do begin
      print, filelist[i:i+2]
      file = string(filelist[i:i+2])
      secchi_prep, file, headd, imd, /CALIMG_OFF, /NOCALFAC,/rotate_on,  /write_fts, savepath = spath,/polariz_on, /pB
      i= i+3
    endwhile
    ;CD, outdir
    ;spawn, 'rm *018_s4c1B.fts'
    ;spawn, 'rm *s5c1A.fts'
  ENDFOR



END