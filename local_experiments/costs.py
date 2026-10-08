"""Physical attempts counted once; arm paths include their shared logical ancestry."""
from collections import defaultdict

def totals(records):
 def tokens(key):
  values=[r['usage'][key] for r in records if isinstance(r.get('usage'),dict) and key in r['usage']]
  return sum(values) if values else None
 return {'physical_attempts':len(records),'logical_requests':len({r['logical_request_id'] for r in records}),
         'reported_input_tokens':tokens('prompt_tokens'),'reported_output_tokens':tokens('completion_tokens'),
         'attempts_missing_usage':sum(not r.get('usage') for r in records),'cost':None,'cost_status':'unknown'}

def summarize_costs(client,rows):
 paths=[];arms=defaultdict(set)
 for row in rows:
  ids=set(row['logical_request_ids']);records=[r for r in client.records if r['logical_request_id'] in ids]
  paths.append({k:row[k] for k in ('root_id','arm_id','common_prefix_repeat_id','suffix_repeat_id')}|totals(records))
  arms[row['arm_id']].update(ids)
 return {'schema_version':1,'physical_deduplicated':totals(client.records),
         'logical_paths':paths,'logical_arm_unique_ancestry':{a:totals([r for r in client.records if r['logical_request_id'] in ids]) for a,ids in arms.items()},
         'definition':'Path costs include all physical retry attempts of reference, proposal, common prefix and own suffix. Shared ancestry appears in each logical path but once in physical totals. Unknown prices/usage are never zero.'}
