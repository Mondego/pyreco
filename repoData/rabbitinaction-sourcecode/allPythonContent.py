__FILENAME__ = amqp_ping_check
###############################################
# RabbitMQ in Action
# Chapter 10 - RabbitMQ ping (AMQP) check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, pika

#(nc.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(nc.1) Parse command line arguments
server, port = sys.argv[1].split(":")
vhost = sys.argv[2]
username = sys.argv[3]
password = sys.argv[4]

#/(nc.2) Establish connection to broker
creds_broker = pika.PlainCredentials(username, password)
conn_params = pika.ConnectionParameters(server,
                                        virtual_host = vhost,
                                        credentials = creds_broker)
try:
    conn_broker = pika.BlockingConnection(conn_params)
    channel = conn_broker.channel()
except Exception:
#/(nc.3) Connection failed, return CRITICAL status
    print "CRITICAL: Could not connect to %s:%s!" % (server, port)
    exit(EXIT_CRITICAL)

#(nc.4) Connection OK, return OK status
print "OK: Connect to %s:%s successful." % (server, port)
exit(EXIT_OK)
########NEW FILE########
__FILENAME__ = amqp_queue_count_check
###############################################
# RabbitMQ in Action
# Chapter 10 - Queue count (AMQP) check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, pika, socket

#(aqcc.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(aqcc.1) Parse command line arguments
server, port = sys.argv[1].split(":")
vhost = sys.argv[2]
username = sys.argv[3]
password = sys.argv[4]
queue_name = sys.argv[5]
max_critical = int(sys.argv[6])
max_warn = int(sys.argv[7])

#/(aqcc.2) Establish connection to broker
creds_broker = pika.PlainCredentials(username, password)
conn_params = pika.ConnectionParameters(server,
                                        virtual_host = vhost,
                                        credentials = creds_broker)
try:
    conn_broker = pika.BlockingConnection(conn_params)
    channel = conn_broker.channel()
except socket.timeout:
#/(aqcc.3) Connection failed, return unknown status
    print "Unknown: Could not connect to %s:%s!" % (server, port)
    exit(EXIT_UNKNOWN)

try:
    response = channel.queue_declare(queue=queue_name,
                                     passive=True)
except pika.exceptions.AMQPChannelError:
    print "CRITICAL: Queue %s does not exist." % queue_name
    exit(EXIT_CRITICAL)

#(aqcc.4) Message count is above critical limit
if response.method.message_count >= max_critical:
    print "CRITICAL: Queue %s message count: %d" % \
          (queue_name, response.method.message_count)
    exit(EXIT_CRITICAL)

#(aqcc.5) Message count is above warning limit
if response.method.message_count >= max_warn:
    print "WARN: Queue %s message count: %d" % \
          (queue_name, response.method.message_count)
    exit(EXIT_WARNING)

#(aqcc.6) Connection OK, return OK status
print "OK: Queue %s message count: %d" % \
      (queue_name, response.method.message_count)
exit(EXIT_OK)
########NEW FILE########
__FILENAME__ = api_ping_check
###############################################
# RabbitMQ in Action
# Chapter 10 - RabbitMQ ping (HTTP API) check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import sys, json, httplib, urllib, base64, socket

#(apic.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(apic.1) Parse arguments
server, port = sys.argv[1].split(":")
vhost = sys.argv[2]
username = sys.argv[3]
password = sys.argv[4]

#/(apic.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(apic.3) Build API path
path = "/api/aliveness-test/%s" % urllib.quote(vhost, safe="")
method = "GET"

#/(apic.4) Issue API request
credentials = base64.b64encode("%s:%s" % (username, password))

try:
    conn.request(method, path, "",
                 {"Content-Type" : "application/json",
                  "Authorization" : "Basic " + credentials})

#/(apic.5) Could not connect to API server, return critical status
except socket.error:
    print "CRITICAL: Could not connect to %s:%s" % (server, port)
    exit(EXIT_CRITICAL)

response = conn.getresponse()

#/(apic.6) RabbitMQ not responding/alive, return critical status
if response.status > 299:
    print "CRITICAL: Broker not alive: %s" % response.read()
    exit(EXIT_CRITICAL)

#/(apic.7) RabbitMQ alive, return OK status
print "OK: Broker alive: %s" % response.read()
exit(EXIT_OK)

########NEW FILE########
__FILENAME__ = api_queue_count_check
###############################################
# RabbitMQ in Action
# Chapter 10 - Queue count (HTTP API) check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import sys, json, httplib, urllib, base64, socket

#(aqcc.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(aqcc.1) Parse arguments
server, port = sys.argv[1].split(":")
vhost = sys.argv[2]
username = sys.argv[3]
password = sys.argv[4]
queue_name = sys.argv[5]
max_unack_critical = int(sys.argv[6])
max_unack_warn = int(sys.argv[7])
max_ready_critical = int(sys.argv[8])
max_ready_warn = int(sys.argv[9])


#/(aqcc.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(aqcc.3) Build API path
path = "/api/queues/%s/%s" % (urllib.quote(vhost, safe=""),
                              queue_name)
method = "GET"

#/(aqcc.4) Issue API request
credentials = base64.b64encode("%s:%s" % (username, password))

try:
    conn.request(method, path, "",
                 {"Content-Type" : "application/json",
                  "Authorization" : "Basic " + credentials})

#/(aqcc.5) Could not connect to API server, return unknown status
except socket.error:
    print "UNKNOWN: Could not connect to %s:%s" % (server, port)
    exit(EXIT_UNKNOWN)

