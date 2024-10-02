

# chat_app.py
import json
import pika
import threading


class ChatApp:
    # RabbitMQ connection parameters
    RABBITMQ_HOST = 'localhost'
    RABBITMQ_PORT = 5672
    RABBITMQ_USERNAME = 'admin'
    RABBITMQ_PASSWORD = 'admin'

    def __init__(self, user_queue, partner_queue):
        self.user_queue = user_queue
        self.partner_queue = partner_queue

        self.credentials = pika.PlainCredentials(ChatApp.RABBITMQ_USERNAME, ChatApp.RABBITMQ_PASSWORD)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=ChatApp.RABBITMQ_HOST, port=ChatApp.RABBITMQ_PORT, credentials=self.credentials))
        self.receiver_thread = threading.Thread(target=self.start_receiver, args=(user_queue, )) # Create a thread for the receiver

        self.receiver_thread.start() # Start the thread



    def clear_message(self, channel, method, properties, body):
       
        print(f"Received message: {body.decode()}")
        channel.basic_ack(delivery_tag=method.delivery_tag)


    def start_receiver(self, queue_name):
        print('start_receiver')
    
        def callback(ch, method, properties, body):
            print('callback')
        
            self.clear_message(ch, method, properties, body)

        # set credentials
        credentials = self.credentials

        # set connection for
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=ChatApp.RABBITMQ_HOST, port=ChatApp.RABBITMQ_PORT, credentials=credentials))

        self.channel = connection.channel()

        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback)

        print(f" [*] Waiting for messages in {queue_name}. To exit press CTRL+C")
        self.channel.start_consuming()

    def send_message(self, queue_name, message):
        print('send_message')
        channel = self.connection.channel()

        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(exchange='', routing_key=queue_name, body=message)
        print(f" [x] Sent '{message}'")



if __name__ == '__main__':

    queue_name = input('Enter queue name: ')
    partner_queue = input('Enter partner queue name: ')

    chat_app = ChatApp(queue_name, partner_queue)
    while True:
        message = input('Enter message: ')
        chat_app.send_message(partner_queue, message)



