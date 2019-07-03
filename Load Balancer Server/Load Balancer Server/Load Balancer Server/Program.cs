using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Net.Sockets;

namespace Load_Balancer_Server
{
    class Program
    {
        static HashSet<IPEndPoint> _servers = new HashSet<IPEndPoint>();
        static LoadBalancer<IPEndPoint> _loadBalancer = new LoadBalancer<IPEndPoint>(_servers);
        static Dictionary<IPEndPoint, Socket> _clients = new Dictionary<IPEndPoint, Socket>();
        const string SERVER_REGEX = @"(?<ip>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)):(?<port>\d+)";
        const string SERVERS_FILE = "servers.cfg";
        const int SERVE_PORT = 80;
        const int PROXY_PORT = 7070;
        const int SECOND = 1000;

        static void Main(string[] args)
        {
            // Load all the servers from the configuration file in a constant interval
            Thread serverLoadingThread = new Thread(() =>
            {
                while (true)
                {
                    HashSet<IPEndPoint> addedServers = LoadServers(SERVERS_FILE);
                    //Console.WriteLine("Reloading servers...");

                    // Add the new servers to the Load Balancer
                    foreach (var server in addedServers)
                    {
                        lock (_loadBalancer)
                        {
                            _loadBalancer.AddLoadCarrier(server);
                        }
                    }

                    // Sleep for ten Seconds
                    Thread.Sleep(SECOND);
                }
            });
            serverLoadingThread.Start();

            // Start the status-printing thread
            Thread statusPrintingThread = new Thread(() =>
            {
                while (true)
                {
                    PrintLoadBalancingStatus();
                    Thread.Sleep(100);
                }
            });
            statusPrintingThread.Start();

            // Set-up the server and start listening for client-requests and server-responses
            ProxyServer proxyServer = new ProxyServer(SERVE_PORT, PROXY_PORT);
            proxyServer.Start();

            while (true)
            {
                // Get request from client
                ProxyMessage clientRequest = proxyServer.ReceiveClientMessage();
                _clients[clientRequest.ClientEndpoint] = clientRequest.Socket;
                //ColorizedWriteLine($"REQUEST from {clientRequest.ClientEndpoint}", ConsoleColor.Green);
                
                // Pick the most available server
                IPEndPoint handlingServer;
                lock (_loadBalancer)
                {
                    //Console.WriteLine("Picking Web Server...");
                    handlingServer = _loadBalancer.PickMostAvailableCarrier();
                    //Console.WriteLine($"Picked {handlingServer}");
                }
                
                try
                {
                    // Pass the request of the client to the server
                    //Console.WriteLine($"Passing Client Request to {handlingServer}");
                    proxyServer.PassClientMessage(clientRequest, handlingServer);
                    // Add the load to the handling server
                    _loadBalancer.AddLoad(handlingServer);
                }
                catch // There's a problem with the web server
                {
                    // Send the client an error message
                    byte[] problemResponseData = Encoding.ASCII.GetBytes("HTTP/1.1 500 Internal Server Error");
                    var clientEP = clientRequest.ClientEndpoint;
                    proxyServer.PassResponse(new ProxyMessage(clientEP, null, problemResponseData), clientRequest.Socket);

                    // Remove the load from the handling server
                    _loadBalancer.RemoveLoad(handlingServer);
                    
                    // Notify in the console that the web server has a problem
                    ColorizedWriteLine($"Web Server {handlingServer} has a problem! (2)", ConsoleColor.Red);
                    continue;
                }

                // Queue a thread for handling the request
                ThreadPool.QueueUserWorkItem((obj) =>
                {
                    try
                    {
                        // Get the response for the client form the server
                        ProxyMessage serverResponse = proxyServer.ReceiveResponse();
                        
                        // Pass the response to the client
                        proxyServer.PassResponse(serverResponse, _clients[serverResponse.ClientEndpoint]);
                        _clients.Remove(serverResponse.ClientEndpoint);
                        //ColorizedWriteLine($"RESPONSE to {clientRequest.ClientEndpoint}", ConsoleColor.Blue);
                    }
                    catch (Exception e)
                    {
                        // Send the client an error message
                        byte[] problemResponseData = Encoding.ASCII.GetBytes("HTTP/1.1 500 Internal Server Error");
                        var clientEP = clientRequest.ClientEndpoint;
                        proxyServer.PassResponse(new ProxyMessage(clientEP, null, problemResponseData), clientRequest.Socket);

                        // Notify in the console that the web server has a problem
                        ColorizedWriteLine($"Web Server {handlingServer} has a problem!\n", ConsoleColor.Red);
                    }

                    // Remove the load from the handling server
                    _loadBalancer.RemoveLoad(handlingServer);
                });
            }
        }

