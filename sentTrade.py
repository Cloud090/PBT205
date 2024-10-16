import pika
import argparse

def send_trade(username, stock_symbol, price, quantity=100):
    # Connect to RabbitMQ middleware
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declare the Trades exchange
    channel.exchange_declare(exchange='Trades', exchange_type='direct')

    # Create the trade message
    trade_message = f"{username},{stock_symbol},{quantity},{price}"

    # Publish the message to the 'Trades' exchange
    channel.basic_publish(exchange='Trades', routing_key='trades', body=trade_message)

    print(f"[x] Sent Trade: {trade_message}")

    # Close the connection
    connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a trade to RabbitMQ.")
    parser.add_argument("username", type=str, help="The username of the trader")
    parser.add_argument("stock_symbol", type=str, help="The stock symbol being traded")
    parser.add_argument("price", type=float, help="The price of the trade")
    parser.add_argument("--quantity", type=int, default=100, help="The quantity of the trade (default: 100)")

    args = parser.parse_args()
    
    # Call send_trade with parsed arguments
    send_trade(args.username, args.stock_symbol, args.price, args.quantity)
