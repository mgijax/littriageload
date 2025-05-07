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

# Check that PUBLISHEDDIR directory exists
if [ ! -d ${PUBLISHEDDIR} ]
then
    echo "_New_Newcurrent directory is missing: ${PUBLISHEDDIR}"
    exit 1
fi

# Check that PUBLISHEDDIR directory is not empty
if [ "$(ls -A ${PUBLISHEDDIR})" ]
then
    echo "_New_Newcurrent directory is not empty: ${PUBLISHEDDIR}"
else
    echo "_New_Newcurrent directory is empty: ${PUBLISHEDDIR}"
    exit 1
fi

# Check that NEEDSREVIEWTRIAGEDIR directory exists
if [ ! -d ${NEEDSREVIEWTRIAGEDIR} ]
then
    echo "needs_review directory is missing: ${NEEDSREVIEWTRIAGEDIR}"
    exit 1
fi

# Check that NEEDSREVIEWTRIAGEDIR directory is not empty
if [ "$(ls -A ${NEEDSREVIEWTRIAGEDIR})" ]
then
    echo "needs_review directory is not empty: ${NEEDSREVIEWTRIAGEDIR}"
else
    echo "needs_review directory is empty: ${NEEDSREVIEWTRIAGEDIR}"
    exit 1
fi

#
# Initialize the log file.
# open LOG in append mode and redirect stdout
#
LOG=${LOG_FILE}
rm -rf ${LOG}
>>${LOG}
rm -rf ${LOG_RENAME}
>>${LOG_RENAME}

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
# clean out logs.*, input.*, output.* after 35 days
#
find ${FILEDIR}/logs.* -type d -mtime +35 -exec rm -rf {} \; >> ${LOG} 2>&1
find ${FILEDIR}/input.* -type d -mtime +35 -exec rm -rf {} \; >> ${LOG} 2>&1
find ${FILEDIR}/output.* -type d -mtime +35 -exec rm -rf {} \; >> ${LOG} 2>&1

#
# copy the ${LOGDIR} to a separate archive
# make sure this happens *before* next step
#
timestamp=`date '+%Y%m%d.%H%M'`
cp -r ${LOGDIR} ${LOGDIR}.${timestamp} >> ${LOG} 2>&1

#
# createArchive including OUTPUTDIR, INPUTDIR, etc.
# sets "JOBKEY"
# preload will create the LOG_DIAG, LOG_ERROR, etc. files
preloadNoArchive ${OUTPUTDIR}

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
# turn off if not on production server
#
# 12/21/2024 : turn off by default; not really needed anymore
# as the doi ids are picked up along with the pubmedid from EUtils
#
#date >> ${LOG}
#echo "running findNLMrefresh.sh..." >> ${LOG} 2>&1
#${LITTRIAGELOAD}/bin/findNLMrefresh.sh >> ${LOG} 2>&1

# move needs_review files to INPUT/user
#date >> ${LOG} 2>&1
#echo "running restore_needsreview_folder.sh..." >> ${LOG} 2>&1
#${LITTRIAGELOAD}/bin/restore_needsreview_folder.sh >> ${LOG} 2>&1

#
# rename PUBLISHEDDIR/user pdf files that contain terms that will 
# are cheched by jenkins_admin/logList.tasks.daily
# log the renames to a different log:  logs/littriageload.rename.log
# and do *not* add this log to jenkins_admin/logList.tasks.daily
#
date >> ${LOG}
date >> ${LOG_RENAME}
echo "---------------------" >> ${LOG} 2>&1
echo "Rename ${PUBLISHEDDIR} files that contain bad terms" >> ${LOG} 2>&1
cd ${PUBLISHEDDIR}
for i in `find . -maxdepth 2 -iname "*fail*.pdf"`
do
NEW_FILE=$(echo $i | sed 's/fail//')
echo "mv ${i} $NEW_FILE" >> ${LOG_RENAME} 2>&1
mv "$i" "$NEW_FILE" >> ${LOG_RENAME} 2>&1
done

#
# cp/mv PUBLISHEDDIR/user pdf files to INPUTDIR/user
#
date >> ${LOG}
echo "---------------------" >> ${LOG} 2>&1
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}" >> ${LOG} 2>&1
rsync -avz --exclude=".*" --remove-source-files ${PUBLISHEDDIR}/* ${INPUTDIR} >> ${LOG} 2>&1

# results of cp/mv
date >> ${LOG} 2>&1
echo "---------------------" >> ${LOG} 2>&1
echo "${PUBLISHEDDIR} listing : NOT MOVED TO INPUT DIRECTORY" >> ${LOG} 2>&1
ls -l ${PUBLISHEDDIR}/* >> ${LOG} 2>&1

#
# mv the ${INPUTDIR} to date-stamped archive
# create new ${INPUTDIR} folder using ${INPUTDIR}.default
# this will be used if help restart a load
# make sure this happens *before* next step
#
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
${PYTHON} ${LITTRIAGELOAD}/bin/littriageload.py >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py" >> ${LOG_DIAG} 2>&1

#
# 11/26/2024
# update GXD HT : add J:, set Status
# commented out/not being used at the moment
# if these become a problem for Connie, then turn this on/un-comment
#
#echo "Running updateGXDHT.py" | tee -a ${LOG_DIAG}
#${PYTHON} updateGXDHT.py  >> ${LOG_DIAG} 2>&1
#checkStatus ${STAT} "${LITTRIAGELOAD}/bin/updateGXDHT.py"

# update cache
date >> ${LOG_DIAG} 2>&1
echo "Update BIB_Citation_Cache"  >> ${LOG_DIAG} 2>&1
${MGICACHELOAD}/bibcitation.csh >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/bibcitation.csh" >> ${LOG_DIAG} 2>&1

# relevance classifier
date >> ${LOG_DIAG} 2>&1
echo "process relevance classifier" >> ${LOG_DIAG} 2>&1
${LITTRIAGELOAD}/bin/processRelevance.sh >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/processRelevance.csh" >> ${LOG_DIAG} 2>&1

# secondary triage
date >> ${LOG_DIAG} 2>&1
echo "process secondary triage" >> ${LOG_DIAG} 2>&1
${LITTRIAGELOAD}/bin/processSecondary.sh >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/processSecondary.csh" >> ${LOG_DIAG} 2>&1

# log OUTPUTDIR
cp -r ${OUTPUTDIR} ${OUTPUTDIR}.${timestamp} >> ${LOG} 2>&1

# run postload cleanup and email logs
shutDown

