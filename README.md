# Ionosphere Plasmasphere Electrodynamics Model

Documentation can be found at

[https://swqu-gsmwam-ipe.readthedocs.io]

For further details on the IPE model see Maruyama et al. 2016, GRL, 48, 2429

[https://doi.org/10.1002/2015GL067312](https://doi.org/10.1002/2015GL067312)


## Configuring the code

There are no two methods of configuring IPE to work.  The first uses the configure script, which builds the Makefile structure within the main directory and the subdirectories.  The other is to use the UM provided Config.py script.

### Dependencies

No matter which way the code is configured, IPE is dependent on the following:
- ESMF
- COMIO
- Parallel NetCDF (COMIO is actually dependent on this)
- HDF5 (COMIO is actually dependent on this)

Once COMIO and ESMF have been downloaded, made, and installed, you can move forward with configuring IPE. You will need to know where each of these things are installed.

### Configuring with the NOAA system

There are several INSTALL "manuals", which attempt to describe how to install IPE on different systems.

### Configuring with the UM system

To use the UM Makefile structure, you should be able run Config.py. This will:
- Link an appropriate Makefile in the main IPE directory
- Add an absolute path to the Makefile system, so the makefiles know where to locate the subdirectories
- Download the Electrodynamics library.

There a four fundamental Makefiles:
1. build/Makefile.dirs - this is the file that points the makefile system to all of the appropriate places WITHIN IPE.
2. build/Makefile.conf - this is the file that describes HOW to actually compile things.  So, it has all of the include paths and library paths.  This is the hardest file to make, since it has definitions for the compiler, linker, include files, library files, etc. All of the dependencies for IPE need to be met in this makefile.
3. Makefile - this makefile drives the compilation.  It will send the processes into each subdirectory and make each library in the respective subdirectory.
4. In each subdirectory, there is a Makefile.UM, which this system uses as the makefile. Each Makefile.UM has list of objects to compile and a definition for the library that it will create.

