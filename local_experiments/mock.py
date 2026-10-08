"""Authored development policy; never used by the live transport or for causal claims."""
import json
import re
from .storage import digest

class MockTransport:
 def __call__(self,payload):
  role=payload['model'];messages=payload['messages'];last=messages[-1]
  text=None;calls=[]
  def tool(name,args):
   return [{'id':'mock-'+digest(payload)[:20],'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]
  if role=='mock-reviewer':
   target=re.search(r'Target call ID: (controller-[0-9a-f]+)',last['content']).group(1)
   text=json.dumps({'selected_action':{'name':'get_details_by_id','arguments':{'id':'L1002'}},'packet':'Execute the selected diagnostic call and keep the user requirements in force.','declaration':{'target_action_id':target,'scope':'action_local','instruction':'execute_target_call','close_condition':'normal_tool_return'}})
  elif role=='mock-actor':
   content=last.get('content') or ''
   if last['role']=='system' and content.startswith('Controller execution record'):
    calls=tool('get_data_usage',{'customer_id':'C1001','line_id':'L1002'})
   elif last['role']=='tool':
    prior=next(m for m in reversed(messages[:-1]) if m.get('tool_calls'))
    name=prior['tool_calls'][0]['function']['name']
    if name=='get_customer_by_phone': calls=tool('get_details_by_id',{'id':'L1002'})
    elif name=='get_details_by_id' and not any('Airplane mode is off' in (m.get('content') or '') for m in messages): text='Please turn airplane mode off.'
    elif name=='get_details_by_id': calls=tool('get_data_usage',{'customer_id':'C1001','line_id':'L1002'})
    else: text='Please set network preference to 4g_5g_preferred and run a speed test.'
   elif 'Airplane mode is off' in content: calls=tool('get_data_usage',{'customer_id':'C1001','line_id':'L1002'})
   elif 'Speed test done' in content: text='The requested troubleshooting is completed.'
   else: calls=tool('get_customer_by_phone',{'phone_number':'555-123-2002'})
  elif role=='mock-user':
   content=last.get('content') or ''
   if last['role']=='tool':
    prior=next(m for m in reversed(messages[:-1]) if m.get('tool_calls'))
    name=prior['tool_calls'][0]['function']['name']
    if name=='toggle_airplane_mode': text='Airplane mode is off; please continue.'
    elif name=='set_network_mode_preference': calls=tool('run_speed_test',{})
    else: text='Speed test done; please finish.'
   elif 'turn airplane mode off' in content: calls=tool('toggle_airplane_mode',{})
   elif '4g_5g_preferred' in content: calls=tool('set_network_mode_preference',{'mode':'4g_5g_preferred'})
   elif 'completed' in content: text='###STOP###'
   else: text='My mobile data is not working and I want excellent speed. I am John Smith, phone 555-123-2002.'
  else: raise AssertionError('Mock received a nonfixture model')
  return {'id':'mock-'+digest(payload)[:16],'choices':[{'finish_reason':'tool_calls' if calls else 'stop','message':{'role':'assistant','content':text,'tool_calls':calls}}], 'usage':None}
