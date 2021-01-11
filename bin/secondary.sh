#!/bin/sh

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

LOG=${LOG_SECONDARY}
rm -rf ${LOG}
>>${LOG}

date >> ${LOG} 2>&1
${PYTHON} secondaryAP.py >> ${LOG} 2>&1
date >> ${LOG} 2>&1

date >> ${LOG} 2>&1
${PYTHON} secondaryGXD.py >> ${LOG} 2>&1
date >> ${LOG} 2>&1

date >> ${LOG} 2>&1
${PYTHON} secondaryQTL.py >> ${LOG} 2>&1
date >> ${LOG} 2>&1

date >> ${LOG} 2>&1
${PYTHON} secondaryTumor.py >> ${LOG} 2>&1
date >> ${LOG} 2>&1

date >> ${LOG} 2>&1