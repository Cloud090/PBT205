import pika
import json

print("Welcome to the chat room")
def send_message(message):
    
    # connect to rabbitmq
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    # delcare exchange
    channel.exchange_declare(exchange='chat_exchange', exchange_type='topic')

    routing_key = "chat.general"  
    channel.basic_publish(exchange='chat_exchange', routing_key=routing_key, body=json.dumps({'sender': 'User1', 'message': message}))
    connection.close()    

if __name__ == '__main__':
  while True:
    message = input("Enter your message: ")
    send_message(message)
