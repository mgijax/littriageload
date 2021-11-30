\echo ''
\echo 'Lit Triage PRO extracted text'
\echo ''

select t.term
from voc_term t
where t._vocab_key = 169
order by t.term
