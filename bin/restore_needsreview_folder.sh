#!/bin/sh

#
# This purpose of this script is to move the needs_review folders
# to the master input folder so it can be re-processed during the
# next run of the littriage load.
#

cd `dirname $0` 

COMMON_CONFIG=../littriageload.config

USAGE="Usage: restore_needsreview_folder.sh"

#
# Make sure the common configuration file exists and source it. 
#
if [ -f ${COMMON_CONFIG} ]
then
    . ${COMMON_CONFIG}
else
    echo "Missing configuration file: ${COMMON_CONFIG}"
    exit 1
fi

#
# Initialize the log file.
# open LOG in append mode and redirect stdout
#
LOG=${LOG_FILE}
rm -rf ${LOG}
>>${LOG}

#
# mv {NEEDSREVIEWTRIAGEDIR/user pdf files to INPUTDIR/user
#
date >> ${LOG}
echo "---------------------" >> ${LOG} 2>&1
echo "Move ${NEEDSREVIEWTRIAGEDIR} files to ${INPUTDIR}" >> ${LOG} 2>&1
rm -rf ${NEEDSREVIEWTRIAGEDIR}/*/.DS_Store >> ${LOG} 2>&1
cd ${NEEDSREVIEWTRIAGEDIR} >> ${LOG} 2>&1
for i in `find . -maxdepth 2 -iname "[a-zA-Z0-9]*.pdf"`
do
echo "cp/rm -f ${i} ${INPUTDIR}/${i}" >> ${LOG} 2>&1
mv -vn ${i} ${INPUTDIR}/${i} >> ${LOG} 2>&1
done

