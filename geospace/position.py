"""@brief Contains all position related functions and classes."""
#ifndef DOXYGEN_SHOULD_SKIP_THIS
#
# Copyright (C) 2009
# by 52 North Initiative for Geospatial Open Source Software GmbH
#
# Contact: Andreas Wytzisk
# 52 North Initiative for Geospatial Open Source Software GmbH
# Martin-Luther-King-Weg 24
# 48155 Muenster, Germany
# info@52north.org
#
# This program is free software; you can redistribute and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed WITHOUT ANY WARRANTY; even without the
# implied WARRANTY OF MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program (see gnu-gpl v2.txt). If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA or visit the Free Software Foundation web page,
# http://www.fsf.org.
#
# @author: Henning Bredel
# Created: Oct 26, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$id $'

import gps
import time
import logging

import utils

LOGGER = logging.getLogger('position-logger')
utils.init_logging(LOGGER)

###############################################################################

def get_position_info(query='admosy'):
    """Gathers the current position information.

        Generator function to retrieve GPS position information from a GPS
        session running in background. A gpsd daemon has to be running
        in background.

        The gathered information can be retrieved fine-grained by passing a
        query string containing special parameter chars (see `man gpsd' for
        detailed information. However, This function queries the following:
        ===============
            a = altitude
            d = date/time
            m = NMEA mode
            o = position report
            s = NMEA status
            y = satellites
        ===============

        The returned value is a dictionary containing the most recent
        information of the current GPS session, dependent of the query
        parameter passed to the function.

        The keys to retrieve the information are:
        ======= ==================================
          latitude       the coordinates latitude (requires 'o')
          longitude    the coordinates longitude (requires 'o')
          utc             UTC time in the ISO-8601 format (requires 'd')
          altitude       Meters above mean sea level (requires 'a')
          eph            Horizontal error estimate (requires 'o')
          epv            Vertical error estimate (requires 'o')
          speed         Speed over ground (requires 'o')
          climb          Vertical velocity (requires 'o')
          status         0=no fix, 1=fix, 2=DGPS-corrected fis (requires 's')
          satellites     satellites gathered the information (requires 'y')
        ======= ==================================

        Use it as the following example:
            >>> gps_infos = get_position_info().next()

        @param query: The query string which information is of interest.
        @return: A dictionary with the current GPS information. If no current
                session is available an empty dictionary will be returned.
    """
    session = gps.gps()
    result = { # default values
              'latitude': 0.0,
              'longitude': 0.0,
              'utc': time.time(),
              'altitude': 0.0,
              'eph': 0.0,
              'epv': 0.0,
              'speed': 0.0,
              'climb': 0.0,
              'satellites': []
              }
    try:
        while True:
            try:
                session.query(query)
            except:
                LOGGER.error("No GPS connection possible. ")
                raise
            if session:
                result['latitude'] = session.fix.latitude
                result['longitude'] = session.fix.longitude
                result['utc'] = session.fix.time
                result['altitude'] = session.fix.altitude
                result['eph'] = session.fix.eph
                result['epv'] = session.fix.epv
                result['speed'] = session.fix.speed
                result['climb'] = session.fix.climb
                result['satellites'] = session.satellites
            yield result
    finally:
        del result
        del session

###############################################################################

#if __name__ == '__main__':
#    import time
#
#    for i in range(0,100):
#        infos = get_position_info().next()
#
#        print 'latitude    ' , infos['latitude']
#        print 'longitude   ' , infos['longitude']
#        print 'time utc    ' , infos['utc']
#        print 'altitude    ' , infos['altitude']
#        print 'eph         ' , infos['eph']
#        print 'epv         ' , infos['epv']
#        print 'speed       ' , infos['speed']
#        print 'climb       ' , infos['climb']
#        print len(infos['satellites'])
#
#        time.sleep(3)

