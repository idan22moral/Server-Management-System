import socket
import threading
import pickle
import os

LISTEN_PORT = 1337
CHUNK_SIZE = 1024

client_threads = []

def recv_data_in_chunks(sock, total_size, chunk_size):
    '''
    This function recieves data of size total_size using given socket in chunks of chunk_size.
    '''
    data = b''

    # While we didn't recieve the whole data, continue recieving it 
    while len(data) < total_size:
        new_data = sock.recv(chunk_size)
        data = data + new_data
    return data

def json_to_folder(folder_json, relative_path=''):
    '''
    This function converts the given json-formatted data to a folder and saves it.
    The format is:
        {
            "type" : "folder",
            "name" : "the name of the folder",
            "entries" : [
                {
                    "type" : "file",
                    "name" : "the name of the file",
                    "data" : "either textual or binary data"
                },
                {
                    "type" : "folder",
                    "name" : "the name of the folder",
                    "entries" : [...]
                },
                ...
            ] 
        }
    '''

    # Prepare the relative_path for a recursive call or a entry saving
    relative_path += folder_json['name'] + '/'

    # Create directory for the folder
    print('Creating dir...')
    try:
        os.mkdir(relative_path)
    except:
        # The folder already exists, let the client know that he should rename it
        return 'RENAME'

    # Wait until the system creates the folder        
    while not os.path.exists(relative_path):
        pass
    print('Dir Created!')

    # For each entry in the folder's entry-list
    for entry in folder_json['entries']:
        if entry['type'] == 'file':
            # Write the data to the file
            open(relative_path + entry['name'], "wb").write(entry['data'])
        elif entry['type'] == 'folder':
            # Convert the json to a folder recursively
            json_to_folder(entry, relative_path)
    return 'DONE'

def handle_client(client_socket, client_addr):
    '''
    This function handles a connection to a client that wants to host a website.
    '''

    print('%s: Connected!' % (str(client_addr)))

    # Get the serialized data *length* from the client
    data_length = int(client_socket.recv(CHUNK_SIZE).decode())

    # Agree or deny to receive the data
    if data_length > 0:
        print('%s: OK (%d bytes)' % (str(client_addr), data_length))
        client_socket.send(b'OK') 
    else:
        print('%s: DENIED' % (str(client_addr)))
        client_socket.send(b'DENIED')
        return None

    print('%s: Recieving and deserializing data...' % (str(client_addr)))
    
    # Recieve the folder data from the client and deserialize it
    serialized_data = recv_data_in_chunks(client_socket, data_length, CHUNK_SIZE)
    website_folder_json = pickle.loads(serialized_data)

    print('%s: Creating folder...' % (str(client_addr)))
    
    # Save the folder and make sure that it has an unique name
    while json_to_folder(website_folder_json) == 'RENAME':
        client_socket.send(b'RENAME')
        new_name = client_socket.recv(CHUNK_SIZE).decode().split(':')[1]
        website_folder_json['name'] = new_name
    
    # End the client serving
    client_socket.send(b'DONE')
    print('Finished serving %s' % (str(client_addr)))

def main():
    # Initialize the listening socket and start listening for clients
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.bind(('localhost', LISTEN_PORT))
    listening_socket.listen()
    print('Listening for clients on port %d...' % (LISTEN_PORT))
    
    while True:
        # Accept a client, create a thread for him and start handling his connection
        client_socket, client_address = listening_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_threads.append(client_thread)
        client_thread.start()

    # Make sure that all the clients' threads are closed
    for thead in client_threads:
        thead.join()

if __name__ == "__main__":
    main()