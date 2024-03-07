#!/bin/csh -f

#
# Template
#


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

select c.mgiid, c.pubmedid, t.term, v.confidence, s._assoc_key
into temp table refs
from bib_citation_cache c, bib_workflow_status s, voc_term t, 
bib_refs r, bib_workflow_relevance v
where c._refs_key = s._refs_key
and s.isCurrent = 1
and s._status_key = t._term_key
and s._group_key = 31576665
and c._refs_key = r._refs_key
and r.creation_date between '09/01/2022' and '11/30/2022'
and c._refs_key = v._refs_key
and v._modifiedby_key = 1617
and v.confidence >= -2.75
order by c.mgiid
;

create index refs_0 on refs (_assoc_key);

select * from refs;

update bib_workflow_status s set _status_key = 71027551 from refs r where r._assoc_key = s._assoc_key

EOSQL

date |tee -a $LOG

