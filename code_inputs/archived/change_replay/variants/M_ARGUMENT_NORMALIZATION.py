from copy import deepcopy

def system_prompt():
    return "Use tools to satisfy the user. Preserve exact values. Finish only when complete."

def normalize_arguments(arguments):
    def lower(value):
        if isinstance(value, str):
            return value.casefold()
        if isinstance(value, list):
            return [lower(item) for item in value]
        if isinstance(value, dict):
            return {key: lower(item) for key, item in value.items()}
        return value
    return lower(deepcopy(arguments))

def prepare_observation(observation):
    return deepcopy(observation)

def retry_arguments(tool, arguments, observation, attempt):
    if attempt == 0 and observation.get("transient") is True and (tool != "write" or "idempotency_key" in arguments):
        return deepcopy(arguments)
    return None

def should_terminate(tool, observation):
    return False
