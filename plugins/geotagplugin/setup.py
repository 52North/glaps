#!/usr/bin/env python
"""This file was evolved from a normal setup.py script for the only use
    of generating po/language.pot file. Use it as normal: ./setup.py genpot.
"""

import subprocess
import sys
import os

###############################################################################

def usage():
    print "You only can create pot file. Run `./setup.py genpot'."

if __name__ == '__main__':
    """
        @see: bundlebuilder.py#335 ff.
    """
    if len(sys.argv) != 2 or sys.argv[1] != 'genpot':
        usage()
        exit(1)
    else:
        po_path = os.path.join(os.curdir, 'po')
        if not os.path.isdir(po_path):
            os.mkdir(po_path)

        python_files = []
        for root_dummy, dirs_dummy, files in os.walk(os.curdir):
            for file_name in files:
                if file_name.endswith('.py'):
                    python_files.append(file_name)

        pot_file = os.path.join('po', 'language.pot')
        file = open(pot_file, "w")
        file.close()

        args = [ 'xgettext', '--join-existing', '--language=Python',
             '--keyword=_', '--add-comments=TRANS:', '--output=%s' % pot_file ]

        args += python_files
        retcode = subprocess.call(args)
        if retcode:
            print 'ERROR - xgettext failed with return code %i.' % retcode
            exit (1)

###############################################################################
