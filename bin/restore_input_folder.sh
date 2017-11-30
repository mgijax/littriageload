#!/bin/sh

#
# This purpose of this script is to restore the last input folder
# to the master input folder so it can be re-processed during the
# next run of the littriage load.
#
# This will be necessary, for example, if the Production database is 
# restored from a backup due data corrupption from another load or process.
#
# If this happens, then the last input folder needs to be processed again
# by the Lit Triage loader.
#

cd `dirname $0` 

COMMON_CONFIG=../littriageload.config

USAGE="Usage: restore_input_folder.sh"

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

cp -R ${LASTINPUTDIR} ${INPUTDIR} >> ${LOG} 2>&1

