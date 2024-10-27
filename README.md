# PBT205 - Trading System

## Install Required Packages

1. Use pip to install the pika library, which is needed to interact with RabbitMQ:
   ```bash
   pip install pika
   ```

## Setup Instructions

1. Install and Configure Docker

2. Install RabbitMQ:
   ```bash
   docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management
   ```

3. Check RabbitMQ is running in Docker

4. Clone the application from GitHub:
   ```bash
   # Default clone to user folder
   git clone https://github.com/Cloud090/PBT205.git

   # Or clone to custom directory
   git clone https://github.com/Cloud090/PBT205.git [desired_clone_directory_here]
   ```

5. Open the project directory in CMD:
   ```bash
   cd PBT205  # or your custom directory
   ```

6. Switch to the Karma branch:
   ```bash
   git checkout Karma
   ```

7. Ensure code is up to date:
   ```bash
   git pull
   ```

## How to Run exchange.py

1. Command format:
   ```bash
   Python exchange.py <host>
   ```
   Example:
   ```bash
   Python exchange.py localhost
   ```

2. Expected terminal activity:
   
   exchange.py will listen for order, attempt to match them, and log each step, as shown below.
   ```
   Matching order: {'username': 'joe', 'side': 'sell', 'quantity': 10, 'price': 100.0, 'stock_symbol': 'XYZ'}
   Order added to book: {'username': 'joe', 'side': 'sell', 'quantity': 10, 'price': 100.0, 'stock_symbol': 'XYZ'}
   ```

3. Trade Confirmation:
   ```
   Matching order: {'username': 'joe', 'side': 'sell', 'quantity': 10, 'price': 100.0, 'stock_symbol': 'XYZ'}
   Order added to book: {'username': 'joe', 'side': 'sell', 'quantity': 10, 'price': 100.0, 'stock_symbol': 'XYZ'}
   Matching order: {'username': 'alex', 'side': 'buy', 'quantity': 10, 'price': 100.0, 'stock_symbol': 'XYZ'}
   Checking existing order: 100.0
   [x] Trade published: {"buyer": "alex", "seller": "joe", "stock_symbol": "XYZ", "price": 100.0, "quantity": 10}
   Trade published: alex with joe for 10 @ $100.0
   ```

## How to Run SendOrder.py

1. Command format:
   ```bash
   python SendOrder.py [username] [middleware_endpoint] [side(buy/sell)] [quantity] [price]
   ```
   Example:
   ```bash
   python SendOrder.py john localhost BUY 10 100
   ```

2. The program will confirm the order:
   ```
   [x] Sent Order: {"username": "joe", "side": "buy", "quantity": 10, "price": 100.0, "stock_symbol": "XYZ"}
   ```

3. SendOrder.py will now exit