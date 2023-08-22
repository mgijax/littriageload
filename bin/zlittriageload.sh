#!/bin/sh

#
# This script is a wrapper around the process that loads 
#	TR12250/Literature Triage
#
#     littriageload.sh 
#
# 1. Move ${PUBLISHEDDIR} PDF files to ${INPUTDIR}
# 2. Process PDF files in ${INPUTDIR}
#

cd `dirname $0` 

COMMON_CONFIG=../littriageload.config

USAGE="Usage: littriageload.sh"

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

rm -rf ${LOG_DIAG}

# secondary triage
date >> ${LOG_DIAG} 2>&1
echo "process secondary triage" >> ${LOG_DIAG} 2>&1
${LITTRIAGELOAD}/bin/processSecondary.sh >> ${LOG_DIAG} 2>&1

