#!/bin/sh

#
#
# processRelevance.sh
#
# The purpose of this script is to process the Relenvance Classifier using the Predicated Set of References
#
#       1. makePredictedFile.py
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
    PYTHONPATH=${PYTHONPATH}:${ANACONDAPYTHONLIB}; export PYTHONPATH
else
    echo "Missing configuration file: ${ANACONDAPYTHON}"
    exit 1
fi

LOG=${LOG_RELEVANCE}
rm -rf ${LOG}
>>${LOG}

echo 'PYTHON', $PYTHON | tee -a $LOG
echo 'PYTHONPATH', $PYTHONPATH | tee -a $LOG

date | tee -a ${LOG}
${PYTHON} makePredictedFile.py | tee -a $LOG

date | tee -a ${LOG}
rm -rf ${PREDICTED_RELEVANCE}
${ANACONDAPYTHONLIB}/predict.py -m relevanceClassifier.pkl -p figureTextLegCloseWords50 -p removeURLsCleanStem ${NOTSPECIFIED_RELEVANCE} > ${PREDICTED_RELEVANCE}

date | tee -a ${LOG}
