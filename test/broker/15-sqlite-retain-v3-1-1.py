#!/usr/bin/env python3

# Publish a retained messages, check they are restored

from mosq_test_helper import *
import sqlite_help

port = mosq_test.get_port()
conf_file = os.path.basename(__file__).replace('.py', '.conf')
sqlite_help.write_config(conf_file, port)

rc = 1

sqlite_help.init(port)

keepalive = 10
topic1 = "test/retain1"
topic2 = "test/retain2"
topic3 = "test/retain3"
source_id = "persist-retain-v3-1-1"
qos = 0
payload2 = "retained message 2"
payload3 = "retained message 3"
proto_ver = 4
connect_packet = mosq_test.gen_connect(source_id, keepalive=keepalive, proto_ver=proto_ver, clean_session=True)
connack_packet = mosq_test.gen_connack(rc=0, proto_ver=proto_ver)

publish1_packet = mosq_test.gen_publish(topic1, qos=qos, payload="retained message 1", retain=True, proto_ver=proto_ver)
publish2_packet = mosq_test.gen_publish(topic2, qos=qos, payload=payload2, retain=False, proto_ver=proto_ver)
publish3_packet = mosq_test.gen_publish(topic3, qos=qos, payload=payload3, retain=True, proto_ver=proto_ver)

mid = 1
subscribe_packet = mosq_test.gen_subscribe(mid, "#", 0, proto_ver=4)
suback_packet = mosq_test.gen_suback(mid, qos=0, proto_ver=4)

mid = 2
unsubscribe_packet = mosq_test.gen_unsubscribe(mid, "#", proto_ver=4)
unsuback_packet = mosq_test.gen_unsuback(mid, proto_ver=4)

broker = mosq_test.start_broker(filename=os.path.basename(__file__), use_conf=True, port=port)

try:
    # Connect client
    sock = mosq_test.do_client_connect(connect_packet, connack_packet, timeout=5, port=port)
    # Check no retained messages exist
    mosq_test.do_send_receive(sock, subscribe_packet, suback_packet, "suback")
    # Ping will fail if a PUBLISH is received
    mosq_test.do_ping(sock)
    # Unsubscribe, so we don't receive the messages
    mosq_test.do_send_receive(sock, unsubscribe_packet, unsuback_packet, "unsuback")

    # Send some retained messages
    sock.send(publish1_packet)
    mosq_test.do_ping(sock)
    sock.send(publish2_packet) # Not retained
    mosq_test.do_ping(sock)
    sock.send(publish3_packet)
    mosq_test.do_ping(sock)
    sock.close()

    # Kill broker
    broker.terminate()
    broker.wait()

    # Restart broker
    broker = mosq_test.start_broker(filename=os.path.basename(__file__), use_conf=True, port=port)

    # Connect client
    sock = mosq_test.do_client_connect(connect_packet, connack_packet, timeout=5, port=port)
    # Subscribe
    mosq_test.do_send_receive(sock, subscribe_packet, suback_packet, "suback")
    # Check retained messages exist
    mosq_test.receive_unordered(sock, publish1_packet, publish3_packet, "publish 1 / 3")
    mosq_test.do_ping(sock)

    rc = 0
finally:
    if broker is not None:
        broker.terminate()
        broker.wait()
        (stdo, stde) = broker.communicate()
    os.remove(conf_file)
    rc += sqlite_help.cleanup(port)

    if rc:
        print(stde.decode('utf-8'))


exit(rc)
