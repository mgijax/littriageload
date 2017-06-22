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

COMMON_CONFIG=${LITTRIAGELOAD}/littriageload.config

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
#
LOG=${LOG_DIAG}
rm -rf ${LOG}
touch ${LOG}

#
# Source the DLA library functions.
#
if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${LOG}
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${LOG}
    exit 1
fi

#
# createArchive including OUTPUTDIR, INPUTDIR, etc.
# sets "JOBKEY"
#preload ${OUTPUTDIR}

echo "" | tee -a ${LOG}
date | tee -a ${LOG}
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}"  | tee -a ${LOG}
cd ${PUBLISHEDDIR}
for i in *
do
for j in "${i}/*.pdf" "${i}/*.PDF"
do
#mv -f ${j} ${INPUTDIR}/${i} 2>> ${LOG}
cp -f ${j} ${INPUTDIR}/${i} 2>> ${LOG}
done
done

# for testing
#echo "---------------------" | tee -a ${LOG}
#echo "${PUBLISHEDDIR} listing : NOT MOVED TO INPUT DIRECTORY" | tee -a ${LOG}
#ls -l ${PUBLISHEDDIR}/*/* | tee -a ${LOG}
#echo "---------------------" | tee -a ${LOG}
#echo "${INPUTDIR} listing : MOVED TO INPUT DIRECTORY" | tee -a ${LOG}
#ls -l ${INPUTDIR}/*/* | tee -a ${LOG}

cd `dirname $0`/..

#
# run the load
#
echo "" | tee -a ${LOG}
date | tee -a ${LOG}
echo "Run littriageload.py"  | tee -a ${LOG}
${LITTRIAGELOAD}/bin/littriageload.py | tee -a ${LOG}
#STAT=$?
#checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py" | tee -a ${LOG}

# run postload cleanup and email logs
#shutDown

