import pika

def callback(ch, method, properties, body):
    print(f" [x] Received {body.decode()}")

# Connection parameters
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare the Orders exchange and queue
channel.exchange_declare(exchange='Orders', exchange_type='topic')
result = channel.queue_declare('', exclusive=True)  # Create a temporary queue
queue_name = result.method.queue

# Bind the queue to the Orders exchange with a routing key
channel.queue_bind(exchange='Orders', queue=queue_name, routing_key='order.new')

print(' [*] Waiting for messages. To exit press CTRL+C')

# Start consuming messages
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
channel.start_consuming()
