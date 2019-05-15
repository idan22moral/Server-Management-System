"""
Our Proxy-Protocol is based on a simple structure of a packet.
This agent is a simple implementation of the idea, and it should work on HTTP packets only.

The client sends a request in this format:
<ip_in_bytes><HTTP_method>...

For example, if the requesting ip is 56.104.74.10, the request in bytes will be:
ASCII:  8  h  J  \n H  T  T  P  ...
HEX:    38 68 4A 0A 48 54 54 50 ...
"""


import socket
import re

MAX_PACKET_SIZE = 1024
IP_REGEX = '(?P<src_address>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))'


def get_port(msg, excluded_ports=[]):
    """
    Receives port from the user, and returns it.
    Makes sure that the port is valid
    """
    port = None

    # Get a port from the user while the port is invalid
    while port is None:
        try:
            port = int(input(msg))

            # Check if the port is in the list of excluded ports
            if port in excluded_ports:
                print("You chose an excluded port.")
                port = None
        except:
            print("Invalid port. Try entering a number between 1 - 65535")
    return port


def main():
    local_server_port = get_port("Local server port: ")
    listen_port = get_port("Proxy port: ", excluded_ports=[local_server_port])

    # Create a listening socket
    with socket.socket() as listen_socket:
        # Bind the listening socket and start listening
        listen_socket.bind(("0.0.0.0", listen_port))
        listen_socket.listen()

        while True:
            # Accept a client and receive his request
            client_socket, addr = listen_socket.accept()
            packet_data = client_socket.recv(MAX_PACKET_SIZE)

            # Make sure that the request starts with an ip
            # The ip is the ip of the client that should be the final destination of the response
            packet_match = re.match((b'^(.{4})(GET|POST)'), packet_data)
            if packet_match is not None:
                # Take the bytes of the ip and save them for the response
                dst_ip = packet_match[:4]

                # Connect to the local server
                with socket.socket() as local_server_socket:
                    # Remove the ip from the beginning packet
                    # and send the rest of the packet as a pure HTTP request
                    local_server_port.send(packet_data[4:])

                    # Get the response from the local server
                    response_data = local_server_port.recv(MAX_PACKET_SIZE)

                    # Send the response to the client
                    # with the ip that we removed earlier
                    client_socket.send(dst_ip + response_data)
            else:
                # The packet is invalid to our proxy protocol
                # so there's no need to continue the connection with the client
                client_socket.close()


if __name__ == "__main__":
    main()
