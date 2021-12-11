#!/usr/bin/env python3

# Connect a client, add a subscription, disconnect, restore, reconnect, send a
# message with a different client, check it is received.

from mosq_test_helper import *
import sqlite_help

def helper(port, packets):
    helper_id = "persist-subscription-v5-0-helper"
    connect_packet_helper = mosq_test.gen_connect(helper_id, proto_ver=5, clean_session=True)
    connack_packet_helper = mosq_test.gen_connack(rc=0, proto_ver=5)

    # Connect helper and publish
    helper = mosq_test.do_client_connect(connect_packet_helper, connack_packet_helper, timeout=5, port=port, connack_error="helper connack")
    helper.send(packets["publish0-helper"])
    mosq_test.do_send_receive(helper, packets["publish1-helper"], packets["puback1"], "puback helper")
    mosq_test.do_send_receive(helper, packets["publish2-helper"], packets["pubrec2"], "pubrec helper")
    mosq_test.do_send_receive(helper, packets["pubrel2"], packets["pubcomp2"], "pubcomp helper")
    helper.close()

port = mosq_test.get_port()
conf_file = os.path.basename(__file__).replace('.py', '.conf')
sqlite_help.write_config(conf_file, port)

rc = 1

sqlite_help.init(port)

client_id = "persist-subscription-v5-0"
proto_ver = 5

topic0 = "subscription/0"
topic1 = "subscription/1"
topic2 = "subscription/2"

packets = {}
connect_props = mqtt5_props.gen_uint32_prop(mqtt5_props.PROP_SESSION_EXPIRY_INTERVAL, 60)
packets["connect"] = mosq_test.gen_connect(client_id, proto_ver=proto_ver, clean_session=False, properties=connect_props)
packets["connack1"] = mosq_test.gen_connack(rc=0, proto_ver=proto_ver)
packets["connack2"] = mosq_test.gen_connack(rc=0, flags=1, proto_ver=proto_ver)
mid = 1

publish_props0 = mqtt5_props.gen_varint_prop(mqtt5_props.PROP_SUBSCRIPTION_IDENTIFIER, 100)
packets["subscribe0"] = mosq_test.gen_subscribe(mid, topic0, qos=0, proto_ver=proto_ver, properties=publish_props0)
packets["suback0"] = mosq_test.gen_suback(mid=mid, qos=0, proto_ver=proto_ver)

publish_props1 = mqtt5_props.gen_varint_prop(mqtt5_props.PROP_SUBSCRIPTION_IDENTIFIER, 101)
packets["subscribe1"] = mosq_test.gen_subscribe(mid, topic1, qos=1, proto_ver=proto_ver, properties=publish_props1)
packets["suback1"] = mosq_test.gen_suback(mid=mid, qos=1, proto_ver=proto_ver)

publish_props2 = mqtt5_props.gen_varint_prop(mqtt5_props.PROP_SUBSCRIPTION_IDENTIFIER, 102)
packets["subscribe2"] = mosq_test.gen_subscribe(mid, topic2, qos=2, proto_ver=proto_ver, properties=publish_props2)
packets["suback2"] = mosq_test.gen_suback(mid=mid, qos=2, proto_ver=proto_ver)

packets["unsubscribe2"] = mosq_test.gen_unsubscribe(mid, topic2, proto_ver=proto_ver)
packets["unsuback2"] = mosq_test.gen_unsuback(mid=mid, proto_ver=proto_ver)

packets["publish0-helper"] = mosq_test.gen_publish(topic=topic0, qos=0, payload="message", proto_ver=proto_ver)
packets["publish0"] = mosq_test.gen_publish(topic=topic0, qos=0, payload="message", proto_ver=proto_ver, properties=publish_props0)
mid = 1
packets["publish1-helper"] = mosq_test.gen_publish(topic=topic1, qos=1, payload="message", mid=mid, proto_ver=proto_ver)
packets["publish1"] = mosq_test.gen_publish(topic=topic1, qos=1, payload="message", mid=mid, proto_ver=proto_ver, properties=publish_props1)
packets["puback1"] = mosq_test.gen_puback(mid=mid, proto_ver=proto_ver)
mid = 2
packets["publish2-helper"] = mosq_test.gen_publish(topic=topic2, qos=2, payload="message", mid=mid, proto_ver=proto_ver)
packets["publish2"] = mosq_test.gen_publish(topic=topic2, qos=2, payload="message", mid=mid, proto_ver=proto_ver, properties=publish_props2)
packets["pubrec2"] = mosq_test.gen_pubrec(mid=mid, proto_ver=proto_ver)
packets["pubrel2"] = mosq_test.gen_pubrel(mid=mid, proto_ver=proto_ver)
packets["pubcomp2"] = mosq_test.gen_pubcomp(mid=mid, proto_ver=proto_ver)


broker = mosq_test.start_broker(filename=os.path.basename(__file__), use_conf=True, port=port)

con = None
try:
    # Connect client
    sock = mosq_test.do_client_connect(packets["connect"], packets["connack1"], timeout=5, port=port, connack_error="connack1")
    mosq_test.do_send_receive(sock, packets["subscribe0"], packets["suback0"], "suback 0")
    mosq_test.do_send_receive(sock, packets["subscribe1"], packets["suback1"], "suback 1")
    mosq_test.do_send_receive(sock, packets["subscribe2"], packets["suback2"], "suback 2")
    sock.close()

    # Kill broker
    broker.terminate()
    broker.wait()

    # Restart broker
    broker = mosq_test.start_broker(filename=os.path.basename(__file__), use_conf=True, port=port)

    # Connect client again, it should have a session
    sock = mosq_test.do_client_connect(packets["connect"], packets["connack2"], timeout=5, port=port)
    mosq_test.do_ping(sock)

    helper(port, packets)

    # Does the client get the messages
    mosq_test.expect_packet(sock, "publish 0", packets["publish0"])
    mosq_test.do_receive_send(sock, packets["publish1"], packets["puback1"], "publish 1")
    mosq_test.do_receive_send(sock, packets["publish2"], packets["pubrec2"], "publish 2")
    mosq_test.do_receive_send(sock, packets["pubrel2"], packets["pubcomp2"], "pubrel 2")

    # Unsubscribe
    mosq_test.do_send_receive(sock, packets["unsubscribe2"], packets["unsuback2"], "unsuback 2")
    sock.close()

    # Kill broker
    broker.terminate()
    broker.wait()

    # Restart broker
    broker = mosq_test.start_broker(filename=os.path.basename(__file__), use_conf=True, port=port)

    # Connect client again, it should have a session
    sock = mosq_test.do_client_connect(packets["connect"], packets["connack2"], timeout=5, port=port, connack_error="connack2")
    mosq_test.do_ping(sock)

    # Connect helper and publish
    helper(port, packets)

    # Does the client get the messages
    mosq_test.expect_packet(sock, "publish 0", packets["publish0"])
    mosq_test.do_receive_send(sock, packets["publish1"], packets["puback1"], "publish 1")
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