response = conn.getresponse()

#/(aqcc.6) RabbitMQ not responding/alive, return critical status
if response.status > 299:
    print "UNKNOWN: Unexpected API error: %s" % response.read()
    exit(EXIT_UNKNOWN)

#/(aqcc.7) Extract message count levels from response
resp_payload = json.loads(response.read())
msg_cnt_unack = resp_payload["messages_unacknowledged"]
msg_cnt_ready = resp_payload["messages_ready"]
msg_cnt_total = resp_payload["messages"]

#/(aqcc.8) Consumed but unacknowledged message count above thresholds
if msg_cnt_unack >= max_unack_critical:
    print "CRITICAL: %s - %d unack'd messages." % (queue_name,
                                                   msg_cnt_unack)
    exit(EXIT_CRITICAL)
elif msg_cnt_unack >= max_unack_warn:
    print "WARN: %s - %d unack'd messages." % (queue_name,
                                               msg_cnt_unack)
    exit(EXIT_WARNING)

#/(aqcc.9) Ready to be consumed message count above thresholds
if msg_cnt_ready >= max_ready_critical:
    print "CRITICAL: %s - %d unconsumed messages." % (queue_name,
                                                      msg_cnt_ready)
    exit(EXIT_CRITICAL)
elif msg_cnt_ready >= max_ready_warn:
    print "WARN: %s - %d unconsumed messages." % (queue_name,
                                                  msg_cnt_ready)
    exit(EXIT_WARNING)

#/(aqcc.10) Message counts below thresholds, return OK status
print "OK: %s - %d in-flight messages. %dB used memory." % \
      (queue_name, msg_cnt_total, resp_payload["memory"])
exit(EXIT_OK)
########NEW FILE########
__FILENAME__ = cluster_health_check
###############################################
# RabbitMQ in Action
# Chapter 10 - Cluster health check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import sys, json, httplib, base64, socket

#(chc.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(chc.1) Parse arguments
server, port = sys.argv[1].split(":")
username = sys.argv[2]
password = sys.argv[3]
node_list = sys.argv[4].split(",")
mem_critical = int(sys.argv[5])
mem_warning = int(sys.argv[6])

#/(chc.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(chc.3) Build API path
path = "/api/nodes"
method = "GET"

#/(chc.4) Issue API request
credentials = base64.b64encode("%s:%s" % (username, password))
try:
    conn.request(method, path, "",
                 {"Content-Type" : "application/json",
                  "Authorization" : "Basic " + credentials})
#/(chc.5) Could not connect to API server, return unknown status
except socket.error:
    print "UNKNOWN: Could not connect to %s:%s" % (server, port)
    exit(EXIT_UNKNOWN)

response = conn.getresponse()

#/(chc.6) Unexpected API error, return unknown status
if response.status > 299:
    print "UNKNOWN: Unexpected API error: %s" % response.read()
    exit(EXIT_UNKNOWN)

#/(chc.7) Parse API response
response = json.loads(response.read())

#/(chc.8) Cluster is missing nodes, return warning status
for node in response:
    if node["name"] in node_list and node["running"] != False:
        node_list.remove(node["name"])

if len(node_list):
    print "WARNING: Cluster missing nodes: %s" % str(node_list)
    exit(EXIT_WARNING)

#/(chc.9) Node used memory is over limit
for node in response:
    if node["mem_used"] > mem_critical:
        print "CRITICAL: Node %s memory usage is %d." % \
              (node["name"], node["mem_used"])
        exit(EXIT_CRITICAL)
    elif node["mem_used"] > mem_warning:
        print "WARNING: Node %s memory usage is %d." % \
              (node["name"], node["mem_used"])
        exit(EXIT_WARNING)

#/(chc.10) All nodes present and used memory below limit
print "OK: %d nodes. All memory usage below %d." % (len(response),
                                                    mem_warning)
exit(EXIT_OK)
########NEW FILE########
__FILENAME__ = nagios_check
###############################################
# RabbitMQ in Action
# Chapter 10 - Basic Nagios check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, httplib, base64

#/(nc.1) Return requested Nagios status code 
status = sys.argv[1]

if status.lower() == "warning":
    print "Status is WARN"
    exit(1)
elif status.lower() == "critical":
    print "Status is CRITICAL"
    exit(2)
elif status.lower() == "unknown":
    print "Status is UNKNOWN"
    exit(3)
else:
    print "Status is OK"
    exit(0)

########NEW FILE########
__FILENAME__ = queue_config_check
###############################################
# RabbitMQ in Action
# Chapter 10 - Queue config watchdog check.
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import sys, json, httplib, urllib, base64, socket

#(qcwc.0) Nagios status codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

#/(qcwc.1) Parse arguments
server, port = sys.argv[1].split(":")
vhost = sys.argv[2]
username = sys.argv[3]
password = sys.argv[4]
queue_name = sys.argv[5]
auto_delete = json.loads(sys.argv[6].lower())
durable = json.loads(sys.argv[7].lower())

#/(qcwc.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(qcwc.3) Build API path
path = "/api/queues/%s/%s" % (urllib.quote(vhost, safe=""),
                              urllib.quote(queue_name))
method = "GET"

#/(qcwc.4) Issue API request
credentials = base64.b64encode("%s:%s" % (username, password))
try:
    conn.request(method, path, "",
                 {"Content-Type" : "application/json",
                  "Authorization" : "Basic " + credentials})
