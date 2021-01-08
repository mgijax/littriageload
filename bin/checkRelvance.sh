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

select c.mgiID, t.term, r.confidence, u.login, r.version
from bib_workflow_relevance r, voc_term t, bib_citation_cache c, mgi_user u
where r.isCurrent = 0
and r._relevance_key = t._term_key
and r._refs_key = c._refs_key
and r._createdby_key = u._user_key
and u.login = 'littriageload'
order by mgiID
;

select c.mgiID, t.term, r.confidence, u.login, r.version
from bib_workflow_relevance r, voc_term t, bib_citation_cache c, mgi_user u
where r.isCurrent = 1
and r._relevance_key = t._term_key
and r._refs_key = c._refs_key
and r._createdby_key = u._user_key
and u.login = 'relevance_classifier'
order by mgiID
;

EOSQL

date |tee -a $LOG

