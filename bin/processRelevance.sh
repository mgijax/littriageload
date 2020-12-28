#!/bin/sh

#
#
# processRelevance.sh
#
# The purpose of this script is to process the Relenvance Classifier using the Predicated Set of References
#
#       1. makePredicted.py
#               . select refs from bib_workflow_relevance where 'Not Specified' (70594668)
#               . create relevance text file (NOTSPECIFIED_RELEVANCE) as input to predict.py
#
#       2. predict.py (lib/python_anaconda)
#               . using NOTSPECIFIED_RELEVANCE, process the predictions (PREDICTED_RELEVANCE)
#
#       3. updatePredicted.py
#               . using PREDICTED_RELEVANCE, add predicted records to bib_workflow_relevance
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
rm -rf ${LOG_RELEVANCE}
>>${LOG_RELEVANCE}

date >> ${LOG_RELEVANCE} 2>&1
echo 'PYTHON', $PYTHON  >> ${LOG_RELEVANCE} 2>&1
echo 'PYTHONPATH', $PYTHONPATH  >> ${LOG_RELEVANCE} 2>&1

date >> ${LOG_RELEVANCE} 2>&1
${PYTHON} makePredicted.py  >> ${LOG_RELEVANCE} 2>&1

date >> ${LOG_RELEVANCE} 2>&1
rm -rf ${PREDICTED_RELEVANCE}
${ANACONDAPYTHON} ${ANACONDAPYTHONLIB}/predict.py -m ${RELEVANCECLASSIFIERPKL} -p figureTextLegCloseWords50 -p removeURLsCleanStem ${NOTSPECIFIED_RELEVANCE} > ${PREDICTED_RELEVANCE}

date >> ${LOG_RELEVANCE} 2>&1
${PYTHON} updatePredicted.py  >> ${LOG_RELEVANCE} 2>&1
date >> ${LOG_RELEVANCE} 2>&1

date >> ${LOG_RELEVANCE} 2>&1
