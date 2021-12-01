#!/bin/csh -f

#
# secondaryReports.csh
# uses qcreports/Configuration file so *must* be a "csh" script
#
# PRO_extracted_text
# PRO_ignored_text
#

cd `dirname $0` && source ${QCRPTS}/Configuration

# PRO-specific reports directory
setenv QCPROARCHIVE             ${QCARCHIVEDIR}/pro

foreach i (PRO_extracted_text PRO_ignored_text)
        ${QCRPTS}/reports.csh $i ${QCOUTPUTDIR}/$i.rpt ${PG_DBSERVER} ${PG_DBNAME}
        cp -p ${QCOUTPUTDIR}/$i.rpt ${QCPROARCHIVE}/$i.`date +%Y%m%d`
end

