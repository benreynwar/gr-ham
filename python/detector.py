"""
Defines Detector objects that take care of signal detection and classification.
"""

import logging

from gnuradio import gr, window

from multi.signal_psk31 import PSK31Signal

logger = logging.getLogger(__name__)

def mag(c):
    """Magnitude of complex number."""
    return (c*c.conjugate()).real

def convolve(data, taps):
    """
    Convolves `data` and `taps` together.
    """
    N = len(data)
    data = [0]*(len(taps)-1) + list(data)
    new_data = []
    for i in range(0, N):
        value = 0
        for j in range(0, len(taps)):
            value += taps[j]*data[i+j]
        new_data.append(value)
    return new_data

class Detector(object):
    
    def __init__(self, system, fftwidth=256, n=128, cutoff=100):
        """
        Add blocks to the top_blocks that will be used for extracting the fft
        from the flow graph for detection.

        Args:
            system: A wrapper for the top block.
            fftwidth: The width of the fft used for detection.
            n: The fft is only updated every 1 in n times.
            cutoff: How sharp peaks need to be, to be detected.
        """
        self.system = system
        self.fftwidth = fftwidth
        self.n = n
        self.cutoff = cutoff
        self.stream_to_vector = gr.stream_to_vector(gr.sizeof_gr_complex, fftwidth)
        self.keep_one_in_n = gr.keep_one_in_n(gr.sizeof_gr_complex*fftwidth, n) 
        self.fft = gr.fft_vcc(fftwidth, True, window.blackmanharris(fftwidth))
        self.probe = gr.probe_signal_vc(fftwidth)
        system.connect(system.out, self.stream_to_vector, self.keep_one_in_n,
                       self.fft, self.probe)

    def get_fft(self):
        """
        Return the fft.
        """
        return [mag(x) for x in self.probe.level()]

    def get_peaks(self):
        """
        Get the frequencies of the peaks.

        It looks for zero-intercepts of the smoothed first-derivative where
        the second-derivative is sufficiently large.

        """
        data = self.get_fft()
        samp_rate = self.system.samp_rate
        center_freq = self.system.center_freq
        diff_taps = (-0.5, 0, 0.5)
        fftwidth = 1000
        n_taps = 20
        lpf_taps = gr.firdes.low_pass_2(1, fftwidth, 80, 40, n_taps)
        data = convolve(data, diff_taps)
        data = convolve(data, lpf_taps)
        # Not sure why it is necessary to subtract 0.5 from the offset but
        # otherwise it gives an incorrect answer.
        offset = (len(diff_taps)+len(lpf_taps))/2.0 - 0.5 
        # Now find spots where it passes through 0
        cutoff = 1.0*self.cutoff/fftwidth
        peak_freqs = []
        for i in range(0, len(data)-1):
            if data[i] > 0 and data[i+1] < 0:
                diff = data[i] - data[i+1]
                if diff > cutoff:
                    x = i + 1.0/diff*data[i]
                    f = (x + 0.5 - offset)*samp_rate/len(data)
                    if f > samp_rate/2:
                        f -= samp_rate
                    f += center_freq
                    peak_freqs.append(f)
        return peak_freqs

    def scan(self, signals, freq_range=None):
        """
        Update the signals within the freq_range.
        """
        freqs = self.get_peaks()
        # How close in frequency two peaks need to be for us to
        # consider them to be one signal.
        delta_freq = 50
        # How many times we can fail to detect a signal before it is
        # declared inactive.
        consec_silences = 5
        found_signals = []
        new_freqs = []
        for freq in freqs:
            found = False
            for signal in signals:
                if abs(freq - signal.carrier_freq) < delta_freq:
                    found_signals.append(signal)
                    found = True
                    break
            if not found:
                new_freqs.append(freq)
        silent_signals = list(set(signals) - set(found_signals))
        for s in silent_signals:
            s.consecutive_silences += 1
            if s.consecutive_silences > consec_silences:
                if s.active:
                    s.inactivate()
        for s in found_signals:
            s.consecutive_silences = 0
            if not s.active:
                logger.debug("Reactivating signal with freq {0}.".format(signal.carrier_freq))
                s.activate()
        # We assume everything is a PSK31 signal at the moment.
        new_signals = [PSK31Signal(self.system.samp_rate, freq)
                       for freq in new_freqs]
        for s in new_signals:
            s.activate()
        return signals + new_signals   
