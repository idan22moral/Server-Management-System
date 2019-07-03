using System;
using System.Linq;
using System.Net;
using System.Net.Sockets;

namespace Load_Balancer_Server
{
    class ProxyServer
    {
        // The maximum length of a packet
        private const int MAX_PACKET_SIZE = 65536;
        // The amount of bytes that an IP contains
        private const int IP_LENGTH_IN_BYTES = 4;
        // The amount of bytes that an port contains
        private const int PORT_LENGTH_IN_BYTES = 2;

        // Boolean that says wether or not the server
        // is listening for clients and responses
        private bool running;
        // The TCP listeners for clients requests and server responses
        private readonly TcpListener _tcpClientListener;
        private readonly TcpListener _tcpResponseListener;

        /// <summary>
        /// Creates an instance of the class ProxyServer
        /// </summary>
        /// <param name="servingPort">The port that the client connects to.</param>
        /// <param name="proxyPort">The port on this Proxy that the responses return to.</param>
        public ProxyServer(int servingPort, int proxyPort)
        {
            // Make sure that the ports are valid
            if (servingPort > IPEndPoint.MaxPort || servingPort < 1)
                throw new Exception("The given serving port is invalid.");
            if (proxyPort > IPEndPoint.MaxPort || proxyPort < 1)
                throw new Exception("The given proxy port is invalid.");
            if (servingPort == proxyPort)
                throw new Exception("The serving port cannot be the same as the proxy port.");

            // Create the TCP listeners of the server
            _tcpClientListener = new TcpListener(IPAddress.Parse("0.0.0.0"), servingPort);
            _tcpResponseListener = new TcpListener(IPAddress.Parse("0.0.0.0"), proxyPort);
            running = false;
        }

        /// <summary>
        /// Make the server start listening.
        /// </summary>
        public void Start()
        {
            // Start the listeners
            _tcpResponseListener.Start();
            _tcpClientListener.Start();
            running = true;
        }

        /// <summary>
        /// Passes the given client message to the given endpoint.
        /// </summary>
        /// <param name="message">The message of the client and his endpoint.</param>
        /// <param name="dstEP">The endpoint that will receive the client's message</param>
        public void PassClientMessage(ProxyMessage message, IPEndPoint dstEP)
        {
            // Build the message in our proxy format:
            // <endpoint_bytes><client_message>
            var ipBytes = message.ClientEndpoint.Address.GetAddressBytes();
            var portBytes = BitConverter.GetBytes(message.ClientEndpoint.Port).Take(PORT_LENGTH_IN_BYTES).ToArray();
            byte[] messageToSend = ipBytes.Concat(portBytes).Concat(message.Content).ToArray();

            // Send the proxy-formatted message to the destination
            Socket socket = new Socket(SocketType.Stream, ProtocolType.Tcp);
            try
            {
                socket.Connect(dstEP);
            }
            catch
            {
                throw new Exception("Connection to server failed.");
            }
            socket.Send(messageToSend);
        }

        /// <summary>
        /// Passes the given response message to the endpoint.
        /// </summary>
        /// <param name="response"></param>
        public void PassResponse(ProxyMessage response, Socket clientSocket)
        {
            // Send the response to the client
            if(clientSocket != null && clientSocket.Connected)
                clientSocket.Send(response.Content);
        }

        /// <summary>
        /// Receives a message from one of the clients.
        /// </summary>
        /// <returns>Returns the message that the client send.</returns>
        public ProxyMessage ReceiveClientMessage()
        {
            if (!running)
                throw new Exception("Start the server before trying to receive messages.");

            // Accept a client
            var buffer = new byte[MAX_PACKET_SIZE];

            var clientSocket = _tcpClientListener.AcceptSocket();

            // Get the message from the client and return it
            clientSocket.Receive(buffer);
            return new ProxyMessage((IPEndPoint)clientSocket.RemoteEndPoint, clientSocket, buffer);
        }

        /// <summary>
        /// Receives a response for one of the client requests.
        /// </summary>
        /// <returns>A tuple containing the EndPoint of the client, and the response data in bytes.</returns>
        public ProxyMessage ReceiveResponse()
        {
            if (!running)
                throw new Exception("Start the server before trying to receive messages.");

            // Accept the responsing server
            var buffer = new byte[MAX_PACKET_SIZE];
            var responseSocket = _tcpResponseListener.AcceptSocket();

            // Get the message from the server and return it
            try
            {
                // Give the server 5 seconds to respond
                responseSocket.ReceiveTimeout = 1000 * 5;
                responseSocket.Receive(buffer);
            }
            catch (Exception e)
            {
                throw new Exception("Response receiving timeout.");
            }

            // Extract the client endpoint from the response
            byte[] ipBytes = buffer.Take(IP_LENGTH_IN_BYTES).ToArray();
            byte[] portBytes = buffer.Skip(IP_LENGTH_IN_BYTES).Take(PORT_LENGTH_IN_BYTES).ToArray();
            long ipLong = BitConverter.ToInt64(ipBytes.Concat(new byte[] { 0, 0, 0, 0 }).ToArray(), 0);
            int portInt = BitConverter.ToInt32(portBytes.Concat(new byte[] { 0, 0 }).ToArray(), 0);
            var clientEndpoint = new IPEndPoint(ipLong, portInt);

            // Extract the response data from the response
            var responseData = buffer.Skip(IP_LENGTH_IN_BYTES + PORT_LENGTH_IN_BYTES).ToArray();

            return new ProxyMessage(clientEndpoint, null, responseData);
        }

        /// <summary>
        /// Converts an array of bytes to long.
        /// </summary>
        /// <param name="bytes">The array of bytes to convert.</param>
        /// <returns>A long representation of the given bytes array..</returns>
        private long BytesToLong(byte[] bytes)
        {
            // Make sure that the array exists and it is not empty
            if (bytes == null || bytes.Length == 0)
                return 0;

            long number = bytes[0];
            for (int i = 1; i < bytes.Length; i++)
            {
                // This operation shifts the number's bits 8 times.
                // Before:  0x000000FF
                // After:   0x0000FF00
                number <<= 8;
                number += bytes[i];
            }

            return number;
        }
    }

}
