import random, math, time, curses

import ham
from gnuradio import gr, window, digital, audio

def get_ffted_source(src, fftwidth, number_ffts=1):
    """
    Get averaged fft data for the source.

    `src` is the source block.
    `fftwidth` is the width of the fft.
    `number_ffts` is the number of ffts that should be averaged together.
    """
    tb = gr.top_block()
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

class psk31_stream(object):
    """
    Represents the section of a flow graph that receives a psk31 signal.
    """

    def __init__(self, tb, carrier_freq, samp_rate, symbol_rate=31.25, decim=200):
        self.tb = tb
        self.carrier_freq = carrier_freq
        self.symbol_rate = symbol_rate
        self.decim = decim
        self.samp_rate = samp_rate

        self.msgq_out = gr.msg_queue()
        self.decoder = ham.psk31_decode_bb(True)
        self.null = gr.null_source(gr.sizeof_float)
        self.float_to_complex = gr.float_to_complex(1)
        self.coswave = gr.sig_source_c(self.samp_rate, gr.GR_COS_WAVE,
                                  -self.carrier_freq, 1, 0)
        self.multiply = gr.multiply_vcc(1)
	self.snk = gr.message_sink(gr.sizeof_char, self.msgq_out, True)
        midpoint = 60
        width = 20
        n_taps = 10
        taps = gr.firdes.low_pass_2(decim, samp_rate, midpoint, width, n_taps)
	self.lpf = gr.fft_filter_ccc(decim, taps)
	self.diff = gr.diff_decoder_bb(2)
	self.costas = digital.costas_loop_cc(2*3.14/100, 4)
	self.receiver = digital.constellation_receiver_cb(
            digital.constellation_bpsk().base(), 2*3.14/100, -0.25, 0.25)
        self.clock_recovery = digital.clock_recovery_mm_cc(
            samp_rate/decim/symbol_rate, 0.25 * 0.1*0.1, 0.05, 0.1, 0.001)
        self.message = ''
        self.tb.connect(self.null, (self.float_to_complex, 1))
        self.tb.connect(self.float_to_complex, (self.multiply, 0))
        self.tb.connect(self.coswave, (self.multiply, 1))
        self.tb.connect(self.multiply, self.lpf, self.costas, self.clock_recovery,
                   self.receiver, self.diff, self.decoder, self.snk)
        # Number of times we've not seen frequency in peaks.
        self.consecutive_silences = 0
        self.active = False

    def connect(self):
        """Connect this section into the top block."""
        self.tb.connect(self.tb.src, (self.float_to_complex, 0))
        self.active = True
        
    def disconnect(self):
        """Disconnect this section into the top block."""
        self.tb.disconnect(self.tb.src, (self.float_to_complex, 0))
        self.active = False

    def get_message(self):
        """
        Returns the total received message so far.
        """
        self.message += msgq_to_string(self.msgq_out)
        return self.message

class psk31_topblock(gr.top_block):
    """
    A top block that just sets up the source.
    psk31_stream objects make the rest of the connections.
    """

    def __init__(self, src, throttle=None):
        gr.top_block.__init__(self)
        if throttle is None:
            self.src = src
        else:
            self.real_src = src
            self.src = throttle
            self.connect(src, throttle)

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

def update_steams(freqs, streams, tb, samp_rate):
    """
    Connect, disconnect and create new psk31 streams based on
    the observed peak frequencies.
    """
    delta_freq = 20
    consec_silences = 5
    found_streams = []
    new_freqs = []
    for freq in freqs:
        found = False
        for stream in streams:
            if abs(freq - stream.carrier_freq) < delta_freq:
                found_streams.append(stream)
                found = True
                break
        if not found:
            new_freqs.append(freq)
    silent_streams = list(set(streams) - set(found_streams))
    for s in silent_streams:
        s.consecutive_silences += 1
        if s.consecutive_silences > consec_silences:
            s.disconnect()
    for s in found_streams:
        s.consecutive_silences = 0
        if not s.active:
            s.connect()
    new_streams = [psk31_stream(tb, freq, samp_rate) for freq in new_freqs]
    for s in new_streams:
        s.connect()
    return streams + new_streams
        
    
def decode(stdscr, src, samp_rate, fftwidth, cutoff, total_time=10, time_step=0.1, scan_time=1):
    """
    Given a function that generates the source this will:
     - detect the peaks.
     - create a receiver for each.
     - write the results to the terminal (using curses module).
    """
    ffted = get_ffted_source(src, fftwidth, 100)
    peak_freqs = get_peaks(ffted, samp_rate, fftwidth, cutoff)
    tb = psk31_topblock(src)
    streams = []
    streams = update_steams(peak_freqs, streams, tb, samp_rate)
    tb.start()
    scan_steps = int(scan_time/time_step)
    for t in range(0, int(total_time/time_step)):
        #if (t+1) % scan_steps == 0:
        #    # Need calculation of peak freqs here
        #    tb.lock()
        #    streams = update_steams(peak_freqs, streams, tb, samp_rate)
        #    tb.unlock()
        spacing = 4
        stdscr.erase()
        for i, s in enumerate(streams):
            stdscr.addstr(0, 0, str(t*time_step))
            stdscr.addstr(i*spacing+1, 0,
                          '**{0:0.2f}*****'.format(s.carrier_freq))
            m = s.get_message()
            lines = m.split('\n')
            n_lines = len(lines)
            if n_lines > spacing-2:
                m = '\n'.join(lines[n_lines-spacing+2:])
            stdscr.addstr(i*spacing+2, 0, m)
        stdscr.refresh()
        time.sleep(time_step)
    tb.stop()

class fake_stdscr(object):
    """
    A fake stdscr object for debugging.
    (curses is a pain to debug with).
    """
    def addstr(self, x, y, text):
        print(text)
    def erase(self):
        print('-----------------')
    def refresh(self):
        pass

def start(fake=False):
    """
    Set up curses.
    If `fake` is True then it doesn't really use curses. 
    """
    if fake:
        stdscr = fake_stdscr()
    else:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
    return stdscr

def end(stdscr, fake=False):
    """Break down curses."""
    if not fake:
        curses.nocbreak()
        stdscr.keypad(0)
        curses.echo()
        curses.endwin()
    
def execute(stdscr):
    samp_rate = 44100
    #src = audio.source(44100, "", True)
    src = gr.wavfile_source("example2.wav", False)
    decode(stdscr, src, samp_rate, 1000, 100, total_time=10, time_step=1)

if __name__ == '__main__':
    fake = False
    stdscr = start(fake)
    try:
        execute(stdscr)
    except:
        end(stdscr, fake)
        raise
    end(stdscr, fake)
