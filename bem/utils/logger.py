import logging
from collections import deque

# ERC Logger grabber
class TailLogHandler(logging.Handler):
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.append(self.format(record))


class TailLogger(object):
    def __init__(self, maxlen):
        self._log_queue = deque(maxlen=maxlen)
        self._log_handler = TailLogHandler(self._log_queue)

    def contents(self):
        return '\n'.join(self._log_queue)

    @property
    def log_handler(self):
        return self._log_handler


def ERC_logger():
    erc = logging.getLogger('ERC_Logger')
    tail = TailLogger(10)
    log_handler = tail.log_handler
    for handler in erc.handlers[:]:
        erc.removeHandler(handler)

    erc.addHandler(log_handler)

    return tail


def block_definition(block, args, kwargs):
    # Aggregate block definition for logging
    definition = []
    def print_value(value):
        if isinstance(value, list):
           return ' '.join(value)
        else:
           return str(value)

    mods = ', '.join([key + ' = ' + print_value(value) for key, value in block.mods.items()])
    props = ', '.join([key + ' = ' + print_value(value) for key, value in block.props.items()])
    args = ', '.join([key + ' = ' + str(value) for key, value in kwargs.items()])
    # models = ', '.join([str(model) for model in block.models])
    # classes = ', '.join([str(model) for model in block.classes])

    if mods:
        definition.append('mods: ' + mods)

    if props:
        definition.append('props: ' + props)

    if args:
        definition.append(args)

    # if models:
    #    definition.append(models)

    # if classes:
    #    definition.append(classes)

    return ' | '.join(definition)
