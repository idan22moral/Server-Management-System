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

MAX_PACKET_SIZE = 65536
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


def recv_dynamic_data(sock, chunk_size):
    '''
    This function recieves data of size total_size using given socket in chunks of chunk_size.
    '''
    full_data = b''

    # Receive the length of the data
    total_size_in_bytes = sock.recv(4) # 4 is the length of int in bytes
    # Convert the byte-formatted total size to int
    total_size = int.from_bytes(total_size_in_bytes, byteorder="big", signed=False)

    # Recieve the data pieces and join them together
    while len(full_data) < total_size:
        chunk_data = sock.recv(chunk_size)
        print(f"Recieved {len(chunk_data)}")
        full_data = full_data + chunk_data
    
    # Return the data
    return full_data


def send_dynamic_data(sock, data, chunk_size):
    '''
    This function sends the given data in chunks of size chunk_size using the given socket.
    '''
    # Get the length of the data
    data_length = len(data)
    # Convert the length (int) to bytes and send the length of the data
    sock.send((data_length).to_bytes(4, byteorder="big"))

    # Run through the data list and jump chunk_size elements every time
    # Stop when you get to the last chunk, then send the rest of the bytes
    for i in range(0, chunk_size * (data_length // chunk_size) + 1, chunk_size):
        data_to_send = data[i:i + chunk_size]
        sock.send(data_to_send)


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
            print("Accepting client...")
            proxy_request_socket, proxy_address = listen_socket.accept()
            print("Client connected:", proxy_address)
            packet_data = b''
            try:
                packet_data = proxy_request_socket.recv(MAX_PACKET_SIZE)
            except:
                print("Connection failed.")
                continue
            print("Request:", packet_data[:32])
            proxy_request_socket.close()

            # Make sure that the request starts with an ip
            # The ip is the ip of the client that should be the final destination of the response
            # Example of matching request: '8hJ\n\x1b\x9ePOST / HTTP/1.1 ...'
            packet_match = re.match(f'^(.{{6}})({"|".join(VALID_HTTP_METHODS)})'.encode(), packet_data)
            if packet_match is not None:
                # Take the bytes of the endpoint and save them for the response
                dst_endpoint = packet_match.group(1)

                with socket.socket() as local_server_socket:
                    # Connect to the local server
                    print("connecting to", ("localhost", local_server_port))
                    local_server_socket.connect(("localhost", local_server_port))

                    # Remove the ip from the beginning packet
                    # and send the rest of the packet as a pure HTTP request
                    print("sending request:", packet_data[ENDPOINT_LENGTH:32])
                    local_server_socket.send(packet_data[ENDPOINT_LENGTH:])

                    # Get the response from the local server
                    # This is a time consuming action, it should be done in a thread
                    print("receiving response")
                    response_data = local_server_socket.recv(MAX_PACKET_SIZE)
                    print("response:", packet_data[ENDPOINT_LENGTH:32])
                    with socket.socket() as proxy_response_socket:
                        # Connect to the proxy server
                        print("connecting to proxy to respond")
                        proxy_response_socket.connect(
                            (proxy_address[0], proxy_response_port))
                        print("connected to proxy on", (proxy_address[0], proxy_response_port))
                        # Send the response to the proxy with
                        # the ip that we removed earlier
                        print("sending response to proxy", (proxy_address[0], proxy_response_port))
                        proxy_response_socket.send(
                            dst_endpoint + response_data)
                        proxy_response_socket.close()
                        print("sent response: ", dst_endpoint + response_data[:32])
                    local_server_socket.close()
            else:
                # The packet is invalid to our proxy protocol,
                # so there's no need to continue the connection with the client.
				# The socket is already closed, so there's no need to close
                print("INVALID PACKET:", packet_data)
                pass


if __name__ == "__main__":
    main()
