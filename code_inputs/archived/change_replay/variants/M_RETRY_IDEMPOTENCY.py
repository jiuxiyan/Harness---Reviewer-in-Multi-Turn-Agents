from copy import deepcopy

def system_prompt():
    return "Use tools to satisfy the user. Preserve exact values. Finish only when complete."

def normalize_arguments(arguments):
    return deepcopy(arguments)

def prepare_observation(observation):
    return deepcopy(observation)

def retry_arguments(tool, arguments, observation, attempt):
    if attempt == 0 and observation.get("error"):
        retried = deepcopy(arguments)
        if tool == "write":
            retried.pop("idempotency_key", None)
        return retried
    return None

def should_terminate(tool, observation):
    return False
