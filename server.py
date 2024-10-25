# import libraries
import pika
import json

# The on_message function
def on_message(ch, method, properties, body):
    data = json.loads(body)
    sender = data['sender']
    message = data['message']
    print(f"{sender}: {message}")

# The main function
def main():
    # connection to rabbitmq
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', port= 5672))

    # create a channel
    channel = connection.channel()

    # declare exchange
    channel.exchange_declare(exchange='chat_exchange', exchange_type='topic')

    # create a temporary queue
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # binds the queue to the exchange
    binding_key = "chat.#" 
    channel.queue_bind(exchange='chat_exchange', queue=queue_name, routing_key=binding_key)
    
    # prints waiting messages
    print(' [*] Waiting for messages. To exit press CTRL+C')
    
    # starts consuming messages
    channel.basic_consume(queue=queue_name, on_message_callback=on_message, auto_ack=True)

    channel.start_consuming()

if __name__ == '__main__':
    main()
