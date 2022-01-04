import isotp
import logging
import time
import threading

from can.interfaces.socketcan import SocketcanBus


isotp_timeout = 5.0
isotp_params = {
    'stmin' : 2,                                                    # Will request the sender to wait 2ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
    'blocksize' : 8,                                                # Request the sender to send 8 consecutives frames before sending a new flow control message
    'wftmax' : 0,                                                   # Number of wait frame allowed before triggering an error
    'tx_data_length' : 8,                                           # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
    'tx_data_min_length' : 8,                                       # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
    'tx_padding' : 0x00,                                            # Will pad all transmitted CAN messages with byte 0x00.
    'rx_flowcontrol_timeout' : int(isotp_timeout * 1000),           # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
    'rx_consecutive_frame_timeout' : int(isotp_timeout * 1000),     # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
    'squash_stmin_requirement' : False,                             # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
    'max_frame_size' : 4095                                         # Limit the size of receive frame.
}

class ThreadedApp:
    def __init__(self):
        self.exit_requested = False
        self.bus = SocketcanBus(channel='can0')
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=0x7E2, txid=0x7EA)
        self.stack = isotp.CanStack(self.bus, address=addr, error_handler=self.my_error_handler, params=isotp_params)

    def start(self):
        self.exit_requested = False
        self.thread = threading.Thread(target = self.thread_task)
        self.thread.start()

    def stop(self):
        self.exit_requested = True
        if self.thread.is_alive():
            self.thread.join()

    def my_error_handler(self, error):
        logging.warning('IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def thread_task(self):
        while self.exit_requested == False:
            self.stack.process()                # Non-blocking
            time.sleep(self.stack.sleep_time()) # Variable sleep time based on state machine state

    def shutdown(self):
        self.stop()
        self.bus.shutdown()

if __name__ == '__main__':
    app = ThreadedApp()
    app.start()

    print('Waiting for payload - Ctrl-C to exit')
    while True:
        try:
            if app.stack.available():
                payload = app.stack.recv()
                print("Received payload : %s" % (payload))
            time.sleep(0.2)
        except KeyboardInterrupt:
            break

    print("Exiting")
    app.shutdown()