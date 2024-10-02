'''
devoriales.com
https://devoriales.com/post/249

This is the second part of the tutorial on how to create a chat application with Python and RabbitMQ. 
In the first part, we created a simple chat application that allowed users to send messages to a queue. 
In this part, we will create a chat application that allows users to send messages to each other.

'''

# chat_app.py
import json
import pika
import threading


class ChatApp:
    # RabbitMQ connection parameters
    RABBITMQ_HOST = 'localhost'
    RABBITMQ_PORT = 5672
    RABBITMQ_USERNAME = 'guest'
    RABBITMQ_PASSWORD = 'guest'

    def __init__(self, user_queue, partner_queue):
        self.user_queue = user_queue
        self.partner_queue = partner_queue

        self.credentials = pika.PlainCredentials(ChatApp.RABBITMQ_USERNAME, ChatApp.RABBITMQ_PASSWORD)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=ChatApp.RABBITMQ_HOST, port=ChatApp.RABBITMQ_PORT, credentials=self.credentials))
        self.receiver_thread = threading.Thread(target=self.start_receiver, args=(user_queue, )) # Create a thread for the receiver

        self.receiver_thread.start() # Start the thread



    def clear_message(self, channel, method, properties, body):
        '''
        This function is called when a message is received by the consumer.
        It prints the message to the console and acknowledges the message to the broker.
        The broker will delete the message from the queue.
        :param channel:
        :param method:
        :param properties:
        :param body:
        :return:
        '''
        print(f"Received message: {body.decode()}")
        channel.basic_ack(delivery_tag=method.delivery_tag)


    def start_receiver(self, queue_name):
        print('start_receiver')
        '''
        This function starts a consumer that listens to the queue and calls the on_message function when a message is received.
        It blocks the main thread, so it should be run in a separate thread.
        :param queue_name:
        :return:
        '''
        def callback(ch, method, properties, body):
            print('callback')
            '''
            This function is called when a message is received by the consumer.
            The parameters are passed by the Pika library, not from the code.
            :param ch:
            :param method:
            :param properties:
            :param body:
            :return:
            '''
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