        /// <summary>
        /// Loads the servers from the given configuration file, and returns a set new of servers.
        /// </summary>
        /// <param name="serversFile">The path to the servers list file.</param>
        /// <returns>All the new servers that were added.</returns>
        static HashSet<IPEndPoint> LoadServers(string serversFile)
        {
            // Make sure that the given file-path exists
            if (!File.Exists(serversFile))
                throw new FileNotFoundException("The given file name does not exist.");

            // Read all the lines from the file
            // Each line represents the endpoint of a server
            string[] lines = File.ReadAllLines(serversFile);
            HashSet<IPEndPoint> serversAfterChange = new HashSet<IPEndPoint>();
            HashSet<IPEndPoint> addedServers = new HashSet<IPEndPoint>();

            foreach (var line in lines)
            {
                // Make sure that line is in this format: IP:PORT
                var serverMatch = Regex.Match(line, SERVER_REGEX);
                if (serverMatch.Success)
                {
                    try
                    {
                        // Extract the IP and Port from the line
                        string ip = serverMatch.Groups["ip"].Value;
                        int port = int.Parse(serverMatch.Groups["port"].Value);

                        if (!IsValidPort(port))
                            throw new Exception("Port cannot be less than 0 or greater than 65535.");

                        // Create an Endpoint for the server
                        IPEndPoint server = new IPEndPoint(IPAddress.Parse(ip), port);

                        // Add the server to the set that represents the new server set
                        serversAfterChange.Add(server);
                        lock (_servers)
                        {
                            // Add the server to the set that represents the added servers
                            if (!_servers.Contains(server))
                                addedServers.Add(server);
                            // Add the server to the set of servers
                            _servers.Add(server);
                        }
                    }
                    catch (Exception e)
                    {
                        Console.WriteLine(e.Message);
                    }
                }
            }

            lock (_servers)
            {
                // Take all the servers that were removed from the configuration file
                HashSet<IPEndPoint> removedServers = new HashSet<IPEndPoint>();
                foreach (IPEndPoint server in _servers)
                    if (!serversAfterChange.Contains(server))
                        removedServers.Add(server);

                // Remove those servers from the servers set and from the load balancer
                foreach (IPEndPoint server in removedServers)
                {
                    _servers.Remove(server);
                    _loadBalancer.RemoveLoadCarrier(server);
                }
            }

            // Return the added servers
            return addedServers;
        }

        /// <summary>
        /// Checks if the given port is a valid one.
        /// </summary>
        /// <param name="port">The port to check.</param>
        /// <returns>Boolean representing the validity of the given port.</returns>
        static bool IsValidPort(int port)
        {
            return port >= 0 && port <= 65535;
        }

        /// <summary>
        /// Prints the given text to the console with the given color.
        /// </summary>
        /// <param name="text">The text to print.</param>
        /// <param name="color">The color to print in.</param>
        static void ColorizedWriteLine(string text, ConsoleColor color)
        {
            lock (Console.Out)
            {
                var previousColor = Console.ForegroundColor;
                Console.ForegroundColor = color;
                Console.WriteLine(text);
                Console.ForegroundColor = previousColor;
            }
        }

        static void PrintLoadBalancingStatus()
        {
            Console.Clear();

            Console.WriteLine($"Servers [{_servers.Count}]:");
            Console.WriteLine("\tIP\t\tPort\tLoad");
            foreach (var server in _servers)
            {
                Console.WriteLine($"\t{server.Address}\t{server.Port}\t{_loadBalancer.GetLoad(server)}");
            }
        }
    }
}
