#!/bin/csh -f

#
# secondaryReports.csh
# uses qcreports/Configuration file so *must* be a "csh" script
#
# PRO_extracted_text.sql
# PRO_ignored_text.sql
#

cd `dirname $0` && source ${QCRPTS}/Configuration

# PRO-specific reports directory
setenv QCPROARCHIVE             ${QCARCHIVEDIR}/pro

foreach i (*.sql)
    if ( $i == "PRO_extracted_text.sql" || $i == "PRO_ignored_text.sql" ) then
	${QCRPTS}/reports.csh $i ${QCOUTPUTDIR}/$i.rpt ${PG_DBSERVER} ${PG_DBNAME}
	cp -p ${QCOUTPUTDIR}/$i.rpt ${QCPROARCHIVE}/$i.`date +%Y%m%d`
    endif
end

