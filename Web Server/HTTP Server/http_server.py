import socket
import re
import logging
import os
import sys
import mimetypes
import traceback


# Setup basic variables.
webroot_path = os.getcwd() + '\webroot\\'   # Website folder path
default_url = webroot_path + 'index.html'   # Default index.html path
http_version = 'HTTP/1.1'                   # Http version used
logger = None                               # Logger object (created in main)


def setup_logging(log_file_name: str):
    """
    Creates and returns a logger that can be used to
    log data to a file and to the console of the program.
    """

    # Set a logger & log formatter
    logger = logging.getLogger(__name__)
    logger.level = logging.DEBUG
    file_log_formatter = logging.Formatter(
        '%(asctime)s  %(levelname)s: %(message)s')
    console_log_formatter = logging.Formatter('%(asctime)s %(message)s')

    # Setup logging to a log file
    file_log_handler = logging.FileHandler(filename=log_file_name, mode='w')
    logger.addHandler(file_log_handler)
    logger.info(
        f'''my_http_server_log_file:
        Website path: {webroot_path}
        Default URL: {default_url}
    ''')
    file_log_handler.setFormatter(file_log_formatter)
    logger.addHandler(file_log_handler)

    # Setup logging to the console
    console_log_handler = logging.StreamHandler()
    console_log_handler.setFormatter(console_log_formatter)
    logger.addHandler(console_log_handler)

    return logger


def validate_http_request(client_socket: socket.socket):
    """  
    Determines weather or not the HTTP request is valid.
    If valid, it returns the sent method and resource string.

    Valid request   => (True, method, resource)
    Invalid request => (False, method, resource) 
    """

    # A (partial) list of valid http protocol request methods.
    valid_request_methods = ['GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE', 'OPTIONS', 'CONNECT', 'PATCH']

    # Recieve request data from the client
    request = client_socket.recv(1024)

    # Using regex to determine weather or not the request is valid
    # if re.match() returns a match object, the request is valid
    request = re.match(rb'(.+) (.+) HTTP/1.1\r\n(.*:.*)\r\n*', request)
    method = 'GET'
    resource = default_url

    # if re.match() returns None, the request is not a valid http request
    if request is None:
        return False, '', ''

    # Get the request method and path from the request
    request_method = request.group(1).decode()
    request_path = request.group(2).decode()

    logger.info(request_method + ' ' + request_path)

    try:
        # Check if the request method is a valid HTTP method
        if request_method in valid_request_methods:
            # There's no need to add anything to the resource path
            # if the client tries to reach '/'
            if request_path != '/':
                method = request_method
                resource = webroot_path + request_path

                # Cut the last '/' if it exists
                if resource[-1] == '/':
                    resource = resource[:-1]

                # Replace '/' with '\\' for windows compatibility.
                resource = resource.replace('/', '\\')
        else:
            return False, '', ''

        return True, method, resource

    except (IndexError, AttributeError, TypeError) as e:
        logger.critical(f'{e.message}\n\tResource: {resource}')


def handle_client_request(client_socket, method, resource):
    """
    Serves the given resource to the client if the resource is available.
    resource - the web page, file or other resource requested by the client.
    """
    # Get the resource type from the requested resource
    # Example for resource 'image13.jpg', the resource_type will be 'jpg'
    # rfind returns the index of the last appriance of the given substring
    resource_type = resource[resource.rfind('.') + 1:]

    # Check if the resource is safe (no "/.." in it), and the requested file (resource) exists
    if "/.." in resource or "\\.." in resource:
        # Requested resouce is unsafe
        logger.warning('!!! UNSAFE REQUEST !!!')
        status_code = 400
        phrase = 'Bad Request'
        headers = ''
        body = '<h1>Error 400 Bad Request.</h1>'
    elif not os.path.isfile(resource):
        # Resource not found, send code 404
        logger.warning('404 ' + resource.split(webroot_path)
                       [-1] + ' Not Found')

        status_code = '404'
        phrase = 'Not Found'
        headers = ''
        body = b'<h1>Error 404 File Not Found.</h1>'
    else:
        # Resource found, send code 200
        # and send the requested resource back to client
        logger.info('200 ' + resource.split(webroot_path)[-1] + ' Found')

        status_code = '200'
        phrase = 'OK'

        # Get the length of the resource file
        content_length = os.stat(resource).st_size

        # Get the content type using a simple library
        # that gives the content type for each extension file
        content_type = mimetypes.guess_type(f'file.{resource_type}')[0]
        content_type_is_known = content_type is not None

        # Make sure that the library gave us a content type
        if content_type_is_known:
            with open(resource, 'rb') as f:
                body = f.read()
        else:
            body = b''

        # Concatenate the headers
        headers = f'Content-Length: {content_length}\r\nContent-Type: {content_type}'

    # Example: HTTP/1.1 200 OK
    response_status = f'{http_version} {status_code} {phrase}'

    # Send response to client
    client_socket.send(response_status.encode() + b'\r\n' +
                       headers.encode() + b'\r\n\r\n' + body)
    logger.info(response_status)


def main():
    # Setup the logging for the console and log file
    global logger
    logger = setup_logging('log.txt')

    # Create a socket to listen to clients
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', 80)  # '0.0.0.0' stands for the local ip

    try:
        server_socket.bind(server_address)
    except Exception as e:
        print(e)
        return  # The server cannot bind to the address, so we need to close it

    # Start listening for clients
    server_socket.listen()
    logger.info('Listening on port 80')

    while True:
        # Accept and create a connection socket with the client
        client_socket, client_address = server_socket.accept()

        logger.info(f'{client_address} Connected')

        # If the client sent a valid http request, handle it
        try:
            is_valid, method, resource = validate_http_request(client_socket)
            if is_valid:
                handle_client_request(client_socket, method, resource)
        except TypeError as e:
            exc_tb = sys.exc_info()[2]  # The exception's traceback
            logger.critical(
                f'{e}\tline {exc_tb.tb_lineno}\n{traceback.format_exc()}\n')


if __name__ == '__main__':
    main()
