import random, math, time, curses

import ham
from gnuradio import gr, window, digital

def get_ffted_source(src_factory, fftwidth, number_ffts=1):
    """
    Get averaged fft data for the source.

    `src_factory` is a function that generates a source block.
    `fftwidth` is the width of the fft.
    `number_ffts` is the number of ffts that should be averaged together.
    """
    tb = gr.top_block()
    src = src_factory()
    stream_to_vector = gr.stream_to_vector(gr.sizeof_float, fftwidth)
    fft = gr.fft_vfc(fftwidth, True, window.blackmanharris(fftwidth))
    vector_to_stream = gr.vector_to_stream(gr.sizeof_gr_complex, fftwidth)
    mag = gr.complex_to_mag()
    head = gr.head(gr.sizeof_float, fftwidth*number_ffts)
    snk = gr.vector_sink_f()
    tb.connect(src, stream_to_vector, fft, vector_to_stream, mag, head, snk)
    tb.run()
    data = snk.data()
    datasets = [data[fftwidth*i:fftwidth*(i+1)] for i in range(0, len(data)/fftwidth)]
    av_data = [0]*fftwidth
    for data in datasets:
        for i in range(0, fftwidth):
            av_data[i] += data[i]
    av_data = [d/len(datasets) for d in av_data]
    return av_data

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

def get_peaks(data, samp_rate, fftwidth=1000, cutoff=100):
    """
    Get the frequencies of the peaks in `data`.
    
    It looks for zero-intercepts of the smoothed first-derivative where
    the second-derivative is sufficiently large.

    """
    diff_taps = (-0.5, 0, 0.5)
    n_taps = 20
    lpf_taps = gr.firdes.low_pass_2(1, fftwidth, 80, 40, n_taps)
    data = convolve(data, diff_taps)
    data = convolve(data, lpf_taps)
    # Not sure why it is necessary to subtract 0.5 from the offset but
    # otherwise it gives an incorrect answer.
    offset = (len(diff_taps)+len(lpf_taps))/2.0 - 0.5 
    # Now find spots where it passes through 0
    cutoff = 1.0*cutoff/fftwidth
    peak_freqs = []
    for i in range(0, len(data)-1):
        if data[i] > 0 and data[i+1] < 0:
            diff = data[i] - data[i+1]
            if diff > cutoff:
                x = i + 1.0/diff*data[i]
                f = (x + 0.5 - offset)*samp_rate/len(data)
                if f > samp_rate/2:
                    f -= samp_rate
                peak_freqs.append(f)
    return peak_freqs

class psk31_topblock(gr.top_block):
    """
    A top block that takes care of psk31 receiving.
    """

    def __init__(self, src_factory, carrier_freq, symbol_rate=31.25,
                 samp_rate=44100, decim=200, slowdown=1):
        gr.top_block.__init__(self)
        self.symbol_rate = symbol_rate
        self.samp_rate = samp_rate
        self.decim = decim 
        self.carrier_freq = carrier_freq

        self.msgq_out = gr.msg_queue()

        src = src_factory()
        decoder = ham.psk31_decode_bb(True)
        null = gr.null_source(gr.sizeof_float)
        float_to_complex = gr.float_to_complex(1)
        coswave = gr.sig_source_c(self.samp_rate, gr.GR_COS_WAVE,
                                  -self.carrier_freq, 1, 0)
        multiply = gr.multiply_vcc(1)
	snk = gr.message_sink(gr.sizeof_char, self.msgq_out, True)
        midpoint = 60
        width = 20
        n_taps = 10
        taps = gr.firdes.low_pass_2(decim, samp_rate, midpoint, width, n_taps)
	lpf = gr.fft_filter_ccc(decim, taps)
	diff = gr.diff_decoder_bb(2)
	costas = digital.costas_loop_cc(2*3.14/100, 4)
	receiver = digital.constellation_receiver_cb(
            digital.constellation_bpsk().base(), 2*3.14/100, -0.25, 0.25)
        clock_recovery = digital.clock_recovery_mm_cc(
            samp_rate/decim/symbol_rate, 0.25 * 0.1*0.1, 0.05, 0.1, 0.001)
        throttle = gr.throttle(gr.sizeof_float, samp_rate/slowdown)

        self.connect(src, throttle, (float_to_complex, 0))
        self.connect(null, (float_to_complex, 1))
        self.connect(float_to_complex, (multiply, 0))
        self.connect(coswave, (multiply, 1))
        self.connect(multiply, lpf, costas, clock_recovery, receiver, diff, decoder, snk)
        self.message = ''

    def get_message(self):
        """
        Returns the total received message so far.
        """
        self.message += msgq_to_string(self.msgq_out)
        return self.message

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
        if ord(c) == 13:
            new_msg.append('\n')
        else:
            new_msg.append(c)
    return ''.join(new_msg)
    
def decode(stdscr, src_factory, samp_rate, fftwidth, cutoff, total_time=10):
    """
    Given a function that generates the source this will:
     - detect the peaks.
     - create a receiver for each.
     - write the results to the terminal (using curses module).
    """
    ffted = get_ffted_source(src_factory, fftwidth, 100)
    peak_freqs = get_peaks(ffted, samp_rate, fftwidth, cutoff)
    signals = [psk31_topblock(src_factory, freq, slowdown=1) for freq in peak_freqs]
    for s in signals:
        s.start()
    time_step = 0.1
    for i in range(0, int(total_time/time_step)):
        spacing = 4
        stdscr.erase()
        for i, s in enumerate(signals):
            stdscr.addstr(i*spacing, 0,
                          '**{0:0.2f}*****'.format(s.carrier_freq))
            m = s.get_message()
            lines = m.split('\n')
            n_lines = len(lines)
            if n_lines > spacing-2:
                m = '\n'.join(lines[n_lines-spacing+2:])
            stdscr.addstr(i*spacing+1, 0, m)
        stdscr.refresh()
        time.sleep(time_step)
    for s in signals:
        s.stop()

def make_src():
    return gr.wavfile_source('example.WAV', True) 

def start():
    """Set up curses."""
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    return stdscr

def end(stdscr):
    """Break down curses."""
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()
    
def execute(stdscr):
    samp_rate = 44100
    decode(stdscr, make_src, samp_rate, 1000, 100, total_time=100)

if __name__ == '__main__':
    stdscr = start()
    try:
        execute(stdscr)
    except:
        end(stdscr)
        raise
    end(stdscr)
