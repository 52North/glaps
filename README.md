# ARCHIVED

This project is no longer maintained and will not receive any further updates. If you plan to continue using it, please be aware that future security issues will not be addressed.


PYTHON-INTERPRETER
==================

* This README file gives information about the eclipse setup, configuration
* and used plugins during development of the project.

To enjoy content-assist you have to add more libraries directly to your Python
interpreter (the paths may vary depending to your system):

  1) /var/lib/python-support/python2.5/gtk-2.0
  2) /usr/lib/python2.5/site-packages/sugar

PLUGINS
=======

  1) Pydev
   http://pydev.org/
  2) eclox
   http://home.gna.org/eclox/#update-site

 CONFIGURATION
 =============
 General configuration points

  1) See `cfg/GeospatialLearning'.doxyfile for documentation generation

 LIBRARIES
 =========
 Sugar has no dependency mechanism yet. So we have to ship 3rd party libraries
 with this project:

  1) shapely
  2) geojson
  3) groupthink
  4) owslib
 
 OTHER
 =====
 The software depends on the gpsd package which grabs GPS data from a connected
 GPS device. Install gpsd by means of your package manager of download it from
 
   http://gpsd.berlios.de/
   
 NOTE: Some distributions provide dependencies to Python GPS bindings and some
   do not. Please check within your distribution if the package python-gps will
   be installed automatically as dependency to the gpsd package.
   
