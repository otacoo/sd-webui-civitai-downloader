# Shared process state and cancel flag for all long-running backend operations

PROCESS_STATE = {'running': False, 'type': None}
CANCEL_FLAG = {'cancel': False}

def is_running():
    return PROCESS_STATE['running']

def get_type():
    return PROCESS_STATE['type']

def set_running(process_type):
    PROCESS_STATE['running'] = True
    PROCESS_STATE['type'] = process_type
    CANCEL_FLAG['cancel'] = False

def clear_running():
    PROCESS_STATE['running'] = False
    PROCESS_STATE['type'] = None
    CANCEL_FLAG['cancel'] = False

def cancel_process():
    CANCEL_FLAG['cancel'] = True

def is_cancelled():
    return CANCEL_FLAG['cancel']
