#!/bin/sh

#
#
# findNLMrefresh.sh
#
# The purpose of this script is to:
#
# 1. query the database for References that are
#	. reference type = Peer Reviewed Article
#	. have pubmed id
#	. do not have doi id
#	. creation date of MGD Reference is between today-7 and today
#       . relevance != discard
#
# 2. find the PDF (by using MGI ID) of the Reference in the Lit Triage Master folder
#
# 3. copy the PDF into the New_New/littriage_NLM_refresh folder
#    this will process the PDF and add the DOI id during the next run of the Lit Triage load
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

LOG=${LOG_NLMREFRESHFIND}
PDF=${LOG_NLMREFRESHPDF}
rm -rf ${LOG} ${PDF}
>>${LOG}

date | tee -a ${LOG}

cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${LOG}

select count(c.*)
from bib_citation_cache c, bib_refs r, bib_workflow_relevance v
where c.referencetype = 'Peer Reviewed Article'
and c.pubmedID is not null
and c.doiID is null
and c._refs_key = r._refs_key
and r.creation_date between (now() + interval '-7 day') and now()
and c._refs_key = v._refs_key
and v.isCurrent = 1
and v._relevance_key not in (70594666)
;

select c.mgiID, c.pubmedID
from bib_citation_cache c, bib_refs r, bib_workflow_relevance v
where c.referencetype = 'Peer Reviewed Article'
and c.pubmedID is not null
and c.doiID is null
and c._refs_key = r._refs_key
and r.creation_date between (now() + interval '-7 day') and now()
and c._refs_key = v._refs_key
and v.isCurrent = 1
and v._relevance_key not in (70594666)
;
EOSQL

cut -f1 -d"|" ${LOG} | grep MGI | sed 's/MGI://' > ${PDF}
ls -l ${PDF}

echo 'will copy PDFs to master folder....' | tee -a ${LOG}
echo $LITTRIAGE_MASTER | tee -a ${LOG}

cat ${PDF} | while read line
do
if [ -f ${LITTRIAGE_MASTER}/*/$line.pdf -a ! -f ${LITTRIAGE_NEWNEW}/littriage_update_pdf/$line.pdf ]
then
echo 'coping to littriage master folder', $line | tee -a ${LOG}
ls ${LITTRIAGE_MASTER}/*/$line.pdf
cp -r ${LITTRIAGE_MASTER}/*/$line.pdf ${LITTRIAGE_NEWNEW}/littriage_NLM_refresh
else
echo 'not copied to littriage master folder', $line | tee -a ${LOG}
fi
done

date | tee -a ${LOG}

