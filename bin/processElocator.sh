#!/bin/sh

#
# The purpose of this script is to run the processElocator python script
#


cd `dirname $0`

COMMON_CONFIG=../littriageload.config

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
setenv LOG $0.log
rm -rf ${LOG}
>>${LOG}

date >> ${LOG} 2>&1
${PYTHON} ${LITTRIAGELOAD}/bin/processElocator.py >> ${LOG} 2>&1

date >> ${LOG} 2>&1
${MGICACHELOAD}/bibcitation.csh >> ${LOG} 2>&1

date |tee -a $LOG

