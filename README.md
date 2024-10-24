# PBT205
Usage for chat application

For running on the windows operating system
# Download,  install docker and run docker

#In the docker terminal run the command
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management

#Download the ZIP file of the chat application from github to the local computer and unzip the file.
#Open the command prompt terminal on the computer
#Go to the location of downloaded folder that contains chat application files
# on a terminal -run the file server.py   - will start waiting for clients to send messages
python server.py

#Open another command prompt terminal on the computer
#Go to the location of downloaded folder that contains chat application files
run the file client.py  - client can type and send  messages.
python client.py username  (example - python client.py Tim)

# user Tim is added to the chatroom
# Tim can now send messages and they will be displayed in the terminal running the server.py

#Check the running server
#It displays the user Tim has joined the chat room and the message.

# on another terminal -run the file client.py
#Go to the location of downloaded folder that contains chat application files
python client.py username (example - python client.py james)

# user James is added to the chatroom
# James can now send messages and they will be displayed in the terminal running the server.py and will be displayed in Tims chatroom

#Check the running server
#It displays the user James has joined the chat room and the message.



