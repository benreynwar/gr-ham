from PyQt4 import QtGui, QtCore

from gnuradio import gr

from ham.gui import PSK31QWidget
from ham.system import System
from ham.detector import Detector
from ham.channelizer import Channelizer

class App():
    def __init__(self):
        tb = gr.top_block()
        src = gr.wavfile_source('example.WAV', True)
        samp_rate = 44100
        self.system = System(tb, src, samp_rate, throttle=True, src_is_float=True,
                        center_freq=0)
        self.detector = Detector(self.system)
        self.channelizer = Channelizer(self.system)
        self.app = QtGui.QApplication([])
        self.widget = PSK31QWidget()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.signals = []
        
    def run(self):
        self.system.start()
        self.update()
        self.timer.start(1000)
        self.app.exec_()

    def update(self):
        self.signals = self.detector.scan(self.signals)
        self.channelizer.update_signals(self.signals)
        self.system.refresh()
        self.widget.update(self.signals)

if __name__ == '__main__':
    app = App()
    app.run()
