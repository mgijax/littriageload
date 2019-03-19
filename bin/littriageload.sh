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

#
# Source the DLA library functions.
#
if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" >> ${LOG} 2>&1
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." >> ${LOG} 2>&1
    exit 1
fi

#
# clean out archive, logs.*, input.* after 30 days
#
find ${FILEDIR}/archive/* -type f -mtime +30 -exec rm -rf {} \; >> ${LOG} 2>&1
find ${FILEDIR}/logs.* -type d -mtime +30 -exec rm -rf {} \; >> ${LOG} 2>&1
find ${FILEDIR}/input.* -type d -mtime +14 -exec rm -rf {} \; >> ${LOG} 2>&1

#
# copy the ${LOGDIR} to a separate archive
# make sure this happens *before* next step
#
cp -r ${LOGDIR} ${LOGDIR}.`date '+%Y%m%d.%H%M'` >> ${LOG} 2>&1

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
date >> ${LOG}
echo "---------------------" >> ${LOG} 2>&1
echo "input directory" >> ${LOG} 2>&1
ls -l ${INPUTDIR_DIAG} >> ${LOG} 2>&1
echo "---------------------" >> ${LOG} 2>&1
echo "needs review directory" >> ${LOG} 2>&1
ls -l ${NEEDSREVIEWTRIAGEDIR} >> ${LOG} 2>&1

#
# run findNLMrefres.sh to find references that are mising DOI ids
# this will copy the pdfs for this set (if pdf exists)
# into the ${LITTRIAGE_NEWNEW}/littriage_NLM_refresh directory
#
date >> ${LOG}
echo "running findNLMrefresh.sh..." >> ${LOG} 2>&1
${LITTRIAGELOAD}/bin/findNLMrefresh.sh >> ${LOG} 2>&1

#
# if DEV, use 'cp'
# else use 'mv'
#
# cp/mv PUBLISHEDDIR/user pdf files to INPUTDIR/user
#
date >> ${LOG}
echo "---------------------" >> ${LOG} 2>&1
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}" >> ${LOG} 2>&1
cd ${PUBLISHEDDIR}
for i in `find . -maxdepth 2 -iname "[a-zA-Z0-9]*.pdf"`
do
if [ `uname -n` = "bhmgidevapp01" ]
then
echo "cp/rm -f ${i} ${INPUTDIR}/${i}" >> ${LOG} 2>&1
cp -f ${i} ${INPUTDIR}/${i} >> ${LOG} 2>&1
rm -rf ${i} >> ${LOG} 2>&1
elif [ "${INSTALL_TYPE}" = "dev" ]
then
echo "cp -f ${i} ${INPUTDIR}/${i}" >> ${LOG} 2>&1
cp -f ${i} ${INPUTDIR}/${i} >> ${LOG} 2>&1
else
echo "cp/rm -f ${i} ${INPUTDIR}/${i}" >> ${LOG} 2>&1
cp -f ${i} ${INPUTDIR}/${i} >> ${LOG} 2>&1
rm -rf ${i} >> ${LOG} 2>&1
fi
done

# results of cp/mv
date >> ${LOG} 2>&1
echo "---------------------" >> ${LOG} 2>&1
echo "${PUBLISHEDDIR} listing : NOT MOVED TO INPUT DIRECTORY" >> ${LOG} 2>&1
ls -l ${PUBLISHEDDIR}/*/* >> ${LOG} 2>&1

#
# copy the ${INPUTDIR} to a separate archive
# this will be used if help restart a load
# make sure this happens *before* next step
#
timestamp=`date '+%Y%m%d.%H%M'`
cp -r ${INPUTDIR} ${INPUTDIR}.${timestamp} >> ${LOG} 2>&1
rm -rf ${LASTINPUTDIR} >> ${LOG} 2>&1
ln -s ${INPUTDIR}.${timestamp} ${LASTINPUTDIR} >> ${LOG} 2>&1

cd ${LITTRIAGELOAD}

#
# run the load
#
date >> ${LOG_DIAG} 2>&1
echo "---------------------" >> ${LOG_DIAG} 2>&1
echo "Run littriageload.py"  >> ${LOG_DIAG} 2>&1
${LITTRIAGELOAD}/bin/littriageload.py >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py" >> ${LOG_DIAG} 2>&1

# update cache
date >> ${LOG_DIAG} 2>&1
echo "Update BIB_Citation_Cache"  >> ${LOG_DIAG} 2>&1
${MGICACHELOAD}/bibcitation.csh >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/bibcitation.csh" >> ${LOG_DIAG} 2>&1

# run postload cleanup and email logs
shutDown

