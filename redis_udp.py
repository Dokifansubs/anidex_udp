from socket import inet_aton, inet_ntoa
import SocketServer
from struct import *
# import sys
import random
# import pdb
import redis
import itertools
import time

def ip2int(addr):
    return unpack('!I', inet_aton(addr))[0]


def int2ip(addr):
    return inet_ntoa(pack('!I', addr))

r = redis.Redis(unix_socket_path='/tmp/redis.sock')


class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request[0]
        req_socket = self.request[1]
        # print '%s: %d: %s' % (self.client_address[0], len(data), str([ord(c) for c in data]))
        if len(data) >= 16:
            con_id, action, trans_id = unpack_from('!Qii', data)
            response = pack('!ii5s', 3, trans_id, 'error')
            # print unpack_from('!qii', data)
            # The connect (need to redo)
            if action == 0 and con_id == 0x41727101980:
                while True:
                    con_id = random.getrandbits(63)
                    if con_id != 0x41727101980:
                        break
                response = pack('!iiQ', action, trans_id, con_id)
            # Announce
            elif action == 1 and len(data) >= 98:
                info_hash, peer_id, downloaded, left, uploaded, event, ip, key, num_want, port = unpack_from('!20s20sqqqiIiiH', data, 16)
                # print '%s: announce %s' % self.client_address, unpack_from('!20s20sqqqiIiiH', data, 16)
                info_hash = info_hash.encode('hex')
                seed_key = info_hash + ':1'
                leech_key = info_hash + ':0'
                completed = seed_key if event == 1 or left == 0 else leech_key
                # Send a max of 200 (MTU is like ~1400-1500 bytes)
                num_want = min(200, num_want) if num_want >= 0 else 200
                # Deafult ip
                ip = ip2int(self.client_address[0]) if ip == 0 else ip
                # default port?
                port = self.client_address[1] if port == 0 else port
                # Contact every 10 mins
                interval = 600

                timenow = int(time.time())
                # Aggregate the leechers and seeders and add this one to the list
                pipe = r.pipeline(transaction=False)
                # expire old keys
                pipe.zremrangebyscore(leech_key, 0, timenow - interval)
                pipe.zremrangebyscore(seed_key, 0, timenow - interval)
                # get counts
                pipe.zcard(leech_key)
                pipe.zcard(seed_key)
                # for some reason it is key, max, min to get lastest num_want of each
                pipe.zrevrangebyscore(leech_key, timenow, timenow - interval, 0, num_want)
                pipe.zrevrangebyscore(seed_key, timenow, timenow - interval, 0, num_want)
                # add / update peer if not a stop event
                if event != 3:
                    pipe.zadd(completed, pack('!IH', ip, port), timenow)
                resp = pipe.execute()
                # get my counts
                leechers = resp[2]
                seeders = resp[3]
                # Prepare response
                ips_ports = [pack('!iiiii', 1, trans_id, interval, leechers, seeders)]
                # concat 2 lists to make a new list for shuffling
                resp[4] += resp[5]
                limit = min(num_want, len(resp[4]))
                ips_ports.extend( random.sample(resp[4], limit) )
                # join all the stuff!
                response = ''.join(ips_ports)
            # The scrape
            elif action == 2:
                num = (len(data) - 16) / 20
                # start building the response
                scrape = [pack('!ii', 2, trans_id)]
                pipe = r.pipeline(transaction=False)
                for i in xrange(num):
                    info_hash = unpack_from('!20s', data, 16 + 20 * i)[0].encode('hex')
                    seed_key = info_hash + ':1'
                    leech_key = info_hash + ':0'
                    pipe.zcard(seed_key)
                    pipe.zcard(leech_key)
                    # 0 for # of torrent downloads (for now)
                iterat = iter(pipe.execute())
                pairs = itertools.izip(iterat, iterat)
                scrape.extend( (pack('!iii', seeders, 0, leechers) for seeders,leechers in pairs) )
                response = ''.join(scrape)
            # print '%d: %s' % (len(response), str([hex(ord(c)) for c in response]))
            # print '\n'
            # sys.stdout.flush()
            req_socket.sendto(response, self.client_address)

if __name__ == '__main__':
    HOST, PORT = '', 6969
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()

