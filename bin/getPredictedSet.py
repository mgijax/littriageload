 
import sys 
import os
import db
import reportlib

db.setTrace()

CRT = reportlib.CRT
SPACE = reportlib.SPACE
TAB = reportlib.TAB
PAGE = reportlib.PAGE

#
# Main
#

fp = reportlib.init(sys.argv[0], printHeading = None)

results = db.sql(cmd, 'auto')

for r in results:
    fp.write(r['item'] + CRT)

reportlib.finish_nonps(fp)

