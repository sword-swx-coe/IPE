
PROGRAM IPE_Driver

  USE IPE_Precision
  USE IPE_Model_Class

  IMPLICIT NONE

  TYPE( IPE_Model ) :: ipe
  LOGICAL           :: init_success, fileExists
  REAL(prec)        :: t0_ipe, t1_ipe
  REAL(prec)        :: t2, t1, cpuTime0, ipeTotalSimulationTime, ipeTotalElapsedTime
  real(prec) :: ipeTimeLeft, ipeTotalWallTime, ipeEstimatedWall, ipePercentComplete
  INTEGER           :: i, rc, stat
  CHARACTER(200)    :: init_file
  character(6) :: unit
  
  CALL ipe % Build( rc=rc )
  IF ( ipe_error_check( rc, msg="IPE model initialization unsuccessful", &
       line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

  init_file = &
       trim(ipe % parameters % file_prefix) // &
       ipe % time_tracker % DateStamp( ) // &
       ipe % parameters % file_extension

  ! Only check for file existence if we need to read it:
  IF (ipe % parameters % read_apex_neutrals) THEN
     
     INQUIRE( FILE = TRIM(init_file), EXIST = fileExists, iostat=stat )
     IF ( ipe_iostatus_check( rc, &
          msg="Error inquiring about IPE initial state file "//init_file, &
          line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

     IF ( ipe_status_check( fileExists, &
          msg="IPE initial state file not found: "//init_file, &
          line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()
  endif

  CALL ipe % Initialize( init_file, rc=rc )
  IF ( ipe_iostatus_check( rc, msg="Error initializing IPE", &
       line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

  CALL ipe % time_tracker % Update( ipe % parameters % start_time )

  ipeTotalSimulationTime = ipe % parameters % end_time - ipe % parameters % start_time
  CALL CPU_TIME(cpuTime0)
  
  DO i = 1, ipe % parameters % n_model_updates

     IF (ipe % mpi_layer % rank_id == 0) &
          write(*,*) 'Starting time loop at time : ', ipe % time_tracker % DateStamp( )

     CALL CPU_TIME(t1)
     t0_ipe = ipe % parameters % start_time + &
          REAL(i-1,prec)*ipe % parameters % file_output_frequency
      t1_ipe = ipe % parameters % start_time + &
           REAL(i,prec)*ipe % parameters % file_output_frequency

      CALL ipe % Update( t0_ipe, t1_ipe, rc=rc )
      IF ( ipe_iostatus_check( rc, msg="Error updating IPE model", &
        line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

      CALL CPU_TIME(t2)
      ipeTotalWallTime = t2 - cpuTime0

      CALL ipe % WriteStates( rc=rc )
      IF ( ipe_iostatus_check( rc, msg="Error writing IPE output file", &
        line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

      CALL ipe % Write2d( rc=rc )
      IF ( ipe_iostatus_check( rc, msg="Error writing IPE output file", &
        line=__LINE__, file=__FILE__ ) ) CALL ipe % Trash()

      IF( ipe % mpi_layer % rank_id == 0 )THEN
         ipeTotalElapsedTime = ipe % time_tracker % elapsed_sec
         ipePercentComplete = ipeTotalElapsedTime / ipeTotalSimulationTime
         ipeEstimatedWall = ipeTotalWallTime / ipePercentComplete
         ipeTimeLeft = ipeEstimatedWall - ipeTotalWallTime
         write(6,*) '***********************************************'
         write(6,'(a,f9.2,a)') '*   Update Time for this period : ', t2-t1, ' (sec)'
         call get_unit(ipeTotalWallTime, unit)
         write(6,'(a,f9.2,a)') '*   Wall Time Complete: ', ipeTotalWallTime, unit
         call get_unit(ipeTimeLeft, unit)
         write(6,'(a,f9.2,a)') '*   Projected completion: ', ipeTimeLeft, unit
         write(6,*) '***********************************************'
      ENDIF

    ENDDO

    CALL ipe % Trash( )

END PROGRAM IPE_Driver

