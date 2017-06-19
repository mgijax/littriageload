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
preload ${OUTPUTDIR}

echo "" >> ${LOG}
date >> ${LOG}
echo "Move ${PUBLISHEDDIR} files to ${INPUTDIR}"  | tee -a ${LOG}
cd ${PUBLISHEDDIR}
for i in *
do
mv -f ${i}/*.pdf ${INPUTDIR}/${i} 2>> ${LOG}
done
STAT=$?
checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py"

# for testing
echo "${PUBLISHEDDIR} listing..." | tee -a ${LOG}
ls -l ${PUBLISHEDDIR}/*/* | tee -a ${LOG}
echo "---------------------" | tee -a ${LOG}
echo "${INPUTDIR} listing..." | tee -a ${LOG}
ls -l ${INPUTDIR}/*/* | tee -a ${LOG}

cd `dirname $0`/..

#
# run the load
#
#echo "" >> ${LOG}
#date >> ${LOG}
#echo "Run littriageload.py"  | tee -a ${LOG}
#${LITTRIAGELOAD}/bin/littriageload.py  
#STAT=$?
#checkStatus ${STAT} "${LITTRIAGELOAD}/bin/littriageload.py"

#
# run BCP
#

# BCP delimiters
#COLDELIM="\t"
#LINEDELIM="\n"
#TABLE=BIB_Refs
#if [ -s "${OUTPUTDIR}/${TABLE}.bcp" ]
#then
#    echo "" >> ${LOG}
#    date >> ${LOG}
#    echo 'BCP in BIB_Refs'  >> ${LOG}
#
#    # Drop indexes
#    ${MGD_DBSCHEMADIR}/index/${TABLE}_drop.object >> ${LOG}
#
#    # BCP new data
#    ${PG_DBUTILS}/bin/bcpin.csh ${MGD_DBSERVER} ${MGD_DBNAME} ${TABLE} ${OUTPUTDIR} ${TABLE}.bcp ${COLDELIM} ${LINEDELIM} ${SCHEMA} >> ${LOG}
#
#    # Create indexes
#    ${MGD_DBSCHEMADIR}/index/${TABLE}_create.object >> ${LOG}
#fi

# run postload cleanup and email logs
shutDown