#/(qcwc.5) Could not connect to API server, return unknown status
except socket.error:
    print "UNKNOWN: Could not connect to %s:%s" % (server, port)
    exit(EXIT_UNKNOWN)

response = conn.getresponse()

#/(qcwc.6) Queue does not exist, return critical status
if response.status == 404:
    print "CRITICAL: Queue %s does not exist." % queue_name
    exit(EXIT_CRITICAL)
#/(qcwc.7) Unexpected API error, return unknown status
elif response.status > 299:
    print "UNKNOWN: Unexpected API error: %s" % response.read()
    exit(EXIT_UNKNOWN)

#/(qcwc.8) Parse API response
response = json.loads(response.read())

#/(qcwc.9) Queue auto_delete flag incorrect, return warning status
if response["auto_delete"] != auto_delete:
    print "WARN: Queue '%s' - auto_delete flag is NOT %s." % \
          (queue_name, auto_delete)
    exit(EXIT_WARNING)

#/(qcwc.10) Queue durable flag incorrect, return warning status
if response["durable"] != durable:
    print "WARN: Queue '%s' - durable flag is NOT %s." % \
          (queue_name, durable)
    exit(EXIT_WARNING)


#/(qcwc.11) Queue exists and it's flags are correct, return OK status
print "OK: Queue %s configured correctly." % queue_name
exit(EXIT_OK)
########NEW FILE########
__FILENAME__ = hello_world_consumer
###############################################
# RabbitMQ in Action
# Chapter 1 - Hello World Consumer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) #/(hwc.1) Establish connection to broker


channel = conn_broker.channel() #/(hwc.2) Obtain channel

channel.exchange_declare(exchange="hello-exchange", #/(hwc.3) Declare the exchange
                         type="direct",
                         passive=False,
                         durable=True,
                         auto_delete=False)

channel.queue_declare(queue="hello-queue") #/(hwc.4) Declare the queue

channel.queue_bind(queue="hello-queue",     #/(hwc.5) Bind the queue and exchange together on the key "hola"
                   exchange="hello-exchange",
                   routing_key="hola")


def msg_consumer(channel, method, header, body): #/(hwc.6) Make function to process incoming messages
    
    channel.basic_ack(delivery_tag=method.delivery_tag)  #/(hwc.7) Message acknowledgement
    
    if body == "quit":
        channel.basic_cancel(consumer_tag="hello-consumer") #/(hwc.8) Stop consuming more messages and quit
        channel.stop_consuming()
    else:
        print body
    
    return



channel.basic_consume( msg_consumer,    #/(hwc.9) Subscribe our consumer
                       queue="hello-queue",
                       consumer_tag="hello-consumer")

channel.start_consuming() #/(hwc.10) Start consuming
########NEW FILE########
__FILENAME__ = hello_world_producer
###############################################
# RabbitMQ in Action
# Chapter 1 - Hello World Producer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika, sys

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) #/(hwp.1) Establish connection to broker


channel = conn_broker.channel() #/(hwp.2) Obtain channel

channel.exchange_declare(exchange="hello-exchange", #/(hwp.3) Declare the exchange
                         type="direct",
                         passive=False,
                         durable=True,
                         auto_delete=False)

msg = sys.argv[1]
msg_props = pika.BasicProperties()
msg_props.content_type = "text/plain" #/(hwp.4) Create a plaintext message

channel.basic_publish(body=msg,
                      exchange="hello-exchange",
                      properties=msg_props,
                      routing_key="hola") #/(hwp.5) Publish the message
########NEW FILE########
__FILENAME__ = hello_world_producer_pubconfirm
###############################################
# RabbitMQ in Action
# Chapter 1 - Hello World Producer
#             w/ Publisher Confirms
# 
# Requires: pika >= 0.9.6
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika, sys
from pika import spec

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) 

channel = conn_broker.channel()

def confirm_handler(frame): #/(hwppc.1) Publisher confirm handler
    if type(frame.method) == spec.Confirm.SelectOk:
        print "Channel in 'confirm' mode."
    elif type(frame.method) == spec.Basic.Nack:
        if frame.method.delivery_tag in msg_ids:
            print "Message lost!"
    elif type(frame.method) == spec.Basic.Ack:
        if frame.method.delivery_tag in msg_ids:
            print "Confirm received!"
            msg_ids.remove(frame.method.delivery_tag)

#/(hwppc.2) Put channel in "confirm" mode
channel.confirm_delivery(callback=confirm_handler)

msg = sys.argv[1]
msg_props = pika.BasicProperties()
msg_props.content_type = "text/plain"

msg_ids = [] #/(hwppc.3) Reset message ID tracker

channel.basic_publish(body=msg,
                      exchange="hello-exchange",
                      properties=msg_props,
                      routing_key="hola") #/(hwppc.4) Publish the message

msg_ids.append(len(msg_ids) + 1) #/(hwppc.5) Add ID to tracking list

channel.close()


########NEW FILE########
__FILENAME__ = hello_world_producer_tx
###############################################
# RabbitMQ in Action
# Chapter 1 - Hello World Producer
#             w/ Transactions
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika, sys

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) #/(hwp.1) Establish connection to broker


channel = conn_broker.channel() #/(hwp.2) Obtain channel

channel.exchange_declare(exchange="hello-exchange", #/(hwp.3) Declare the exchange
                         type="direct",
                         passive=False,
                         durable=True,
                         auto_delete=False)

msg = sys.argv[1]
msg_props = pika.BasicProperties()
msg_props.content_type = "text/plain" #/(hwp.4) Create a plaintext message

