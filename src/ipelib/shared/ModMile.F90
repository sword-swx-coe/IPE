
module modmile

#ifdef HAVE_MILE

  ! Needed for MILE:
  USE ModIE

  type(ieModel), allocatable :: IEModel_
  
#endif
  
  logical :: didInitGetPotential = .false.
  integer :: iMileVerbose = 0

#ifdef HAVE_MILE
  character(len=10), parameter :: dataDir = 'UA/dataIn/'
  logical :: useMile = .TRUE.
#else
  character(len=2), parameter :: dataDir = './'
  logical :: useMile = .FALSE.
#endif
  
end module modmile
