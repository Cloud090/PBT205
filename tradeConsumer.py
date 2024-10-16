import pika

def callback(ch, method, properties, body):
    # This function will be called when a message is received
    trade_message = body.decode()
    print(f"[x] Received Trade: {trade_message}")

def consume_trades():
    # Connect to RabbitMQ middleware
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declare the Trades exchange and queue
    channel.exchange_declare(exchange='Trades', exchange_type='direct')
    channel.queue_declare(queue='trades_queue')
    
    # Bind the queue to the Trades exchange
    channel.queue_bind(exchange='Trades', queue='trades_queue', routing_key='trades')

    # Set up subscription to the queue
    channel.basic_consume(queue='trades_queue', on_message_callback=callback, auto_ack=True)

    print(" [*] Waiting for trades. To exit press CTRL+C")
    # Start consuming messages
    channel.start_consuming()

if __name__ == "__main__":
    consume_trades()
