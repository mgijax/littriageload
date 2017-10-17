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
#
LOG=littriageload.log
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
find ${FILEDIR}/archive/* -type f -mtime +30 -exec rm -rf {} \; | tee -a ${LOG}
find ${FILEDIR}/logs.* -type d -mtime +30 -exec rm -rf {} \; | tee -a ${LOG}

#
# copy the ${LOGDIR} to a separate archive
# make sure this happens *before* next step
#
cp -r ${LOGDIR} ${LOGDIR}.`date '+%Y%m%d.%H%M'` | tee -a ${LOG}

#
# createArchive including OUTPUTDIR, INPUTDIR, etc.
# sets "JOBKEY"
# preload will create the LOG_DIAG, LOG_ERROR, etc. files
preload ${OUTPUTDIR}

#
# Create curator subdirectories in input directory
# Create curator subdirectories in needs review directory
# note: this will not remove old/obsolete input directories
#       archive obsolete curator directories manually
#
cd ${PUBLISHEDDIR}
for i in *
do
mkdir -p ${INPUTDIR}/${i}
mkdir -p ${NEEDSREVIEWTRIAGEDIR}/${i}
done
date | tee -a ${LOG_DIAG}
echo "---------------------" | tee -a ${LOG_DIAG}
echo "input directory" | tee -a ${LOG_DIAG}
ls -l ${INPUTDIR_DIAG} | tee -a ${LOG_DIAG}
echo "---------------------" | tee -a ${LOG_DIAG}
echo "needs review directory"| tee -a ${LOG_DIAG}
ls -l ${NEEDSREVIEWTRIAGEDIR} | tee -a ${LOG_DIAG}

#
# if DEV, use 'cp'
# else use 'mv'
#
# cp/mv PUBLISHEDDIR/user pdf files to INPUTDIR/user
#
date | tee -a ${LOG_DIAG}
echo "---------------------" | tee -a ${LOG_DIAG}
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}"  | tee -a ${LOG_DIAG}
cd ${PUBLISHEDDIR}
for i in `find . -maxdepth 2 -iname "[a-zA-Z0-9]*.pdf"`
do
if [ `uname -n` = "bhmgidevapp01" ]
then
echo "mv -f ${i} ${INPUTDIR}/${i}" 2>> ${LOG_DIAG}
mv -f ${i} ${INPUTDIR}/${i} 2>> ${LOG_DIAG}
elif [ "${INSTALL_TYPE}" = "dev" ]
then
echo "cp -f ${i} ${INPUTDIR}/${i}" 2>> ${LOG_DIAG}
cp -f ${i} ${INPUTDIR}/${i} 2>> ${LOG_DIAG}
else
echo "mv -f ${i} ${INPUTDIR}/${i}" 2>> ${LOG_DIAG}
mv -f ${i} ${INPUTDIR}/${i} 2>> ${LOG_DIAG}
fi
done

# results of cp/mv
date | tee -a ${LOG_DIAG}
echo "---------------------" | tee -a ${LOG_DIAG}
echo "${PUBLISHEDDIR} listing : NOT MOVED TO INPUT DIRECTORY" | tee -a ${LOG_DIAG}
ls -l ${PUBLISHEDDIR}/*/* | tee -a ${LOG_DIAG}
#echo "---------------------" | tee -a ${LOG_DIAG}
#echo "${INPUTDIR} listing : MOVED TO INPUT DIRECTORY" | tee -a ${LOG_DIAG}
#ls -l ${INPUTDIR}/*/* | tee -a ${LOG_DIAG}

cd ${LITTRIAGELOAD}

# update cache : must be current
#date | tee -a ${LOG_DIAG}
#echo "Update BIB_Citation_Cache"  | tee -a ${LOG_DIAG}
#${MGICACHELOAD}/bibcitation.csh | tee -a ${LOG_DIAG}
#STAT=$?
#checkStatus ${STAT} "${MGICACHELOAD}/bibcitation.csh" | tee -a ${LOG_DIAG}

#
# run the load
#
date | tee -a ${LOG_DIAG}
echo "---------------------" | tee -a ${LOG_DIAG}
echo "Run littriageload.py"  | tee -a ${LOG_DIAG}
${LITTRIAGELOAD}/bin/littriageload.py | tee -a ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py" | tee -a ${LOG_DIAG}

# update cache
date | tee -a ${LOG_DIAG}
echo "Update BIB_Citation_Cache"  | tee -a ${LOG_DIAG}
${MGICACHELOAD}/bibcitation.csh | tee -a ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/bibcitation.csh" | tee -a ${LOG_DIAG}

# run postload cleanup and email logs
shutDown