channel.tx_select()
channel.basic_publish(body=msg,
                      exchange="hello-exchange",
                      properties=msg_props,
                      routing_key="hola") #/(hwp.5) Publish the message
channel.tx_commit()
########NEW FILE########
__FILENAME__ = alert_consumer
###############################################
# RabbitMQ in Action
# Chapter 4.2.2 - Alerting Server Consumer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import json, smtplib
import pika


def send_mail(recipients, subject, message):
    """E-mail generator for received alerts."""
    headers = ("From: %s\r\nTo: \r\nDate: \r\n" + \
               "Subject: %s\r\n\r\n") % ("alerts@ourcompany.com",
                                         subject)
    
    smtp_server = smtplib.SMTP()
    smtp_server.connect("mail.ourcompany.com", 25)
    smtp_server.sendmail("alerts@ourcompany.com",
                         recipients,
                         headers + str(message))
    smtp_server.close()

#/(asc.5) Notify Processors
def critical_notify(channel, method, header, body):
    """Sends CRITICAL alerts to administrators via e-mail."""
    
    EMAIL_RECIPS = ["ops.team@ourcompany.com",]
    
    #/(asc.6) Decode our message from JSON    
    message = json.loads(body)
    
    #/(asc.7) Transmit e-mail to SMTP server
    send_mail(EMAIL_RECIPS, "CRITICAL ALERT", message)
    print ("Sent alert via e-mail! Alert Text: %s  " + \
           "Recipients: %s") % (str(message), str(EMAIL_RECIPS))
    
    #/(asc.8) Acknowledge the message
    channel.basic_ack(delivery_tag=method.delivery_tag)

def rate_limit_notify(channel, method, header, body):
    """Sends the message to the administrators via e-mail."""
    
    EMAIL_RECIPS = ["api.team@ourcompany.com",]
    
    #/(asc.9) Decode our message from JSON
    message = json.loads(body)
    
    #/(asc.10) Transmit e-mail to SMTP server
    send_mail(EMAIL_RECIPS, "RATE LIMIT ALERT!", message)
    
    print ("Sent alert via e-mail! Alert Text: %s  " + \
           "Recipients: %s") % (str(message), str(EMAIL_RECIPS))
    
    #/(asc.11) Acknowledge the message
    channel.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    #/(asc.0) Broker settings
    AMQP_SERVER = "localhost"
    AMQP_USER = "alert_user"
    AMQP_PASS = "alertme"
    AMQP_VHOST = "/"
    AMQP_EXCHANGE = "alerts"
    
    #/(asc.1) Establish connection to broker
    creds_broker = pika.PlainCredentials(AMQP_USER, AMQP_PASS)
    conn_params = pika.ConnectionParameters(AMQP_SERVER,
                                            virtual_host = AMQP_VHOST,
                                            credentials = creds_broker)
    conn_broker = pika.BlockingConnection(conn_params)
    
    channel = conn_broker.channel()
    
    #/(asc.2) Declare the Exchange
    channel.exchange_declare( exchange=AMQP_EXCHANGE,
                              type="topic",
                              auto_delete=False)
    
    #/(asc.3) Build the queues and bindings for our topics    
    channel.queue_declare(queue="critical", auto_delete=False)
    channel.queue_bind(queue="critical",
                       exchange="alerts",
                       routing_key="critical.*")
    
    channel.queue_declare(queue="rate_limit", auto_delete=False)
    channel.queue_bind(queue="rate_limit",
                       exchange="alerts",
                       routing_key="*.rate_limit")
    
    #/(asc.4) Make our alert processors
    
    channel.basic_consume( critical_notify,
                           queue="critical",
                           no_ack=False,
                           consumer_tag="critical")
    
    channel.basic_consume( rate_limit_notify,
                           queue="rate_limit",
                           no_ack=False,
                           consumer_tag="rate_limit")
    
    print "Ready for alerts!"
    channel.start_consuming()
    
########NEW FILE########
__FILENAME__ = alert_producer
###############################################
# RabbitMQ in Action
# Chapter 4.2.2 - Alerting Server Producer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import json, pika
from optparse import OptionParser

#/(asp.0) Read in command line arguments
opt_parser = OptionParser()
opt_parser.add_option("-r",
                      "--routing-key",
                      dest="routing_key",
                      help="Routing key for message (e.g. myalert.im)")
opt_parser.add_option("-m",
                      "--message",
                      dest="message", 
                      help="Message text for alert.")

args = opt_parser.parse_args()[0]

#/(asp.1) Establish connection to broker
creds_broker = pika.PlainCredentials("alert_user", "alertme")
conn_params = pika.ConnectionParameters("localhost",
                                        virtual_host = "/",
                                        credentials = creds_broker)
conn_broker = pika.BlockingConnection(conn_params)

channel = conn_broker.channel()

#/(asp.2) Publish alert message to broker
msg = json.dumps(args.message)
msg_props = pika.BasicProperties()
msg_props.content_type = "application/json"
msg_props.durable = False

channel.basic_publish(body=msg,
                      exchange="alerts",
                      properties=msg_props,
                      routing_key=args.routing_key)

print ("Sent message %s tagged with routing key '%s' to " + \
       "exchange '/'.") % (json.dumps(args.message),
                           args.routing_key)
########NEW FILE########
__FILENAME__ = rpc_client
###############################################
# RabbitMQ in Action
# Chapter 4.3.3 - RPC Client
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import time, json, pika

