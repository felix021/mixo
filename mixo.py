#!/usr/bin/python

import sys 
import struct
import random
import signal

try:
    import gevent
    from gevent import socket
    from gevent.server import StreamServer
    from gevent.socket import create_connection, gethostbyname
except:
    print >>sys.stderr, "please install gevent first!"
    sys.exit(1)

import config

keys = []

if config.seed:
    r = random.Random(config.seed)
    keys = [r.randint(0, 255) for i in xrange(0, 1024)]
    keys += keys
else:
    raise Exception("config.seed not set!")

try:
    import ctypes

    try:
        filename = "./xor.so"
        xor = ctypes.CDLL(filename)
    except:
        import platform
        bits, exetype = platform.architecture()
        filename = "./xor_%s_%s.so" % (exetype, bits)
        xor = ctypes.CDLL(filename)

    print >>sys.stderr, "loaded %s, using faster xor" % filename

    key_str = ''.join(map(chr, keys))

    if xor.set_xor_table(key_str, len(key_str)) == 1:
        raise Exception("set xor table failed")

    def encrypt(data, pos):
        ret = ctypes.create_string_buffer(data)
        xor.xor(ret, len(data), pos)
        return ret.raw[:-1]

except:

    print >>sys.stderr, "can't load xor.so, using python native."
    def encrypt(data, pos):
        return ''.join(map(lambda x, y: chr(ord(x) ^ y), data, keys[pos:pos+len(data)]))

decrypt = encrypt

def dumps(x):
    return ' '.join(map(lambda t: '%x' % struct.unpack('B', t)[0], x))

class XSocket(gevent.socket.socket):
    def __init__(self, socket = None, addr = None, secure = False):
        if socket is not None:
            gevent.socket.socket.__init__(self, _sock = socket)
        elif addr is not None:
            gevent.socket.socket.__init__(self)
            self.connect(addr)
        else:
            raise Exception("XSocket.init: bad arguments")

        self.secure = secure
        self.recv_idx = 0
        self.send_idx = 0

    def unpack(self, fmt, length):
        data = self.recv(length)
        if len(data) < length:
            raise Exception("XSocket.unpack: bad formatted stream")
        return struct.unpack(fmt, data)

    def pack(self, fmt, *args):
        data = struct.pack(fmt, *args)
        return self.sendall(data)

    def recv(self, length, *args):
        data = gevent.socket.socket.recv(self, length, *args)
        if config.debug: print 'Received:', dumps(data)
        if self.secure:
            data = decrypt(data, self.recv_idx)
            self.recv_idx = (self.recv_idx + len(data)) % 1024
            if config.debug: print 'Decrypted:', dumps(data), '--', data
        return data

    def sendall(self, data, flags = 0):
        if config.debug: print 'Send:', dumps(data), '--', data
        if self.secure:
            data = encrypt(data, self.send_idx)
            self.send_idx = (self.send_idx + len(data)) % 1024
            if config.debug: print 'Encrypted:', dumps(data)
        return gevent.socket.socket.sendall(self, data, flags)

    def forward(self, dest):
        try:
            while True:
                data = self.recv(1024)
                if not data:
                    break
                dest.sendall(data)
        #except IOError, e: pass
        finally:
            print 'connection closed'
            self.close()
            dest.close()


class SocksServer(StreamServer):
    def __init__(self, listener, **kwargs):
        StreamServer.__init__(self, listener, **kwargs)

    def handle(self, sock, addr):
        print 'connection from %s:%s' % addr

        src = XSocket(socket = sock, secure = True)

        #socks5 negotiation step2: specify command and destination
        ver, cmd, rsv, atype = src.unpack('BBBB', 4)

        if cmd != 0x01:
            src.pack('BBBBIH', 0x05, 0x07, 0x00, 0x01, 0, 0)
            return

        if atype == 0x01: #ipv4
            host, port = src.unpack('!IH', 6)
            hostip = socket.inet_ntoa(struct.pack('!I', host))
        elif atype == 0x03: #domain name
            length = src.unpack('B', 1)[0]
            hostname, port = src.unpack("!%dsH" % length, length + 2)
            hostip = gethostbyname(hostname)
            host = struct.unpack("!I", socket.inet_aton(hostip))[0]
        elif atype == 0x04: #ipv6: TODO
            src.pack('!BBBBIH', 0x05, 0x07, 0x00, 0x01, 0, 0)
            return
        else:
            src.pack('!BBBBIH', 0x05, 0x07, 0x00, 0x01, 0, 0)
            return

        try:
            dest = XSocket(addr = (hostip, port))
        except IOError, ex:
            print "%s:%d" % addr, "failed to connect to %s:%d" % (hostip, port)
            src.pack('!BBBBIH', 0x05, 0x03, 0x00, 0x01, host, port)
            return

        src.pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, host, port)

        gevent.spawn(src.forward, dest)
        gevent.spawn(dest.forward, src)

    def close(self):
        sys.exit(0)

    @staticmethod
    def start_server():
        server = SocksServer(('0.0.0.0', config.server_port))
        gevent.signal(signal.SIGTERM, server.close)
        gevent.signal(signal.SIGINT, server.close)
        print "Server is listening on 0.0.0.0:%d" % config.server_port
        server.serve_forever()


class PortForwarder(StreamServer):
    def __init__(self, listener, dest, **kwargs):
        StreamServer.__init__(self, listener, **kwargs)
        self.destaddr = dest

    def handle(self, sock, addr):

        src = XSocket(socket = sock)

        #socks5 negotiation step1: choose an authentication method
        ver, n_method = src.unpack('BB', 2) 

        if ver != 0x05:
            src.pack('BB', 0x05, 0xff)
            return

        if n_method > 0:
            src.recv(n_method)
        
        src.pack('!BB', 0x05, 0x00) #0x00 means no authentication needed

        print "Forwarder: connection from %s:%d" % addr
        try:
            dest = XSocket(addr = self.destaddr, secure = True)
        except IOError, ex:
            print "%s:%d" % addr, "failed to connect to SocksServer %s:%d" % self.destaddr
            print ex
            return
        gevent.spawn(src.forward, dest)
        gevent.spawn(dest.forward, src)

    def close(self):
        sys.exit(0)

    @staticmethod
    def start_server():
        forward_addr = (config.forward_host, config.forward_port)
        server_addr  = (config.server_host, config.server_port)
        server = PortForwarder(forward_addr, server_addr)

        gevent.signal(signal.SIGTERM, server.close)
        gevent.signal(signal.SIGINT, server.close)
        print "Forwarder is listening on %s:%d for Server %s:%d" % \
                (config.forward_host, config.forward_port, \
                 config.server_host, config.server_port)
        server.serve_forever()

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        PortForwarder.start_server()
    else:
        SocksServer.start_server()
