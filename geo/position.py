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

import os
import gps
import time
import logging

import constants
from subprocess import Popen, PIPE

_LOG = logging.getLogger('position-logger')

###############################################################################
class GPSReceiver():
    """Receives GPS signal from gpsd Daemon.

    TODO check dbus alternative.
    """

    GPS_SESSION = None

    def __init__(self, gps_infos):
        """Creates GPS_SESSION."""
        _LOG.debug('Create GPSReceiver.')
        self.result = gps_infos

        file_ = None
        try:
            file_ = open(os.path.join(constants.CONFIG_PATH, 'gpsdevice'))
            devices_ = [dev.strip() for dev in file_.readlines() if not dev.startswith('#')]
            _LOG.debug('available GPS interfaces: %s', devices_)
            if len(devices_) != 1:
                _LOG.warn('Check your gpsdevices config file.')
            _LOG.debug("init GPS session with '%s'", 'gpsd ' + devices_[0])

            cmd = 'whereis gpsd'
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            out = p.communicate()[0].split(' ')
            _LOG.debug("out: %s", out)

            cmd = out[1] + " " + devices_[0]
            _LOG.debug(cmd)
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            self.GPS_SESSION = gps.gps()
            time.sleep(0.5)
        except Exception, e:
            self.GPS_SESSION = None
            _LOG.warning('Could not initialize GPS session in postion.py: %s', e)
            if p is not None:
                _LOG.error(p.communicate())
        finally:
            if file_ is not None:
                file_.close()

    def get_position(self, query='admosy'):
        """Gathers the current position information.

        Function to retrieve GPS position information from a GPS
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
          speed         Knots speed over ground (requires 'o')
          climb          Vertical velocity [m/s] (requires 'o')
          status         0=no fix, 1=fix, 2=DGPS-corrected fis (requires 's')
          satellites     satellites gathered the information (requires 'y')
        ======= ==================================

        @param query: The query string which information is of interest.
        @return: A dictionary with the current GPS information. If no current
                session is available an empty dictionary will be returned.
        @raise StopIteration: If no GPS connection is available.
        """
        try:
            self.GPS_SESSION.query(query)
        except:
            _LOG.error("No GPS connection possible. ")
            raise StopIteration, "No GPS connection possible. "
        if self.GPS_SESSION:
            self.result['latitude'] = self.GPS_SESSION.fix.latitude
            self.result['longitude'] = self.GPS_SESSION.fix.longitude
            self.result['utc'] = self.GPS_SESSION.fix.time
            self.result['altitude'] = self.GPS_SESSION.fix.altitude
            self.result['eph'] = self.GPS_SESSION.fix.eph
            self.result['epv'] = self.GPS_SESSION.fix.epv
            self.result['speed'] = self.GPS_SESSION.fix.speed
            self.result['climb'] = self.GPS_SESSION.fix.climb
            self.result['satellites'] = self.GPS_SESSION.satellites

            #_LOG.debug(self.result)

###############################################################################

if __name__ == '__main__':

    infos = {'latitude'  : 0.0,  # WGS84 latitude
             'longitude' : 0.0,  # WGS84 longitude
             'utc'       : None, # UTC time
             'altitude'  : 0.0,  # m over sealevel
             'eph'       : 0.0,  #
             'epv'       : 0.0,  #
             'speed'     : 0.0,  # current speed
             'climb'     : 0.0,  #
             'satellites': 0     # #satellites
             }

    recvr = GPSReceiver(infos)

    for i in range(0, 100):
        recvr.get_position()

        print 'latitude    ' , infos['latitude']
        print 'longitude   ' , infos['longitude']
        print 'time utc    ' , infos['utc']
        print 'altitude    ' , infos['altitude']
        print 'eph         ' , infos['eph']
        print 'epv         ' , infos['epv']
        print 'speed       ' , infos['speed']
        print 'climb       ' , infos['climb']
        print infos['satellites']

        time.sleep(3)