#/(rpcc.0) Establish connection to broker
creds_broker = pika.PlainCredentials("rpc_user", "rpcme")
conn_params = pika.ConnectionParameters("localhost",
                                        virtual_host = "/",
                                        credentials = creds_broker)
conn_broker = pika.BlockingConnection(conn_params)
channel = conn_broker.channel()

#/(rpcc.1) Issue RPC call & wait for reply
msg = json.dumps({"client_name": "RPC Client 1.0", 
                  "time" : time.time()})

result = channel.queue_declare(exclusive=True, auto_delete=True)
msg_props = pika.BasicProperties()
msg_props.reply_to=result.method.queue

channel.basic_publish(body=msg,
                      exchange="rpc",
                      properties=msg_props,
                      routing_key="ping")

print "Sent 'ping' RPC call. Waiting for reply..."

def reply_callback(channel, method, header, body):
    """Receives RPC server replies."""
    print "RPC Reply --- " + body
    channel.stop_consuming()



channel.basic_consume(reply_callback,
                      queue=result.method.queue,
                      consumer_tag=result.method.queue)

channel.start_consuming()
########NEW FILE########
__FILENAME__ = rpc_server
###############################################
# RabbitMQ in Action
# Chapter 4.3.3 - RPC Server
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika, json

#/(apiserver.0) Establish connection to broker
creds_broker = pika.PlainCredentials("rpc_user", "rpcme")
conn_params = pika.ConnectionParameters("localhost",
                                        virtual_host = "/",
                                        credentials = creds_broker)
conn_broker = pika.BlockingConnection(conn_params)
channel = conn_broker.channel()

#/(apiserver.1) Declare Exchange & "ping" Call Queue
channel.exchange_declare(exchange="rpc",
                         type="direct",
                         auto_delete=False)
channel.queue_declare(queue="ping", auto_delete=False)
channel.queue_bind(queue="ping",
                   exchange="rpc",
                   routing_key="ping")

#/(apiserver.2) Wait for RPC calls and reply
def api_ping(channel, method, header, body):
    """'ping' API call."""
    channel.basic_ack(delivery_tag=method.delivery_tag)
    msg_dict = json.loads(body)
    print "Received API call...replying..."
    channel.basic_publish(body="Pong!" + str(msg_dict["time"]),
                          exchange="",
                          routing_key=header.reply_to)

channel.basic_consume(api_ping,
                      queue="ping",
                      consumer_tag="ping")

print "Waiting for RPC calls..."
channel.start_consuming()
########NEW FILE########
__FILENAME__ = hello_world_mirrored_queue_consumer
###############################################
# RabbitMQ in Action
# Chapter 5 - Hello World Consumer
#             (Mirrored Queues)
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) #/(hwcmq.1) Establish connection to broker


channel = conn_broker.channel() #/(hwcmq.2) Obtain channel

channel.exchange_declare(exchange="hello-exchange", #/(hwcmq.3) Declare the exchange
                         type="direct",
                         passive=False,
                         durable=True,
                         auto_delete=False)

queue_args = {"x-ha-policy" : "all" } #/(hwcmq.4) Set queue mirroring policy

channel.queue_declare(queue="hello-queue", arguments=queue_args) #/(hwcmq.5) Declare the queue

channel.queue_bind(queue="hello-queue",     #/(hwcmq.6) Bind the queue and exchange together on the key "hola"
                   exchange="hello-exchange",
                   routing_key="hola")


def msg_consumer(channel, method, header, body): #/(hwcmq.7) Make function to process incoming messages
    
    channel.basic_ack(delivery_tag=method.delivery_tag)  #/(hwcmq.8) Message acknowledgement
    
    if body == "quit":
        channel.basic_cancel(consumer_tag="hello-consumer") #/(hwcmq.9) Stop consuming more messages and quit
        channel.stop_consuming()
    else:
        print body
    
    return



channel.basic_consume( msg_consumer,    #/(hwc.9) Subscribe our consumer
                       queue="hello-queue",
                       consumer_tag="hello-consumer")

channel.start_consuming() #/(hwc.10) Start consuming
########NEW FILE########
__FILENAME__ = hello_world_mirrored_queue_consumer_selective_nodes
###############################################
# RabbitMQ in Action
# Chapter 5 - Hello World Consumer
#             (Mirrored Queues)
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################

import pika

credentials = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters("localhost",
                                        credentials = credentials)
conn_broker = pika.BlockingConnection(conn_params) #/(hwcmq.1) Establish connection to broker


channel = conn_broker.channel() #/(hwcmq.2) Obtain channel

channel.exchange_declare(exchange="hello-exchange", #/(hwcmq.3) Declare the exchange
                         type="direct",
                         passive=False,
                         durable=True,
                         auto_delete=False)

queue_args = {"x-ha-policy" : "nodes",
              "x-ha-policy-params" : ["rabbit@Phantome",
                                      "rabbit2@Phantome"]} #/(hwcmq.4) Set queue mirroring policy

channel.queue_declare(queue="hello-queue", arguments=queue_args) #/(hwcmq.5) Declare the queue

channel.queue_bind(queue="hello-queue",     #/(hwcmq.6) Bind the queue and exchange together on the key "hola"
                   exchange="hello-exchange",
                   routing_key="hola")


def msg_consumer(channel, method, header, body): #/(hwcmq.7) Make function to process incoming messages
    
    channel.basic_ack(delivery_tag=method.delivery_tag)  #/(hwcmq.8) Message acknowledgement
    
    if body == "quit":
        channel.basic_cancel(consumer_tag="hello-consumer") #/(hwcmq.9) Stop consuming more messages and quit
        channel.stop_consuming()
    else:
        print body
    
    return



