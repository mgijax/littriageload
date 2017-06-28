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
# copy the ${LOGDIR} to a separate archive
# make sure this happens *before* next step
#
cp -r ${LOGDIR} ${LOGDIR}.`date '+%Y%m%d.%H%M'`

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
# clean out arhicve and logs.* after 30 days
#
find ${FILEDIR} -type f -mtime +30 | grep "archive" | sort | sed 's/^/rm -f /' | tee -a ${LOG}
find ${FILEDIR} -type f -mtime +30 | grep "logs." | sort | sed 's/^/rm -f /' | tee -a ${LOG}

#
# createArchive including OUTPUTDIR, INPUTDIR, etc.
# sets "JOBKEY"
preload ${OUTPUTDIR}

#
# Create curator subdirectories in input directory
# Create curator subdirectories in failed directory
# note: this will not remove old/obsolete input directories
#       archive obsolete curator directories manually
#
cd ${PUBLISHEDDIR}
for i in *
do
mkdir -p ${INPUTDIR}/${i}
mkdir -p ${FAILEDTRIAGEDIR}/${i}
done
echo 'input directory'
ls -l ${INPUTDIR}
echo 'failed directory'
ls -l ${FAILEDTRIAGEDIR}

#
# if DEV, use 'cp'
# else use 'mv'
#
# cp/mv PUBLISHEDDIR/user pdf files to INPUTDIR/user
#
echo "" | tee -a ${LOG}
date | tee -a ${LOG}
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}"  | tee -a ${LOG}
cd ${PUBLISHEDDIR}
for i in *
do
for j in "${i}/*.pdf" "${i}/*.PDF"
do
if [ "${INSTALL_TYPE}" = "dev" ]
then
cp -f ${j} ${INPUTDIR}/${i} 2>> ${LOG}
else
mv -f ${j} ${INPUTDIR}/${i} 2>> ${LOG}
fi
done
done

# results of cp/mv
echo "---------------------" | tee -a ${LOG}
echo "${PUBLISHEDDIR} listing : NOT MOVED TO INPUT DIRECTORY" | tee -a ${LOG}
ls -l ${PUBLISHEDDIR}/*/* | tee -a ${LOG}
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
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py" | tee -a ${LOG}

# run postload cleanup and email logs
shutDown

