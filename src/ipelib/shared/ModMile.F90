
module modmile

  ! Needed for MILE:
  USE ModIE
  
  ! --------------------------------------------------------------------
  ! For ext/Electrodynamics
  ! --------------------------------------------------------------------
  logical :: didInitGetPotential = .false.
  type(ieModel), allocatable :: IEModel_

  integer :: iMileVerbose

  character(len=10), parameter :: dataDir = 'UA/dataIn/'
  logical :: useMile = .TRUE.
  
end module modmile
