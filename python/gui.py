import logging

from PyQt4 import QtGui

class SignalWidget(QtGui.QFrame):

    def __init__(self, freq, initial_text):
        super(SignalWidget, self).__init__()
        self.setFrameStyle(QtGui.QFrame.Box)
        self.initUI(freq, initial_text)

    def initUI(self, freq, initial_text):
        self.vbox = QtGui.QVBoxLayout()
        self.freq_label = QtGui.QLabel(str(freq), self)
        self.text_label = QtGui.QLabel(initial_text, self)
        self.setLayout(self.vbox)
        self.vbox.addWidget(self.freq_label) 
        self.vbox.addWidget(self.text_label) 

    def update_message(self, text):
        self.text_label.setText(text)

class PSK31QWidget(QtGui.QWidget):

    def __init__(self):
        super(PSK31QWidget, self).__init__()
        self.initUI()

    def initUI(self):
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)
        self.signal_widgets = {}
        self.show()

    def add_signal(self, signal):
        sw = SignalWidget(signal.carrier_freq, signal.get_message())
        self.signal_widgets[signal] = sw
        self.vbox.addWidget(sw) 

    def remove_stream(self, signal):
        if signal in self.signal_widgets:
            sw = self.signal_widgets[signal]
            self.vbox.removeWidget(sw)         

    def update(self, signals):
        for signal in signals:
            sw = self.signal_widgets.get(signal, None)
            if sw is None:
                self.add_signal(signal)
            else:
                sw.update_message(signal.get_message())

