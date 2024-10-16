import pika

# Connection parameters
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare the Orders exchange
channel.exchange_declare(exchange='Orders', exchange_type='topic', durable=True)

# Publish a message to the Orders exchange
order_message = "New Order: Stock XYZ"
channel.basic_publish(exchange='Orders', routing_key='order.new', body=order_message)

print(f" [x] Sent '{order_message}' to Orders exchange.")

# Close the connection
connection.close()
