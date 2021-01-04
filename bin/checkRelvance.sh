#!/bin/csh -f

if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
 
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $LOG

select c.mgiID, t.term, r.confidence
from bib_workflow_relevance r, voc_term t, bib_citation_cache c
where r._assoc_key >= 404568
and r.isCurrent = 1
and r._relevance_key = t._term_key
and r._refs_key = c._refs_key
order by mgiID
;

EOSQL

date |tee -a $LOG

