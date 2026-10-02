#!/usr/bin/env python3
"""Loopback-only Kit UDP relay over SSH, with an explicit lifetime policy."""
import argparse
import json
import selectors
import signal
import socket
import struct
import time

HEADER = struct.Struct('!HH')  # Browser UDP source port, datagram length.
MAX_DATAGRAM = 65507
MAX_BUFFER = 8 * 1024 * 1024
MAX_PEERS = 8
UDP_PORT = 47998
TCP_PORT = 47999


def frames(buffer):
    while len(buffer) >= HEADER.size:
        port, length = HEADER.unpack_from(buffer)
        if not port or not 0 < length <= MAX_DATAGRAM:
            raise ValueError('invalid frame header')
        if len(buffer) < HEADER.size + length:
            return
        payload = bytes(buffer[HEADER.size:HEADER.size + length])
        del buffer[:HEADER.size + length]
        yield port, payload


def report(event, **fields):
    print(json.dumps(dict(epoch=time.time(), event=event, **fields)), flush=True)


def relay(connection, mode, deadline):
    connection.setblocking(False)
    connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    selector = selectors.DefaultSelector()
    selector.register(connection, selectors.EVENT_READ, 'tcp')
    peers, incoming, outgoing = {}, bytearray(), bytearray()
    udp = None
    counts = dict(udp_received=0, udp_sent=0, bytes_received=0, bytes_sent=0)
    last_report = time.monotonic()
    partial_since = None
    if mode == 'client':
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('127.0.0.1', UDP_PORT))
        udp.setblocking(False)
        selector.register(udp, selectors.EVENT_READ, 'udp')
    report('connected', mode=mode, deadline=deadline)
    try:
        while deadline is None or time.time() < deadline:
            timeout = .5 if deadline is None else min(.5, max(0, deadline - time.time()))
            for key, events in selector.select(timeout):
                if key.data == 'tcp':
                    if events & selectors.EVENT_READ:
                        chunk = connection.recv(131072)
                        if not chunk:
                            if incoming:
                                raise ValueError('EOF inside frame')
                            return
                        incoming.extend(chunk)
                        if len(incoming) > MAX_BUFFER:
                            raise ValueError('receive queue exceeded limit')
                        for port, payload in frames(incoming):
                            if mode == 'server':
                                if port not in peers:
                                    if len(peers) >= MAX_PEERS:
                                        raise ValueError('peer limit exceeded')
                                    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                    peer.bind(('127.0.0.1', 0))
                                    peer.connect(('127.0.0.1', UDP_PORT))
                                    peer.setblocking(False)
                                    peers[port] = [peer, time.monotonic()]
                                    selector.register(peer, selectors.EVENT_READ, port)
                                peers[port][0].send(payload)
                                peers[port][1] = time.monotonic()
                            elif port in peers:
                                udp.sendto(payload, ('127.0.0.1', port))
                            else:
                                raise ValueError('unknown browser port')
                            counts['udp_sent'] += 1
                            counts['bytes_sent'] += len(payload)
                        # Bound an incomplete frame's idle time, not a continuous
                        # stream of valid datagrams that happens to split at every read.
                        partial_since = time.monotonic() if incoming else None
                    if events & selectors.EVENT_WRITE and outgoing:
                        sent = connection.send(outgoing)
                        del outgoing[:sent]
                else:
                    try:
                        payload, address = key.fileobj.recvfrom(MAX_DATAGRAM + 1)
                    except ConnectionRefusedError:
                        continue  # Kit has not bound UDP yet, or is reconnecting.
                    if not payload or len(payload) > MAX_DATAGRAM:
                        raise ValueError('invalid datagram length')
                    if mode == 'client':
                        if address[0] != '127.0.0.1':
                            continue
                        port = address[1]
                        if port not in peers and len(peers) >= MAX_PEERS:
                            raise ValueError('peer limit exceeded')
                        peers[port] = [None, time.monotonic()]
                    else:
                        port = key.data
                        peers[port][1] = time.monotonic()
                    outgoing.extend(HEADER.pack(port, len(payload)) + payload)
                    if len(outgoing) > MAX_BUFFER:
                        raise ValueError('send queue exceeded limit')
                    counts['udp_received'] += 1
                    counts['bytes_received'] += len(payload)
            selector.modify(connection, selectors.EVENT_READ | (selectors.EVENT_WRITE if outgoing else 0), 'tcp')
            now = time.monotonic()
            if partial_since is not None and now - partial_since > 5:
                raise TimeoutError('incomplete frame exceeded five seconds')
            for port, (peer, activity) in list(peers.items()):
                if now - activity > 60:
                    if peer is not None:
                        selector.unregister(peer)
                        peer.close()
                    del peers[port]
            if now - last_report >= 30:
                report('counters', mode=mode, peers=len(peers), queued_bytes=len(outgoing), **counts)
                last_report = now
    finally:
        report('closed', mode=mode, **counts)
        for peer, _ in peers.values():
            if peer is not None:
                peer.close()
        if udp is not None:
            udp.close()
        selector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('server', 'client'))
    lifetime = parser.add_mutually_exclusive_group(required=True)
    lifetime.add_argument('--deadline', type=int, help='UTC Unix deadline, at most six hours from now')
    lifetime.add_argument('--persistent', action='store_true', help='Run until explicitly stopped; requires operator authorization')
    args = parser.parse_args()
    if args.deadline is not None and not time.time() < args.deadline <= time.time() + 21600:
        parser.error('deadline must be in the next six hours')
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.mode == 'client':
            with socket.create_connection(('127.0.0.1', TCP_PORT), timeout=5) as connection:
                relay(connection, args.mode, args.deadline)
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(('127.0.0.1', TCP_PORT))
                listener.listen(1)
                listener.settimeout(.5)
                report('listening', mode=args.mode, deadline=args.deadline)
                while args.deadline is None or time.time() < args.deadline:
                    try:
                        connection, _ = listener.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        try:
                            relay(connection, args.mode, args.deadline)
                        except (OSError, ValueError) as error:
                            report('connection_error', error=str(error))
    except KeyboardInterrupt:
        report('interrupted')
        return 130
    report('finished')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
