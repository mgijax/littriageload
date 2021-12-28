#!/bin/sh

#
#
# processRelevance.sh
#
# The purpose of this script is to process the Relevance Classifier using the Predicted Set of References
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

#
#  Source the DLA library functions.
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

date | tee -a ${LOG_RELEVANCE} 
echo 'PYTHON', $PYTHON  >> ${LOG_RELEVANCE} 2>&1
echo 'PYTHONPATH', $PYTHONPATH  >> ${LOG_RELEVANCE} 2>&1

date | tee -a ${LOG_RELEVANCE}
echo "Running makePredicted.py" >> ${LOG_RELEVANCE} 2>&1
${PYTHON} makePredicted.py  >> ${LOG_RELEVANCE} 2>&1
STAT=$?
checkStatus ${STAT} "${GXDHTLOAD}/bin/makePredicted.py"

date | tee -a ${LOG_RELEVANCE}
echo "Running predict.py" | tee -a  ${LOG_RELEVANCE}
rm -rf ${PREDICTED_RELEVANCE}

${ANACONDAPYTHON} ${ANACONDAPYTHONLIB}/predict.py -m ${RELEVANCECLASSIFIERPKL} -p figureTextLegCloseWords50 -p removeURLsCleanStem ${NOTSPECIFIED_RELEVANCE} > ${PREDICTED_RELEVANCE}
STAT=$?
checkStatus ${STAT} "${GXDHTLOAD}/bin/predict.py"

date | tee -a ${LOG_RELEVANCE}
echo "Running updateRelevance.py" | tee -a ${LOG_RELEVANCE}
${PYTHON} updateRelevance.py  >> ${LOG_RELEVANCE} 2>&1
STAT=$?
checkStatus ${STAT} "${GXDHTLOAD}/bin/updateRelevance.py"

date | tee -a ${LOG_RELEVANCE}
