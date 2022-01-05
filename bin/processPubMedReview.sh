#!/bin/sh

#
# The purpose of this script is to run the processReviewUpdates python script
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
LOG=${LOG_PUBMEDREVIEW}
rm -rf ${LOG}
>>${LOG}

date >> ${LOG_PUBMEDREVIEW} 2>&1
${PYTHON} ${LITTRIAGELOAD}/bin/processPubMedReview.py >> ${LOG_PUBMEDREVIEW} 2>&1

#date >> ${LOG_PUBMEDREVIEW} 2>&1
#${MGICACHELOAD}/bibcitation.csh >> ${LOG_PUBMEDREVIEW} 2>&1

date |tee -a $LOG

