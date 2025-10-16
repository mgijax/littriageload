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
PYTHONPATH="${PYTHONLIB}:${MGI_PYTHONLIB}:${ANACONDAPYTHONLIB}"
export PYTHONPATH
${PYTHON} secondary.py >> ${LOG} 2>&1
date >> ${LOG} 2>&1

# copy logs/gxd to /data/reports/qcreports_db/archive/gxd
cp -r ${LOGDIR}/gxd ${QCREPORTDIR}/archive/gxd/littriage.`date '+%Y%m%d.%H%M'`
