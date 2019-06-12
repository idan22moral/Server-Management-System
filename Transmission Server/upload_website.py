import sys
import re
import os
import socket
import pickle
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
import threading
import time

AES_ENCRYPTION_KEY = b"N44vCTcb<W8sBXD@"
AES_BLOCKSIZE = 16
AES_IV = b"PoTFg9ZlV?g(bH8Z"

MIN_ARGS_LEN = 3
IP_PATTERN = r'^((1[0-9]{2}|2[0-4][0-9]|25[0-5]|[0-9]{1,2})\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[0-9]{1,2})$'
SERVER_PORT = 1337
CHUNK_SIZE = 16384

websites = []
server_ips = []

def validate_args():
    '''
    This function validates the sys.argv arguments that the user gave to the program.
    '''

    # Check if the args amount is valid
    if len(sys.argv) < MIN_ARGS_LEN:
        print('\nError:\tInvalid syntax.')
        print('\nUSAGE\n\tpython %s websites_folder_path server_ip [server_ip2 server_ip3 ...]\n' % (__file__))
        
        print('NOTES\n\twebsites_folder_path\tThe folder in which the user would be able to upload website-folders to.')
        print('\tserver_ip\t\tThe ip of the server that the website will be uploaded to.\n')
        
        print('EXAMPLES\n\tSingle server:\t\tpython %s WebsiteExampleFolder 192.168.0.45\n' % (__file__))
        print('\tMultiple servers:\tpython %s WebsiteExampleFolder 192.168.0.45 192.168.0.88\n' % (__file__))
        return False

    # Check if the given path exists
    if not os.path.exists(sys.argv[1]):
        print('\nError:\tWebsite Folder does not exist.')
        print('Try giving an existing folder.\n')
        return False

    # Check if the given path is a folder
    if not os.path.isdir(sys.argv[1]):
        print('\nError:\tThe given path is not a folder.')
        print('Try giving an path in which website folders will be stored.\n')
        return False

    # Check if the given IP addresses are valid
    for ip_address in sys.argv[2:]:
        if re.match(IP_PATTERN, ip_address) == None:
            print('\nError:\tInvalid IP address.')
            print('Note:\ta.b.c.d, where a-d are numbers between 0-255 (like 172.160.14.0)\n')
            return False
    return True


def folder_to_json(folder_path):
    '''
    This function converts the data in a given folder to json format.
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

    # Make sure that the folder path is in valid format
    folder_path = os.path.abspath(folder_path)
    
    # Initialize the folder dictionary
    folder_json = {'type' : 'folder', 'name' : os.path.basename(folder_path)}
    folder_json['entries'] = []
    
    # For each entry in the current folder
    for entry in os.listdir(folder_path):
        entry_full_path = folder_path + '/' + entry
        
        # If the entry is a file, save the file's name and data in dictionary
        if os.path.isfile(entry_full_path):
            file_json = {'type' : 'file', 'name': entry}
            file_data = open(entry_full_path, "rb").read()
            file_json['data'] = file_data
            # Add the file dictionary to the entries of the current folder
            folder_json['entries'].append(file_json)
        
        # If the entry is a folder, get the folder's dictionary recursively, and add it
        elif os.path.isdir(entry_full_path):
            folder_json['entries'].append(folder_to_json(entry_full_path))
    return folder_json


def send_data_in_chunks(sock, data, chunk_size):
    '''
    This function sends the given data in chunks of size chunk_size using the given socket.
    '''
    
    # Encrypt the data
    encrypted_data = encrypt_data(data)
    data_length = len(encrypted_data)
    
    print('Data length: %d' % (data_length))

    # Run through the data list and jump chunk_size elements every time
    # Stop when you get to the last chunk, then send the rest of the bytes
    for i in range(0, chunk_size * (data_length // chunk_size) + 1, chunk_size):
        data_to_send = encrypted_data[i:i + chunk_size]
        sock.send(data_to_send)
        print(f"Sent: {len(data_to_send)}")


def encrypt_data(data):
    '''
    This function uses the Cryptodome.Cipher library to encrypt the given data using the AES algoritm.
    Note: AES is out dated. The only reason Im using AES is that it's simple for educational purposes.
    '''

    # Create an instance of a AES object that let's us encrypt our data
    # key - The encryption key. Random string hard-coded at the top of the code.
    #       Note: The same key must be used in the decrypting endpoint, and the key's length must be 8.
    # IV - The initial value for the encryption.
    #       Note: The same IV must be used in the decrypting endpoint, and the IV's length must be 8.
    AES_encryptor = AES.new(AES_ENCRYPTION_KEY, AES.MODE_CBC, AES_IV)
    
    # Pad the data to be in length of a multiple of the AES_BLOCKSIZE
    # Encrypt the given data, then return it
    return AES_encryptor.encrypt(pad(data, AES_BLOCKSIZE))


def upload_website(website_folder_path):
    # Convert the given folder to dictionary (json format)
    website_folder_json = folder_to_json(website_folder_path)
    print('passed')
    # Serialize the json for sending
    serialized_data = pickle.dumps(website_folder_json)
    print(server_ips)
    for server_ip in server_ips:
        # Initiate connection to endpoint server
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.connect((server_ip, SERVER_PORT))

        # Send the serialized data *length* to the server
        connection_socket.send(str(len(serialized_data)).encode())

        # Recieve an agreement to send the data
        agreement = connection_socket.recv(CHUNK_SIZE)
        
        if agreement == b'OK':
            # Send the folder data in chunks
            send_data_in_chunks(connection_socket, serialized_data, CHUNK_SIZE)
            
            # Rename the folder while the name is already taken
            while connection_socket.recv(CHUNK_SIZE) == b'RENAME':
                print('Website name "%s" already taken.' % (os.path.basename(website_folder_json['name'])))
                new_name = input('Enter new name: ')
                website_folder_json['name'] = os.path.join(os.path.dirname(website_folder_json['name']), new_name)
                connection_socket.send(b'NEWNAME:' + new_name.encode())
            print('Done.')
        else:
            print('Failed.')
        
        # End the connection with the server
        connection_socket.close()


def main():
    # Make sure that the format of the arguments is valid
    if not validate_args():
        return None

    # Save the console arguments in variables
    global server_ips
    server_ips = sys.argv[2:]
    websites_folder_path = sys.argv[1]

    # Check which websites are already in the websites folder
    websites = os.listdir(websites_folder_path)

    # Wait for the user to add a folder to the websites folder
    while True:
        # Check if there's a change in the websites folder
        current_websites = os.listdir(websites_folder_path)
        if current_websites != websites:
            new_websites = []
            # Add all the new websites to the list
            for website in current_websites:
                if website not in websites:
                    new_websites.append(website)
            
            # For each new website
            for new_website in new_websites:
                # Upload the new website to the target(s)
                threading.Thread(target=upload_website, args=(f"{websites_folder_path}\{new_website}",)).start()
                # Add the new website to the list of websites
                websites.append(new_website)
        
        # Sleep for 1 second
        time.sleep(1)
        


if __name__ == '__main__':
    main()