channel.basic_consume( msg_consumer,    #/(hwc.9) Subscribe our consumer
                       queue="hello-queue",
                       consumer_tag="hello-consumer")

channel.start_consuming() #/(hwc.10) Start consuming
########NEW FILE########
__FILENAME__ = cluster_test_consumer
###############################################
# RabbitMQ in Action
# Chapter 5 - Cluster Test Consumer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, pika, time, traceback


def msg_rcvd(channel, method, header, body):
    message = json.loads(body)
    
    #/(ctc.1) Print & acknowledge our message
    print "Received: %(content)s/%(time)d" % message
    channel.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    #/(ctc.2) Broker settings
    AMQP_SERVER = sys.argv[1]
    AMQP_PORT = int(sys.argv[2])
    
    #/(ctc.3) Establish broker connection settings
    creds_broker = pika.PlainCredentials("guest", "guest")
    conn_params = pika.ConnectionParameters( AMQP_SERVER,
                                             port=AMQP_PORT,
                                             virtual_host="/",
                                             credentials=creds_broker)
    
    
    #/(ctc.4) On fault, reconnect to RabbitMQ
    while True:
        try:
            #/(ctc.5) Establish connection to RabbitMQ
            conn_broker = pika.BlockingConnection(conn_params)
            
            #/(ctc.6) Custom connection behavior
            channel = conn_broker.channel()
            #/(ctc.7) Declare the exchange, queues & bindings
            channel.exchange_declare( exchange="cluster_test",
                                      type="direct",
                                      auto_delete=False)    
            channel.queue_declare( queue="cluster_test",
                                   auto_delete=False)
            channel.queue_bind( queue="cluster_test",
                                exchange="cluster_test",
                                routing_key="cluster_test")
            
            #/(ctc.8) Start consuming messages
            print "Ready for testing!"
            channel.basic_consume( msg_rcvd,
                                   queue="cluster_test",
                                   no_ack=False,
                                   consumer_tag="cluster_test")
            channel.start_consuming()
        #/(ctc.9) Trap connection errors and print them
        except Exception, e:
            traceback.print_exc()
    
    
    
########NEW FILE########
__FILENAME__ = cluster_test_producer
###############################################
# RabbitMQ in Action
# Chapter 5 - Cluster Test Producer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, time, json, pika

AMQP_HOST = sys.argv[1]
AMQP_PORT = int(sys.argv[2])

#/(ctp.1) Establish connection to broker
creds_broker = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters(AMQP_HOST,
                                        port=AMQP_PORT,
                                        virtual_host = "/",
                                        credentials = creds_broker)

conn_broker = pika.BlockingConnection(conn_params)

channel = conn_broker.channel()

#/(ctp.2) Connect to RabbitMQ and send message

msg = json.dumps({"content": "Cluster Test!", 
                  "time" : time.time()})
msg_props = pika.BasicProperties(content_type="application/json")

channel.basic_publish(body=msg, mandatory=True,
                      exchange="",
                      properties=msg_props,
                      routing_key="cluster_test")

print "Sent cluster test message."


########NEW FILE########
__FILENAME__ = shovel_consumer
###############################################
# RabbitMQ in Action
# Chapter 5 - Shovel Test Consumer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, pika, time, traceback


def msg_rcvd(channel, method, header, body):
    message = json.loads(body)
    
    #/(ctc.1) Print & acknowledge our order
    print "Received order %(ordernum)d for %(type)s." % message
    channel.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    #/(ctc.2) Broker settings
    AMQP_SERVER = sys.argv[1]
    AMQP_PORT = int(sys.argv[2])
    
    #/(ctc.3) Establish broker connection settings
    creds_broker = pika.PlainCredentials("guest", "guest")
    conn_params = pika.ConnectionParameters( AMQP_SERVER,
                                             port=AMQP_PORT,
                                             virtual_host="/",
                                             credentials=creds_broker)
    
    #/(ctc.5) Establish connection to RabbitMQ
    conn_broker = pika.BlockingConnection(conn_params)
    channel = conn_broker.channel()
    
    #/(ctc.8) Start processing orders
    print "Ready for orders!"
    channel.basic_consume( msg_rcvd,
                           queue="warehouse_carpinteria",
                           no_ack=False,
                           consumer_tag="order_processor")
    channel.start_consuming()
    
########NEW FILE########
__FILENAME__ = shovel_producer
###############################################
# RabbitMQ in Action
# Chapter 5 - Shovel Test Producer
# 
# Requires: pika >= 0.9.5
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, pika, random

AMQP_HOST = sys.argv[1]
AMQP_PORT = int(sys.argv[2])
AVOCADO_TYPE = sys.argv[3]

#/(ctp.1) Establish connection to broker
creds_broker = pika.PlainCredentials("guest", "guest")
conn_params = pika.ConnectionParameters(AMQP_HOST,
                                        port=AMQP_PORT,
                                        virtual_host = "/",
                                        credentials = creds_broker)

conn_broker = pika.BlockingConnection(conn_params)

channel = conn_broker.channel()

#/(ctp.2) Connect to RabbitMQ and send message

msg = json.dumps({"ordernum": random.randrange(0, 100, 1),
                  "type" : AVOCADO_TYPE})
msg_props = pika.BasicProperties(content_type="application/json")

