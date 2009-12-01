"""@brief Contains some utility methods."""
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
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program (see gnu-gpl v2.txt).  If not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA or visit the Free Software Foundation web page,
# http://www.fsf.org.
#
# Author: Henning Bredel
# Created: Oct 17, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$id $'
import os

import logging
import logging.config

from gettext import gettext

from sugar import logger

LOGGER = logging.getLogger('utils-logger')
_DEFAULT_LOG_LEVEL = logging.DEBUG

###############################################################################

def __init__():
    """Initializes the logger for this module only."""
    init_logging(LOGGER)
    LOGGER("Logger for utils module initialized.")

def init_logging(logger_, log_level=_DEFAULT_LOG_LEVEL):
    """Initializes logging for given logger instance.

        Creates a file logging handler and adds it  to the given logger_ parameter.

        @param logger_: The logging instance the handler will be created for.
        @param log_level: The default logging level.
    """
    logger_.setLevel(log_level)

    # Second log handler: outputs to a file.
    std_log_dir = logger.get_logs_dir()
    file_ =  'geospace.activity.log'
    format = '%(levelname)s --  ' \
                  '%(filename)s %(funcName)s [line %(lineno)d]:\n %(message)s\n'
    file_handler = logging.FileHandler(os.path.join(std_log_dir, file_))
    file_formatter = logging.Formatter(format)
    file_handler.setFormatter(file_formatter)
    logger_.addHandler(file_handler)

def _(string):
    """Defensive method against variables not translated correctly.

        Since some strings require variables to be substituted into them, they
        need to be translated carefully. If they're not translated correctly,
        trying to do a string substitution can crash your activity.

        The code below redefines the _() to use the gettext method only if
        gettext actually works. If there is an exception, the code will simply
        return the untranslated string. This ensures that instead of crashing,
        your activity will simply not translate your string.

        @see http://wiki.laptop.org/go/Internationalization_in_Sugar
    """
    istrs_test = {}
    for i in range (0, 4):
        istrs_test[str(i)] = str(i)

    #try to use gettext. If it fails, then just return the string untranslated.
    try:
        #test translating the string with many replacements
        i = gettext(string)
        test = i % istrs_test
        print test
    except:
        #if it doesn't work, revert
        i = string
    return i

###############################################################################

