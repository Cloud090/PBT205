# PBT205
Usage for chat application

# install rabbitmq-server on Linux
sudo apt install rabbitmq-server

# start rabbitmq server
service rabbitmq-server start

# on browser go to URL
http://localhost:15672  -login with guest:guest

# on a terminal -run the file server.py   - will start waiting for clients to send messages
python3 server.py

# on another terminal -run the file client.py  - client can type and send  messages.
python3 client.py username - example python3 client.py Tim
# user Tim is added to the chatroom
# Tim can now send messages and they will be displayed in the terminal running the server.py

# on another terminal -run the file client.py 
python3 client.py username - example python3 client.py james
# user James is added to the chatroom
# James can now send messages and they will be displayed in the terminal running the server.py and will be displayed in Tims chatroom



