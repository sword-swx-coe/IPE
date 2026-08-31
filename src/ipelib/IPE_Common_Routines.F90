MODULE IPE_Common_Routines

USE IPE_Precision

IMPLICIT NONE

CONTAINS

  LOGICAL FUNCTION Almost_Equal( a, b )
    IMPLICIT NONE
    REAL(prec) :: a, b


      IF( a == 0.0_prec .OR. b == 0.0_prec )THEN

        IF( ABS(a-b) <= EPSILON(1.0_prec) )THEN

          Almost_Equal = .TRUE.

        ELSE

          Almost_Equal = .FALSE.

        ENDIF

      ELSE

        IF( (ABS(a-b) <= EPSILON(1.0_prec)*ABS(a)) .OR. (ABS(a-b) <= EPSILON(1.0_prec)*ABS(b)) )THEN

          Almost_Equal = .TRUE.

        ELSE

          Almost_Equal = .FALSE.

        ENDIF

      ENDIF

  END FUNCTION Almost_Equal

  INTEGER FUNCTION NewUnit(thisunit)
    IMPLICIT NONE
    INTEGER, INTENT(out), optional :: thisunit
    ! Local
    INTEGER, PARAMETER :: unitMin=100, unitMax=1000
    LOGICAL :: isopened
    INTEGER :: iUnit

      newunit=-1

      DO iUnit=unitMin, unitMax

         INQUIRE(UNIT=iUnit,opened=isopened)

         if( .not. isopened )then
            NewUnit = iUnit
            EXIT
         ENDif

      ENDDO

      IF( PRESENT(thisunit) ) thisunit = NewUnit

  END FUNCTION NewUnit

  SUBROUTINE Hat_Weights( x_grid, x_interp, weights, indices, N )
    INTEGER, INTENT(in)     :: N
    REAL(prec), INTENT(in)  :: x_grid(0:N)
    REAL(prec), INTENT(in)  :: x_interp
    REAL(prec), INTENT(out) :: weights(1:2)
    INTEGER, INTENT(out)    :: indices(1:2)
    ! Local
    INTEGER :: i, j


      weights = 0.0_prec
      indices = 0
      j = 0


      ! ---- Check Endpoints ---- !
      IF( x_interp < x_grid(0) .AND. x_interp < x_grid(1) )THEN

        j = j+1
        weights(j) = 1.0_prec
        indices(j) = 0

        j = j+1
        weights(j) = 0.0_prec
        indices(j) = 1
        RETURN

      ENDIF

      IF( x_interp >= x_grid(N) )THEN
        j = j+1
        weights(j) = 1.0_prec
        indices(j) = N

        j = j+1
        weights(j) = 0.0_prec
        indices(j) = N-1

        RETURN

      ENDIF
      ! ------------------------------------- !

      IF( x_interp >= x_grid(0) .AND. x_interp < x_grid(1) )THEN

        j = j + 1
        weights(j) = ( x_interp - x_grid(1) )/( x_grid(0) - x_grid(1) )
        indices(j) = 0

      ENDIF


      DO i = 1, N-1

        IF( x_interp >= x_grid(i-1) .AND. x_interp < x_grid(i) )THEN

          j = j+1
          weights(j) = ( x_interp - x_grid(i-1) )/( x_grid(i) - x_grid(i-1) )
          indices(j) = i

        ELSEIF( x_interp >= x_grid(i) .AND. x_interp < x_grid(i+1) )THEN

          j = j+1
          weights(j) = ( x_interp - x_grid(i+1) )/( x_grid(i) - x_grid(i+1) )
          indices(j) = i

        ENDIF

        IF( j == 2 )THEN
          RETURN
        ENDIF

      ENDDO

      IF( x_interp >= x_grid(N-1) .AND. x_interp < x_grid(N) )THEN

        j = j+1
        weights(j) = ( x_interp - x_grid(N-1) )/( x_grid(N) - x_grid(N-1) )
        indices(j) = N

      ENDIF

  END SUBROUTINE Hat_Weights

  SUBROUTINE Map_RIM_Aurora_To_Flux_Tube( aver, diff, lat, iLon, &
       latNorth, latSouth, efluxNorth, efluxSouth, chNorth, chSouth )
    REAL(prec), INTENT(in)  :: aver(:,:), diff(:,:), lat(:)
    INTEGER, INTENT(in)     :: iLon
    REAL(prec), INTENT(in)  :: latNorth, latSouth
    REAL(prec), INTENT(out) :: efluxNorth, efluxSouth
    REAL(prec), INTENT(out) :: chNorth, chSouth
    INTEGER :: j

    ! A flux tube has distinct northern and southern magnetic footpoints;
    ! interpolate the same RIM longitude independently at each latitude.
    CALL Interpolate_RIM_Aurora(aver, diff, lat, iLon, latNorth, &
         efluxNorth, chNorth)
    CALL Interpolate_RIM_Aurora(aver, diff, lat, iLon, latSouth, &
         efluxSouth, chSouth)

  CONTAINS

    SUBROUTINE Interpolate_RIM_Aurora(averIn, diffIn, latIn, iLonIn, &
         targetLat, efluxOut, chOut)
      REAL(prec), INTENT(in)  :: averIn(:,:), diffIn(:,:), latIn(:)
      INTEGER, INTENT(in)     :: iLonIn
      REAL(prec), INTENT(in)  :: targetLat
      REAL(prec), INTENT(out) :: efluxOut, chOut
      INTEGER :: j1, j2, nLat
      REAL(prec) :: latValue, weight

      nLat = SIZE(latIn)
      j1 = 1
      j2 = 1
      IF (targetLat <= latIn(1)) THEN
         j1 = 1
         j2 = 1
         weight = 0.0_prec
      ELSEIF (targetLat >= latIn(nLat)) THEN
         j1 = nLat
         j2 = nLat
         weight = 0.0_prec
      ELSE
         DO j = 1, nLat - 1
            IF (targetLat <= latIn(j+1)) THEN
               j1 = j
               j2 = j + 1
               EXIT
            END IF
         END DO
         weight = (targetLat - latIn(j1))/(latIn(j2) - latIn(j1))
      END IF

      latValue = (1.0_prec - weight)*averIn(iLonIn,j1) + &
           weight*averIn(iLonIn,j2)
      ! RIM energy flux is W/m2; IPE uses mW/m2.  IPE's characteristic
      ! energy is one half of RIM's average energy (both energies are keV).
      efluxOut = 1000.0_prec*MAX( &
           (1.0_prec - weight)*diffIn(iLonIn,j1) + &
           weight*diffIn(iLonIn,j2), 0.0_prec)
      chOut = 0.5_prec*latValue
    END SUBROUTINE Interpolate_RIM_Aurora

  END SUBROUTINE Map_RIM_Aurora_To_Flux_Tube

END MODULE IPE_Common_Routines
