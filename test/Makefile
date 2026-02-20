bucket = https://noaa-nws-wam-ipe-pds.s3.amazonaws.com

# Needed for hot restart only
data:
	wget $bucket/NON-OPERATIONAL_RESEARCH/SWORD_DATA/IPE_STANDALONE_FIX.tar.gz
	tar xvf IPE_STANDALONE_FIX.tar.gz
	rm -rf  IPE_STANDALONE_FIX.tar.gz

# Needed for full comparison only, not for sums
regression:
	wget $bucket/NON-OPERATIONAL_RESEARCH/SWORD_DATA/IPE_STANDALONE_REGRESSION.tar.gz
	tar xvf IPE_STANDALONE_REGRESSION.tar.gz
	rm -rf  IPE_STANDALONE_REGRESSION.tar.gz

NP=8

help:
	@echo "make -j test          - run full test on $(NP) processors"
	@echo "make -j test NP=4     - run test on 4 processors"
	@echo "make -j test_compile  - (re)compile ipe.x"
	@echo "make test_rundir      - create run directory 'run/'"
	@echo "make test_run NP=3    - cd run; mpiexec -n 3 ipe.x"
	@echo "make test_check       - check test results against sums"
	@echo "make test_check_all   - check test results for all cells"
	@echo "make check_restartfile - verify restart file integrity"
	@echo "make clean            - remove files created by test"

test:
	@echo test_compile > test.diff
	$(MAKE) test_compile
	@echo test_rundir >> test.diff
	$(MAKE) test_rundir
	@echo test_run >> test.diff
	$(MAKE) test_run
	@echo test_check >> test.diff
	$(MAKE) test_check

test_compile:
	cd ..; make -j; make install

RESTARTFILE = IPE_State.apex.201303160000.nc
md5ref = 951f6543479fe3aecb8c49ea2d318190

check_restartfile:
	@cd run && \
	if [ ! -f $(RESTARTFILE) ]; then echo "Error: $(RESTARTFILE) not found"; exit 1; fi; \
	if command -v md5sum >/dev/null 2>&1; then \
	  md5code=`md5sum $(RESTARTFILE) | cut -d ' ' -f 1`; \
	elif command -v md5 >/dev/null 2>&1; then \
	  md5code=`md5 -q $(RESTARTFILE)`; \
	else \
	  echo "Error: Neither md5sum nor md5 found"; exit 1; \
	fi; \
	if [ "$$md5code" = "$(md5ref)" ]; then \
	  echo "$(RESTARTFILE) is the right file for restart."; \
	else \
	  echo "Warning: $(RESTARTFILE) MD5 mismatch! This is not the correct file for restart!"; exit 1; \
	fi

test_rundir:
	rm -rf run
	mkdir -p run
	cd run && ln -s ../../install/bin/ipe.x . && \
	if [ -d ../data ]; then \
	  cp -f ../data/IPE.inp .; \
	  ln -s ../data/ionprof .; \
	  ln -s ../data/tiros_spectra .; \
	  ln -s ../data/IPE_Grid.nc .; \
	  ln -s ../data/IPE_State.apex.201303160000.nc .; \
	  ln -s ../data/IPE_State.apex.201303160005_ref.nc .; \
	  ln -s ../data/global_idea_coeff_W05* .; \
	fi

# Needed for hot restart only
#	cd run; ln -s ../data/* .

TESTFILE = IPE_State.apex.201303160005.nc
REFFILE  = IPE_State.apex.201303160005_ref.nc

test_run:
	rm -f run/$(TESTFILE)
	cd run;	mpiexec -n $(NP) ./ipe.x > runlog

test_check:
	$(MAKE) check_restartfile
	scripts/compare_sums.py run/$(TESTFILE) reference.txt \
	> test.diff
	@cat test.diff

test_check_all: check_restartfile
	scripts/compare.py run/$(TESTFILE) run/$(REFFILE) \
	> test_all.diff
	@cat test_all.diff

clean:
	rm -rf run test.diff
