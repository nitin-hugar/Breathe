from zeroconf import ServiceInfo, Zeroconf
from pymidi import server
import socket, fcntl, struct

class RtpMidi(object):
    def __init__(self, robot_name: str, handler: server.Handler, port: int = 5004):
        self.robot = robot_name
        self.port  = port
        self.handler = handler

        _TYPE = '_apple-midi._udp.local.'
        _NAME = self.robot + '.' + _TYPE
        self.conf = Zeroconf()
        self.service_info = ServiceInfo(_TYPE, _NAME, port=self.port, addresses=[socket.inet_aton(self.get_ip_address())])
        self.conf.register_service(self.service_info)

        self.server = server.Server([('192.168.2.2', self.port)])
        self.server.add_handler(self.handler)

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.2.3", 5004))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.conf.unregister_all_services()
            self.conf.close()

    
