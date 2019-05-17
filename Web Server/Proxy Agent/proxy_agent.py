"""
Our Proxy-Protocol is based on a simple structure of a packet.
This agent is a simple implementation of the idea, and it should work on HTTP packets only.

The client sends a request in this format:
<ip_in_bytes><port_in_bytes><HTTP_method>...

For example, if the requesting ip is 56.104.74.10 and the port is 7070, the request in bytes will be:
       |--------IP--------|---PORT---|---------DATA---------|          
ASCII:  8    h    J    \n   \x1b \x9e H    T    T    P  ...
HEX:    38   68   4A   0A   1b   9e   48   54   54   50 ...
"""


import socket
import re

MAX_PACKET_SIZE = 1024
IP_REGEX = '(?P<src_address>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))'
ENDPOINT_LENGTH = 6  # Length in bytes
VALID_HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT',
                      'DELETE', 'TRACE', 'OPTIONS', 'CONNECT', 'PATCH']


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
    proxy_response_port = get_port("Proxy server port: ")
    listen_port = get_port("Agent port: ", excluded_ports=[local_server_port])

    # Create a listening socket
    with socket.socket() as listen_socket:
        # Bind the listening socket and start listening
        listen_socket.bind(("0.0.0.0", listen_port))
        listen_socket.listen()

        while True:
            # Accept a client, receive his request and close the connection
            proxy_request_socket, proxy_address = listen_socket.accept()
            packet_data = proxy_request_socket.recv(MAX_PACKET_SIZE)
            proxy_request_socket.close()

            # Make sure that the request starts with an ip
            # The ip is the ip of the client that should be the final destination of the response
            # Example of matching request: '8hJ\n\x1b\x9ePOST / HTTP/1.1 ...'
            packet_match = re.match(f'^(.{{6}})({'|'.join(VALID_HTTP_METHODS)})'.encode(), packet_data)
            if packet_match is not None:
                # Take the bytes of the endpoint and save them for the response
                dst_endpoint = packet_match[:ENDPOINT_LENGTH]

                with socket.socket() as local_server_socket:
                    # Connect to the local server
                    local_server_socket.connect(("0.0.0.0", local_server_port))

                    # Remove the ip from the beginning packet
                    # and send the rest of the packet as a pure HTTP request
                    local_server_socket.send(packet_data[ENDPOINT_LENGTH:])

                    # Get the response from the local server
                    # This is a time consuming action, it should be done in a thread
                    response_data = local_server_socket.recv(MAX_PACKET_SIZE)

                    with socket.socket() as proxy_response_socket:
                        # Connect to the proxy server
                        proxy_response_socket.connect(
                            (proxy_address[0], proxy_response_port))

                        # Send the response to the proxy with
                        # the ip that we removed earlier
                        proxy_response_socket.send(
                            dst_endpoint + response_data)
            else:
                # The packet is invalid to our proxy protocol
                # so there's no need to continue the connection with the client
                proxy_request_socket.close()


if __name__ == "__main__":
    main()
