"""
Defines a channelizer object that is responsible for getting the 
required freqency ranges and connecting them to the signals.
"""

import logging

from gnuradio import gr

logger = logging.getLogger(__name__)

class Channelizer(object):
    
    def __init__(self, system):
        self.system = system
        self.connected_signals = set([])
        self.linkers = {}
        
    def update_signals(self, signals):
        for signal in signals:
            if signal.active and signal not in self.connected_signals:
                if signal in self.linkers:
                    linker = self.linkers[signal]
                else:
                    linker = Linker(signal.carrier_freq, signal.bandwidth, self.system.samp_rate)
                    self.linkers[signal] = linker
                    signal.set_sample_rate(linker.samp_rate)
                logger.debug("New freq at {0}".format(signal.carrier_freq))
                self.system.connect(self.system.out, linker, signal.receiver)
                self.connected_signals.add(signal)
            elif not signal.active and signal in self.connected_signals:
                logger.debug("Turn off freq at {0}".format(signal.carrier_freq))
                self.system.disconnect(self.system.out, self.linkers[signal])
                self.system.disconnect(self.linkers[signal], signal.receiver)
                self.connected_signals.remove(signal)

class Linker(gr.hier_block2):
    def __init__(self, center_freq, bandwidth, samp_rate):
        gr.hier_block2.__init__(self, "linker",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),
                                gr.io_signature(1, 1, gr.sizeof_gr_complex))
        self.coswave = gr.sig_source_c(samp_rate, gr.GR_COS_WAVE,
                                       -center_freq, 1, 0)
        self.multiply = gr.multiply_vcc(1)
        midpoint = bandwidth
        width = 20
        stopband_attenuation = 10
        decim = int(samp_rate / bandwidth / 4)
        taps = gr.firdes.low_pass_2(decim, samp_rate, midpoint, width,
                                    stopband_attenuation)
        self.lpf = gr.fft_filter_ccc(decim, taps)
        self.connect(self, (self.multiply, 0))
        self.connect(self.coswave, (self.multiply, 1))
        self.connect(self.multiply, self.lpf, self)
        self.samp_rate = 1.0*samp_rate/decim

def qa_linker():
    import time
    from gnuradio import window
    from system import System
    from signal_psk31 import PSK31Signal

    def mag(c):
        """Magnitude of complex number."""
        return (c*c.conjugate()).real

    src = gr.wavfile_source("../example.WAV", False)
    samp_rate = 44100
    tb = gr.top_block()
    system = System(tb, src, samp_rate, throttle=False, src_is_float=True,
                    center_freq=0)
    linker = Linker(1000, 80, samp_rate)
    snk = gr.null_sink(gr.sizeof_gr_complex)
    system.connect(system.out, linker, snk)
    system.refresh()
    system.start()
    time.sleep(5)
    system.stop()
    data = linker.probe.level()
    print(data[:10])
    print(linker.samp_rate)
    plot_fft([mag(x) for x in data], linker.samp_rate)

def plot_fft(data, samp_rate):
    import math
    scale = samp_rate/len(data)
    xs = [(-len(data)/2.0 + 0.5 + i)*scale for i in range(0, len(data))]
    switch = int(math.ceil(len(data)/2.0))
    ys = data[switch:] + data[:switch]
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot
    fig = pyplot.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, ys)
    ax.set_yscale('log')
    fig.savefig('deleteme.png')

if __name__ == '__main__':
    qa_linker()

