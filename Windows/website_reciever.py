import socket
import threading
import pickle
import os
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

AES_ENCRYPTION_KEY = b"N44vCTcb<W8sBXD@"
AES_BLOCKSIZE = 16
AES_IV = b"PoTFg9ZlV?g(bH8Z"

LISTEN_PORT = 1337
CHUNK_SIZE = 16384
GOOGLE_DNS_IP = "8.8.8.8"
DNS_PORT = 53

client_threads = []

def recv_data_in_chunks(sock, total_size, chunk_size):
    '''
    This function recieves data of size total_size using given socket in chunks of chunk_size.
    '''
    full_data = b''

    # Recieve the data pieces and join them together
    while len(full_data) < total_size:
        chunk_data = sock.recv(chunk_size)
        print(f"Recieved {len(chunk_data)}")
        full_data = full_data + chunk_data
    
    # Return the decrypted data
    return decrypt_data(full_data)


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
    relative_path += os.path.basename(folder_json['name']) + '/'

    # Create directory for the folder
    print('%s: Creating...' % (relative_path))
    try:
        os.mkdir(relative_path)
    except:
        # The folder already exists, let the client know that he should rename it
        return 'RENAME'

    # Wait until the system creates the folder        
    while not os.path.exists(relative_path):
        pass
    print('%s: Created!' % (relative_path))

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

    print('%s: Recieving and Deserializing data...' % (str(client_addr)))
    
    # Recieve the folder data from the client and decrypt it
    serialized_data = recv_data_in_chunks(client_socket, data_length, CHUNK_SIZE)

    # Deserialize the folder data
    website_folder_json = pickle.loads(serialized_data)

    print('%s: Creating folder...' % (str(client_addr)))
    
    # Save the folder and make sure that it has an unique name
    while json_to_folder(website_folder_json) == 'RENAME':
        client_socket.send(b'RENAME')
        new_name = client_socket.recv(CHUNK_SIZE).decode().split(':')[1]
        website_folder_json['name'] = os.path.basename(new_name)
    
    # End the client serving
    client_socket.send(b'DONE')
    print('Finished serving %s' % (str(client_addr)))


def decrypt_data(data):
    '''
    This function uses the Cryptodome.Cipher library to encrypt the given data using the AES algoritm.
    Note: AES is out dated. The only reason Im using AES is that it's simple for educational purposes.
    '''

    # Create an instance of a AES object that let's us decrypt our data
    # key - The encryption key. Random string hard-coded at the top of the code.
    #       Note: The same key must be used in the encrypting endpoint, and the key's length must be 8.
    # IV - The initial value of the encryption.
    #       Note: According to the protocol of AES, the length of the IV must be a multiple of 8.
    aes_encryptor = AES.new(AES_ENCRYPTION_KEY, AES.MODE_CBC, AES_IV)

    # Encrypt the given data, then return it
    return unpad(aes_encryptor.decrypt(data), AES_BLOCKSIZE)


def get_my_ip():
    '''
    This function return the local IP of the current machine.
    '''
    
    # Create a UDP socket and connect to google's DNS service
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.connect((GOOGLE_DNS_IP, DNS_PORT))

    # Retrieve the ip of the current machine from the connected socket
    local_ip = udp_socket.getsockname()[0]
    return local_ip

def main():
    # Initialize the listening socket and start listening for clients
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    local_ip_address = get_my_ip()
    listening_socket.bind((local_ip_address, LISTEN_PORT))
    listening_socket.listen()
    print('Listening for clients on %s:%d...' % (local_ip_address, LISTEN_PORT))
    
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