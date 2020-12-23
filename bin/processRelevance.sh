#!/bin/sh

#
#
# processPredictions.sh
#
# The purpose of this script is to:
#
#       1. getRefsToPredict.py 
#               . select refs from bib_workflow_relevance where 'Not Specified' (70594668)
#               . create relevance text file; this will become the input for predict.py
#
#       2. predict.py (lib/python_anaconda)
#               . using NOTSPECIFIED_RELEVANCECLASSIFIER
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

if [ -f ${ANACONDAPYTHON} ]
then
    PYTHON=${ANACONDAPYTHON}; export PYTHON
else
    echo "Missing configuration file: ${ANACONDAPYTHON}"
    exit 1
fi
echo $PYTHON

LOG=${LOG_RELEVANCECLASSIFIER}
PDF=${LOG_RELEVANCECLASSIFIER}
rm -rf ${LOG}
>>${LOG}

#
# Example command to get refs that need relevance prediction from db and into
#  a sample file
#date | tee -a ${LOG}
#rm -rf ${NOTSPECIFIED_RELEVANCECLASSIFIER}
#getRefsToPredict.py -s ${MGD_DBSERVER} -d ${MGD_DBNAME} > ${NOTSPECIFIED_RELEVANCECLASSIFIER}
#date | tee -a ${LOG}

# Example command to run predictions on that sample file and create prediction
#  file
#predict.py -m relevanceClassifier.pkl -p figureTextLegCloseWords50 -p removeURLsCleanStem samplefile > predictions

date | tee -a ${LOG}
