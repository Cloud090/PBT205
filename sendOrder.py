import pika
import argparse
import json

def send_order(username, middleware_endpoint, side, quantity, price, stock_symbol='XYZ'):
    # Connect to RabbitMQ middleware
    connection = pika.BlockingConnection(pika.ConnectionParameters(middleware_endpoint))
    channel = connection.channel()

    # Declare the Orders exchange
    channel.exchange_declare(exchange='Orders', exchange_type='direct', durable=True)

    # Create the order message
    order_message = {
        "username": username,
        "side": side,
        "quantity": quantity,
        "price": price,
        "stock_symbol": stock_symbol
    }

    # Publish the message to the 'Orders' exchange in JSON format
    channel.basic_publish(
        exchange='Orders', 
        routing_key='order.new', 
        body=json.dumps(order_message),
        properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
    )

    print(f"[x] Sent Order: {json.dumps(order_message)}")

    # Close the connection
    connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send an order to RabbitMQ.")
    parser.add_argument("username", type=str, help="The username of the trader")
    parser.add_argument("middleware_endpoint", type=str, help="The RabbitMQ middleware endpoint (e.g., 'localhost')")
    parser.add_argument("side", help="Order side ('BUY' or 'SELL')")
    parser.add_argument("quantity", type=int, help="The quantity of the order")
    parser.add_argument("price", type=float, help="The desired price for the order")

    args = parser.parse_args()
    # Normalise the side input to uppercase
    side = args.side.upper()

    # Validate that side is either 'BUY' or 'SELL'
    if side not in ['BUY', 'SELL']:
        print("Error: side must be either 'BUY' or 'SELL'.")
        exit(1)

    # Call send_order with parsed arguments
    send_order(args.username, args.middleware_endpoint, args.side, args.quantity, args.price)