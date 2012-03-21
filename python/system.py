from gnuradio import gr

class System(object):
    """
    Create an object wrapping the top block of the flow graph.
    
    Args:
        tb - The top block of the flow graph.
        src - The source block.
        samp_rate - The sample rate of the src block.
        throttle - Whether to apply a throttle.
        src_is_float - Whether src produces floats.
    """

    def __init__(self, tb, src, samp_rate, throttle=False, src_is_float=False,
                 center_freq=0):
        self.center_freq = center_freq
        self.tb = tb
        self.src = src
        self.samp_rate = samp_rate
        if src_is_float:
            self.null = gr.null_source(gr.sizeof_float)
            self.float_to_complex = gr.float_to_complex(1)
            self.tb.connect(self.null, (self.float_to_complex, 0))
            self.tb.connect(self.src, (self.float_to_complex, 1))
            self.out = self.float_to_complex
        else:
            self.out = self.src
        if throttle:
            self.throttle = gr.throttle(gr.sizeof_gr_complex, samp_rate)
            self.tb.connect(self.out, self.throttle)
            self.out = self.throttle
        null = gr.null_sink(gr.sizeof_gr_complex)
        self.tb.connect(self.out, null)
        self.command_queue = []

    def connect(self, *args, **kwargs):
        self.command_queue.append(('connect', args, kwargs))
        
    def disconnect(self, *args, **kwargs):
        self.command_queue.append(('disconnect', args, kwargs))

    def refresh(self):
        self.lock()
        while self.command_queue:
            command, args, kwargs = self.command_queue.pop(0)
            if command == 'connect':
                self.tb.connect(*args, **kwargs)
            elif command == 'disconnect':
                self.tb.disconnect(*args, **kwargs)
            else:
                raise ValueError("Unrecognised command {0}.".format(command))
        self.unlock()
        
    def lock(self):
        self.tb.lock()
        
    def unlock(self):
        self.tb.unlock()

    def stop(self):
        self.tb.stop()
        
    def start(self):
        self.tb.start()
