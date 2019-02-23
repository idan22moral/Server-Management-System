import sys
import re
import os, os
import socket
import json, pickle
import zipfile, shutil

ARGS_LEN = 3
IP_PATTERN = r'^((1[0-9]{2}|2[0-4][0-9]|25[0-5]|[0-9]{1,2})\.){3}(1[0-9]{2}|2[0-4][0-9]|25[0-5]|[0-9]{1,2})$'
SERVER_PORT = 1337
CHUNK_SIZE = 1024

def validate_args():
    '''
    This function validates the sys.argv arguments that the user gave to the program.
    '''

    # Check if the args amount is valid
    if len(sys.argv) != ARGS_LEN:
        print('\nError:\tInvalid syntax.')
        print('Try:\tpython %s <server_ip> <website_folder_path>\n' % (__file__))
        return False

    # Check if the given IP address is valid
    if re.match(IP_PATTERN, sys.argv[1]) == None:
        print('\nError:\tInvalid IP address.')
        print('Note:\ta.b.c.d, where a-d are numbers between 0-255 (like 172.160.14.0)\n')
        return False

    # Check if the given path exists
    if not os.path.exists(sys.argv[2]):
        print('\nError:\tWebsite Folder does not exist.')
        print('Try giving an existing website folder.\n')
        return False

    # Check if the given path is a folder
    if not os.path.isdir(sys.argv[2]):
        print('\nError:\tThe given path is not a folder.')
        print('Try giving an path to a website folder instead.\n')
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
    folder_json = {'type' : 'folder', 'name' : folder_path.split('/')[-1]}
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
    data_length = len(data)
    
    print('Data length: %d' % (data_length))

    # Run through the data list and jump chunk_size elements every time
    # Then send the current chunk, until you get to the last chunk and send the rest of the bytes
    for i in range(0, chunk_size * (data_length // chunk_size) + 1, chunk_size):
        data_to_send = data[i:i + chunk_size]
        sock.send(data_to_send)
        print('Sent: %d' % (len(data_to_send)))

def main():
    # Make sure that the format of the arguments is valid
    if not validate_args():
        return None

    # Save the console arguments in variables
    server_ip = sys.argv[1]
    website_folder_path = sys.argv[2]

    # Convert the given folder to dictionary (json format)
    website_folder_json = folder_to_json(website_folder_path)
    
    # Serialize the json for sending
    serialized_data = pickle.dumps(website_folder_json)

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
            print('Website name "%s" already taken.' % (website_folder_json['name']))
            new_name = input('Enter new name: ')
            website_folder_json['name'] = new_name
            connection_socket.send(b'NEWNAME:' + new_name.encode())
        print('Done.')
    else:
        print('Failed.')
    
    # End the connection with the server
    connection_socket.close()


if __name__ == '__main__':
    main()