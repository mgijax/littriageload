#!/bin/sh

#
#
# processRelevance.sh
#
# The purpose of this script is to process the Relenvance Classifier using the Predicated Set of References
#
#       1. getPredictedSet.py 
#               . select refs from bib_workflow_relevance where 'Not Specified' (70594668)
#               . create relevance text file (NOTSPECIFIED_RELEVANCE)
#
#       2. predict.py (lib/python_anaconda)
#               . using NOTSPECIFIED_RELEVANCE, process the predictions (PREDICTED_RELEVANCE)
#
#       3. updatePredictedSet.py
#               . using PREDICT)RELEVANCE, add predicted records to bib_workflow_relevance
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

LOG=${LOG_RELEVANCE}
PDF=${LOG_RELEVANCE}
rm -rf ${LOG}
>>${LOG}

#
# Example command to get refs that need relevance prediction from db and into
#  a sample file
#date | tee -a ${LOG}
#rm -rf ${NOTSPECIFIED_RELEVANCE}
#getPredicatedSet.py -s ${MGD_DBSERVER} -d ${MGD_DBNAME} > ${NOTSPECIFIED_RELEVANCE}
#date | tee -a ${LOG}

# Example command to run predictions on that sample file and create prediction
#  file
#predict.py -m relevanceClassifier.pkl -p figureTextLegCloseWords50 -p removeURLsCleanStem samplefile > predictions

date | tee -a ${LOG}
