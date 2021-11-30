\echo ''
\echo 'Lit Triage PRO ignore extracted text'
\echo ''

select t.term
from voc_term t
where t._vocab_key = 170
order by t.term
