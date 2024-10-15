import pika
import json

def on_message(ch, method, properties, body):
    data = json.loads(body)
    sender = data['sender']
    message = data['message']
    print(f"{sender}: {message}")

def main():
    # connection to rabbitmq
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    # declare exchange
    channel.exchange_declare(exchange='chat_exchange', exchange_type='topic')

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    binding_key = "chat.#"  # Bind to all chat-related messages
    channel.queue_bind(exchange='chat_exchange', queue=queue_name, routing_key=binding_key)

    print(' [*] Waiting for messages. To exit press CTRL+C')

    channel.basic_consume(queue=queue_name, on_message_callback=on_message, auto_ack=True)

    channel.start_consuming()

if __name__ == '__main__':
    main()