channel.basic_publish(body=msg, mandatory=True,
                      exchange="incoming_orders",
                      properties=msg_props,
                      routing_key="warehouse")

print "Sent avocado order message."


########NEW FILE########
__FILENAME__ = node_lister
###############################################
# RabbitMQ in Action
# Chapter 9 - RMQ Node Lister
###############################################
# 
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, httplib, base64

#/(nl.1) Assign arguments
if len(sys.argv) < 4:
    print "USAGE: node_lister.py server_name:port auth_user auth_pass"
    sys.exit(1)

server, port = sys.argv[1].split(":")
username = sys.argv[2]
password = sys.argv[3]

#/(nl.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(nl.3) Build API path
path = "/api/nodes"
method = "GET"

#/(nl.4) Issue API request
credentials = base64.b64encode("%s:%s" % (username, password))
conn.request(method, path, "",
             {"Content-Type" : "application/json",
              "Authorization" : "Basic " + credentials})
response = conn.getresponse()
if response.status > 299:
    print "Error executing API call (%d): %s" % (response.status,
                                                 response.read())
    sys.exit(2)

#/(nl.6) Parse and display node list
resp_payload = json.loads(response.read())
for node in resp_payload:
    print "Node '%(name)s'" % node
    print "================"
    print "\t Memory Used: %(mem_used)d" % node
    print "\t Memory Limit: %(mem_limit)d" % node
    print "\t Uptime (secs): %(uptime)d" % node
    print "\t CPU Count: %(processors)d" % node
    print "\t Node Type: %(type)s" % node
    print "\t Erlang Version: %(erlang_version)s"  % node
    print "\n"
    print "\tInstalled Apps/Plugins"
    print "\t----------------------"
    for app in node["applications"]:
        print "\t\t%(name)s" % app
        print "\t\t\tVersion: %(version)s" % app
        print "\t\t\tDescription: %(description)s\n" % app

sys.exit(0)
########NEW FILE########
__FILENAME__ = queue_stats
###############################################
# RabbitMQ in Action
# Chapter 9 - RMQ Queue Statistics
###############################################
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, httplib, urllib, base64

#/(qs.0) Validate argument count
if len(sys.argv) < 6:
    print "USAGE: queue_stats.py server_name:port auth_user auth_pass VHOST QUEUE_NAME"
    sys.exit(1)

#/(qs.1) Assign arguments to memorable variables
server, port = sys.argv[1].split(":")
username = sys.argv[2]
password = sys.argv[3]
vhost = sys.argv[4]
queue_name = sys.argv[5]

#/(qs.2) Build API path
vhost = urllib.quote(vhost, safe='')
queue_name = urllib.quote(queue_name, safe='')
path = "/api/queues/%s/%s" % (vhost, queue_name)
#/(qs.3) Set the request method
method = "GET"

#/(qs.4) Connect to the API server
conn = httplib.HTTPConnection(server, port)
#/(qs.5) Base64 the username/password
credentials = base64.b64encode("%s:%s" % (username, password))
#/(qs.6) Set the content-type and credentials
headers = {"Content-Type" : "application/json",
           "Authorization" : "Basic " + credentials}
#/(qs.7) Send the request
conn.request(method, path, "", headers)
#/(qs.8) Receive the response.
response = conn.getresponse()
if response.status > 299:
    print "Error executing API call (%d): %s" % (response.status,
                                                 response.read())
    sys.exit(2)

#/(qs.9) Decode response
resp_payload = json.loads(response.read())

#/(qs.10) Display queue statistics
print "'%s' Queue Stats" % urllib.unquote(queue_name)
print "-----------------"
print "\tMemory Used (bytes): " + str(resp_payload["memory"])
print "\tConsumer Count: " + str(resp_payload["consumers"])
print "\tMessages:"
print "\t\tUnack'd: " + str(resp_payload["messages_unacknowledged"])
print "\t\tReady: " + str(resp_payload["messages_ready"])
print "\t\tTotal: " + str(resp_payload["messages"])

sys.exit(0)
########NEW FILE########
__FILENAME__ = user_manager
###############################################
# RabbitMQ in Action
# Chapter 9 - RMQ User Manager
###############################################
# 
#   USAGE: 
#       # user_vhost_manager.py "host" "auth_user" "auth_pass" create 'user' 'password' 'true/false'
#                               "host" "auth_user" "auth_pass" delete 'user'
#                               "host" "auth_user" "auth_pass" list
#                               "host" "auth_user" "auth_pass" show 'user'
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, httplib, base64

#/(um.1) Assign arguments
if len(sys.argv) < 5:
    print "USAGE: user_manager.py server_name:port auth_user auth_pass",
    print "ACTION [PARAMS...]"
    sys.exit(1)

server, port = sys.argv[1].split(":")
username = sys.argv[2]
password = sys.argv[3]
action = sys.argv[4]

if len(sys.argv) > 5:
    res_params = sys.argv[5:]
else:
    res_params = []

#/(um.2) Build API path
base_path = "/api/users"

if action == "list":
    path = base_path
    method = "GET"
if action == "create":
    path = base_path + "/" + res_params[0]
    method = "PUT"
if action == "delete":
    path = base_path + "/" + res_params[0]
    method = "DELETE"
if action == "show":
    path = base_path + "/" + res_params[0]
    method = "GET"


#/(um.3) Build JSON arguments
json_args = ""
if action == "create":
    json_args = {"password" : res_params[1],
                 "administrator" : json.loads(res_params[2])}
    json_args = json.dumps(json_args)

