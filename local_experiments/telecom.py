"""Per-instance defaults around the pinned Telecom factory; upstream bytes unchanged."""
from tau2.domains.telecom.environment import get_environment as upstream_environment
from tau2.domains.telecom.user_data_model import VpnDetails,PerformanceLevel,NetworkModePreference
from tau2.registry import registry
from tau2.evaluator.evaluator import evaluate_simulation,EvaluationType

EVALUATION_DOMAIN='local-experiments-isolated-telecom'

def get_environment(**kwargs):
 env=upstream_environment(**kwargs)
 # Do not copy the class attribute: another upstream instance may already have
 # mutated it. These are the defaults in the hash-pinned upstream source.
 env.user_tools.default_vpn_details=VpnDetails(server_address='192.168.1.1',protocol='OpenVPN',server_performance=PerformanceLevel.EXCELLENT)
 env.user_tools.network_mode_preference=NetworkModePreference.FOUR_G_5G_PREFERRED
 return env

# The official evaluator creates tool-schema, predicted and gold environments
# via its registry. A dedicated domain routes all three through this factory,
# without replacing the upstream telecom entry or any global class default.
registry.register_domain(get_environment,name=EVALUATION_DOMAIN)

def evaluate_official(simulation,task):
 return evaluate_simulation(simulation,task,EvaluationType.ALL,False,EVALUATION_DOMAIN,strict_replay=True)
