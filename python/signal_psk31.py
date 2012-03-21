"""
Define a PSK31 signal type.
"""

from gnuradio import gr, digital

import ham

class Signal(object):
    
    def __init__(self):
        # Number of times we've not seen frequency in peaks.
        self.consecutive_silences = 0
        self.active = False

    def activate(self):
        self.active = True
        
    def inactivate(self):
        self.active = False


class psk31_receiver(gr.hier_block2):

    def __init__(self, samp_rate, symbol_rate=31.25):

	super(psk31_receiver, self).__init__(
            "psk31_receiver",
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
            gr.io_signature(0, 0, 1))
        self.symbol_rate = symbol_rate
	self.costas = digital.costas_loop_cc(2*3.14/100, 4)
        self.clock_recovery = digital.clock_recovery_mm_cc(
            1.0*samp_rate/symbol_rate, 0.25 * 0.1*0.1, 0.05, 0.1, 0.001)
	self.receiver = digital.constellation_receiver_cb(
            digital.constellation_bpsk().base(), 2*3.14/100, -0.25, 0.25)
	self.diff = gr.diff_decoder_bb(2)
        self.decoder = ham.psk31_decode_bb(True)
        self.msgq_out = gr.msg_queue()
	self.snk = gr.message_sink(gr.sizeof_char, self.msgq_out, True)
        self.connect(self, self.costas, self.clock_recovery,
                     self.receiver, self.diff, self.decoder, self.snk)

    def set_sample_rate(self, samp_rate):
        self.clock_recovery.set_omega(1.0*samp_rate/self.symbol_rate)
    

def msgq_to_string(q):
    """
    Returns the total string held in a message queue by
    combining messages.
    """
    all_msg = []
    while q.count() > 0:
        all_msg.append(q.delete_head().to_string())
    all_msg = ''.join(all_msg)
    # Replace carriage returns by line feeds.
    new_msg = []
    for c in all_msg:
        if ord(c) in (10, 13):
            new_msg.append('\n')
        elif (ord(c) < 32):
            new_msg.append('?')
        else:
            new_msg.append(c)
    return ''.join(new_msg)


class PSK31Signal(Signal):
    """
    Represents the section of a flow graph that receives a psk31 signal.
    """

    def __init__(self, samp_rate, freq):
        super(PSK31Signal, self).__init__()
        self.message = ''
        self.carrier_freq = freq
        self.bandwidth = 80
        self.receiver = psk31_receiver(samp_rate)
        self.samp_rate = samp_rate

    def set_sample_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.receiver.set_sample_rate(samp_rate)

    def get_message(self):
        """
        Returns the total received message so far.
        """
        self.message += msgq_to_string(self.receiver.msgq_out)
        return self.message
