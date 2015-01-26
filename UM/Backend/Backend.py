from UM.Backend.SignalSocket import SignalSocket
from UM.Preferences import Preferences
from UM.Logger import Logger
from UM.Signal import Signal, SignalEmitter

import struct
import subprocess
from time import sleep


##      Base class for any backend communication (seperate piece of software).
#       It makes use of the Socket class from libArcus for the actual communication bits.
#       The message_handler dict should be filled with message class, function pairs.
class Backend(SignalEmitter):
    def __init__(self,):
        super().__init__() # Call super to make multiple inheritence work.
        self._supported_commands = {}

        self._message_handlers = {}

        self._socket = SignalSocket()
        self._socket.stateChanged.connect(self._onSocketStateChanged)
        self._socket.messageReceived.connect(self._onMessageReceived)
        self._socket.error.connect(self._onSocketError)

        self._socket.listen('127.0.0.1', 0xC20A)

        self._process = None

    processingProgress = Signal()
    
    ##   \brief Start the backend / engine.
    #   Runs the engine, this is only called when the socket is fully opend & ready to accept connections
    def startEngine(self):
        try:
            self._process = self._runEngineProcess(self.getEngineCommand())
        except FileNotFoundError as e:
            Logger.log('e', "Unable to find backend executable")
    
    ##  \brief Convert byte array containing 3 floats per vertex
    def convertBytesToVerticeList(self, data):
        result = []
        if not (len(data) % 12):
            if data is not None:
                for index in range(0,int(len(data)/12)): #For each 12 bits (3 floats)
                    result.append(struct.unpack('fff',data[index*12:index*12+12]))
                return result
        else:
            Logger.log('e', "Data length was incorrect for requested type")
            return None
    
    ##  \brief Convert byte array containing 6 floats per vertex
    def convertBytesToVerticeWithNormalsList(self,data):
        result = []
        if not (len(data) % 24):
            if data is not None:
                for index in range(0,int(len(data)/24)): #For each 24 bits (6 floats)
                    result.append(struct.unpack('ffffff',data[index*24:index*24+24]))
                return result
        else:
            Logger.log('e', "Data length was incorrect for requested type")
            return None

    def getEngineCommand(self):
        return [Preferences.getPreference("BackendLocation"), '--port', str(self._socket_thread.getPort())]

    ## \brief Start the (external) backend process.
    def _runEngineProcess(self, command_list):
        kwargs = {}
        if subprocess.mswindows:
            su = subprocess.STARTUPINFO()
            su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            su.wShowWindow = subprocess.SW_HIDE
            kwargs['startupinfo'] = su
            kwargs['creationflags'] = 0x00004000 #BELOW_NORMAL_PRIORITY_CLASS
        return subprocess.Popen(command_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

    def _onSocketStateChanged(self, state):
        if state == SignalSocket.ListeningState:
            #self.startEngine()
            pass
        elif state == SignalSocket.ConnectedState:
            print('Socket connected')

    def _onMessageReceived(self):
        message = self._socket.takeNextMessage()

        if type(message) not in self._message_handlers:
            Logger.log('e', "No handler defined for message of type %s", type(message))
            return

        self._message_handlers[type(message)](message)

    def _onSocketError(self, error):
        Logger.log('e', str(error))