#/(um.4) Issue API request
conn = httplib.HTTPConnection(server, port)
credentials = base64.b64encode("%s:%s" % (username, password))
conn.request(method, path, json_args,
             {"Content-Type" : "application/json",
              "Authorization" : "Basic " + credentials})
response = conn.getresponse()
if response.status > 299:
    print "Error executing API call (%d): %s" % (response.status,
                                                 response.read())
    sys.exit(2)

#/(um.5) Parse and display response
resp_payload = response.read()
if action in ["list", "show"]:
    resp_payload = json.loads(resp_payload)
    
    #/(um.6) Process 'list' results
    if action == "list":
        print "Count: %d" % len(resp_payload)
        for user in resp_payload:
            print "User: %(name)s" % user
            print "\tPassword: %(password_hash)s" % user
            print "\tAdministrator: %(administrator)s\n" % user
    
    #/(um.7) Process 'show' results
    if action == "show":
        print "User: %(name)s" % resp_payload
        print "\tPassword: %(password_hash)s" % resp_payload
        print "\tAdministrator: %(administrator)s\n" % resp_payload
#/(um.8) Create and delete requests have no result.
else:
    print "Completed request!"

sys.exit(0)
########NEW FILE########
__FILENAME__ = user_vhost_manager
###############################################
# RabbitMQ in Action
# Chapter 9 - RMQ User & Vhost Manager
# 
#   USAGE: 
#       # user_vhost_manager.py "host" "auth_user" "auth_pass" create vhost 'vhostname'
#                               "host" "auth_user" "auth_pass" delete vhost 'vhostname'
#                               "host" "auth_user" "auth_pass" list vhost
#                               "host" "auth_user" "auth_pass" show vhost 'vhostname'
#                               "host" "auth_user" "auth_pass" create user 'user' 'password' 'true/false'
#                               "host" "auth_user" "auth_pass" delete user 'user'
#                               "host" "auth_user" "auth_pass" list user
#                               "host" "auth_user" "auth_pass" show user 'user'
#                               "host" "auth_user" "auth_pass" show permission 'user' 'vhost'
#                               "host" "auth_user" "auth_pass" create permission 'user' 'vhost' 'read' 'write' 'configure'
# 
# Author: Jason J. W. Williams
# (C)2011
###############################################
import sys, json, httplib, base64

base_path = "/api/%ss"

#/(uvm.1) Assign arguments
if len(sys.argv) < 6:
    print "USAGE: user_vhost_manager.py server_name:port auth_user auth_pass",
    print "ACTION RESOURCE [PARAMS...]"
    sys.exit(1)

server, port = sys.argv[1].split(":")
username = sys.argv[2]
password = sys.argv[3]
action = sys.argv[4]
res_type = sys.argv[5]

if len(sys.argv) > 6:
    res_params = sys.argv[6:]
else:
    res_params = []

#/(uvm.2) Connect to server
conn = httplib.HTTPConnection(server, port)

#/(uvm.3) Build API request
if action == "list":
    path = base_path % res_type
    method = "GET"
else:
    if res_type == "permission":
        path = (base_path % res_type) + ("/%s/%s" % (res_params[0],
                                                     res_params[1])) 
    else:
        path = (base_path % res_type) + "/" + res_params[0]
    
    if action == "create":
        method = "PUT"
    elif action == "delete":
        method = "DELETE"
    elif action == "show":
        method = "GET"


#/(uvm.4) Build JSON arguments
json_args = ""
if action == "create" and res_type == "user":
    json_args = {"password" : res_params[1],
                 "administrator" : json.loads(res_params[2])}
    json_args = json.dumps(json_args)

if action == "create" and res_type == "permission":
    json_args = {"read" : res_params[2],
                 "write" : res_params[3],
                 "configure" : res_params[4]}
    json_args = json.dumps(json_args)

#/(uvm.5) Issue API call
credentials = base64.b64encode("%s:%s" % (username, password))
conn.request(method, path, json_args,
             {"Content-Type" : "application/json",
              "Authorization" : "Basic " + credentials})
response = conn.getresponse()
if response.status > 299:
    print "Error executing API call (%d): %s" % (response.status,
                                                 response.read())
    sys.exit(2)

#/(uvm.6) Parse and display response
resp_payload = response.read()
if action in ["list", "show"]:
    resp_payload = json.loads(resp_payload)
    
    #/(uvm.7) Process 'list' results
    if action == "list":
        print "Count: %d" % len(resp_payload)
        if res_type == "vhost":
            for vhost in resp_payload:
                print "Vhost: %(name)s" % vhost
        elif res_type == "user":
            for user in resp_payload:
                print "User: %(name)s" % user
                print "\tPassword: %(password_hash)s" % user
                print "\tAdministrator: %(administrator)s\n" % user
    
    #/(uvm.8) Process 'show' results
    elif action == "show":
        if res_type == "vhost":
            print "Vhost: %(name)s" % resp_payload
        elif res_type == "user":
            print "User: %(name)s" % resp_payload
            print "\tPassword: %(password_hash)s" % resp_payload
            print "\tAdministrator: %(administrator)s\n" % resp_payload
        elif res_type == "permission":
            print "Permissions for '%(user)s' in '%(vhost)s'..." % resp_payload
            print "\tRead: %(read)s" % resp_payload
            print "\tWrite: %(write)s" % resp_payload
            print "\tConfig: %(configure)s" % resp_payload
else:
    print "Completed request!"

sys.exit(0)
########NEW FILE########
