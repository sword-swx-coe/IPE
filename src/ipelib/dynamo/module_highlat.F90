module module_highlat
  !
  PRIVATE
  PUBLIC :: highlat
      
contains 
  !-----------------------------------------------------------------------
  subroutine highlat(offset1_deg_r8, offset2_deg_r8, potential_model, rc)
          
    use ipe_error_module
    use params_module,ONLY: kmlonp1,kmlat,kmlon
    use dynamo_module,ONLY: kmlat0,phihm
    use module_sub_heelis,ONLY: heelis
    use module_colath,ONLY:colath
    use module_magfield
    use module_weimer2005Ipe,ONLY:setmodel2005Ipe,epotval2005Ipe
    use cons_module,ONLY:xlatm_deg,xlonm_deg,pi,dtr,xlatm
    use module_init_heelis
    use heelis_module,ONLY:ctpoten

    use ModMile

    implicit none
    real*8,intent(in) :: offset1_deg_r8,offset2_deg_r8
    integer,intent(in) :: potential_model
    real :: offset1_deg,offset2_deg
    integer,optional,intent(out) :: rc

    integer :: i,j,lrc
    real*8,parameter::fill=1.0E36 !fill in value outside the boundary
    real*8 ::mlat,mlt,epot

    ! This is needed for MILE:
    real :: mlat2d(kmlon, kmlat), mlt2d(kmlon, kmlat), pot2d(kmlon, kmlat)

    offset1_deg = real(offset1_deg_r8)
    offset2_deg = real(offset2_deg_r8)
    !   
    ! am 10/04 remove weimer part: first test without any potential model
    ! Dynamo calls Heelis (heelis.F), Weimer (wei01gcm.F), or neither
    !   for high latitude electric potential, according to user-provided
    !   "model_potential".
    ! Get high latitude (Heelis or other)
    !   colatitudes, NH pfrac, and poten phihm.
    !  If Weimer is used, then theta0,phid etc is changed before use in aurora
    !   in dynamics.
    !
    if (present(rc)) rc = IPE_SUCCESS
    
    if ( potential_model == 1 ) then ! 1 is HEELIS
       call init_heelis
       call heelis(offset1_deg,offset2_deg)

    else if ( potential_model == 2 ) then ! 2 is WEIMER2005

       call setmodel2005Ipe( &
            sangle, &
            bt, &
            stilt, &
            swvel, &
            swden, &
            dataDir, &
            'epot', &
            rc=lrc)
       if (ipe_error_check( &
            lrc, msg="call to setmodel2005Ipe failed", rc = rc)) return
       !        mlatLoop: do j=1,kmlat0 !kmlat0=(kmlat+1)/2, from -90 to 0 SH
       mlatLoop:do j=1,kmlat

          mlat=xlatm_deg(j)      !mlat[deg]
          if ( abs(xlatm(j)) <= pi/6. ) then

             phihm(1:kmlon,j) = 0.
             CYCLE             !go to the next J

          else  !if ( abs(mlat) > pi/6. ) then

             mlonLoop: do i=1,kmlon
                !mltrad = mlonRad - sunlons + pi !mlt(rad)
                !here sunlons must be time dependent!
                mlt = (xlonm_deg(i)*dtr -sunlons + pi)*12./pi !mlt(hr)
                if (mlt>=24.) mlt=mod(mlt,24.0d0)
                if (mlt<0.) mlt=mlt+24.

                !     note:mlat<0 is outside of the boundary(fill in value)!
                call epotval2005Ipe(abs(mlat),mlt,fill,epot)

                if ( epot == fill ) then
                   phihm(i,j) = 0.
                else
                   phihm(i,j) = epot*1.0E+3 !epot[kV]-->[Volt]
                end if
             end do mlonLoop   !i=1,kmlon

             !periodic points:
             phihm(kmlonp1,j) = phihm(1,j)

          end if               !abs(mlat)
       end do mlatLoop      !j=1,kmlat


       ctpoten=(maxval(phihm)-minval(phihm))/1.0E+3
       call init_heelis
       call colath(offset1_deg,offset2_deg)

#ifdef HAVE_MILE

    else if ( potential_model == 10 ) then ! 10 is MILE:

       if (iMileVerbose > 0) then
          write(*,*) "-> MILE: getting potential in module_highlat"
       endif
       ! We really don't know how many different times the IE library is 
       ! going to be needed in each time-step, so set the grid again:
       call IEModel_%nMlts(kmlon)
       call IEModel_%nLats(kmlat)
       do j=1,kmlat
          do i=1,kmlon
             mlat2d(i, j) = xlatm_deg(j)
             mlt2d(i, j) = &
                  mod( (xlonm_deg(i)*dtr -sunlons + pi)*12./pi + 24, 24.0)
          enddo
       enddo
       call iemodel_%grid(mlt2d, mlat2d)
       call iemodel_%get_potential(pot2d)
       phihm(1:kmlon,:) = pot2d
       phihm(kmlonp1,:) = phihm(1,:)
       if (iMileVerbose > 0) then
          write(*,*) ' --> CPCP (kV) : ', &
               (maxval(phihm) - minval(phihm))/1000.0
       endif
         
#endif
         
    else  !  0 - potential_model='NONE'
       do j=1,kmlat0
          do i=1,kmlonp1
             phihm(i,j) = 0.
          enddo ! i=1,kmlonp1
       enddo ! j=1,kmlat0
       call colath(offset1_deg,offset2_deg)
    endif
      
  end subroutine highlat
  !-----------------------------------------------------------------------
end module module_highlat
