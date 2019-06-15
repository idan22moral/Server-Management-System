using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using System.Threading;

namespace Load_Balancer_Server
{
    class Program
    {
        static HashSet<IPEndPoint> _servers = new HashSet<IPEndPoint>();
        static LoadBalancer<IPEndPoint> _loadBalancer = new LoadBalancer<IPEndPoint>(_servers);
        const string SERVER_REGEX = @"(?<ip>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)):(?<port>\d+)";
        const string SERVERS_FILE = "servers.cfg";
        const int SERVE_PORT = 80;
        const int PROXY_PORT = 7070;

        static void Main(string[] args)
        {
            // Load all the servers from the configuration file in a constant interval
            Thread serverLoadingThread = new Thread(() =>
            {
                while (true)
                {
                    HashSet<IPEndPoint> addedServers = LoadServers(SERVERS_FILE);
                    Console.WriteLine("Reloading servers...");

                    // Add the new servers to the Load Balancer
                    foreach (var server in addedServers)
                    {
                        lock (_loadBalancer)
                        {
                            _loadBalancer.AddLoadCarrier(server);
                        }
                    }
                    
                    // Sleep for ten Seconds
                    Thread.Sleep(10 * 1000);
                }
            });
            serverLoadingThread.Start();

            // Set-up the server and start listening for client-requests and server-responses
            ProxyServer proxyServer = new ProxyServer(SERVE_PORT, PROXY_PORT);
            proxyServer.Start();

            while (true)
            {
                // Get request from client
                ProxyMessage clientRequest = proxyServer.ReceiveClientMessage();

                // Pick the most available server
                IPEndPoint handlingServer;
                lock (_loadBalancer)
                {
                    handlingServer = _loadBalancer.PickMostAvailableCarrier();
                }

                // Pass the request of the client to the server
                lock (proxyServer)
                {
                    proxyServer.PassClientMessage(clientRequest, handlingServer);
                }

                // Queue a thread for handling the server's response
                ThreadPool.QueueUserWorkItem((obj) =>
                {
                    ProxyMessage serverResponse;
                    lock (proxyServer)
                    {
                        // Get the response for the client form the server
                        serverResponse = proxyServer.ReceiveResponse();
                    }

                    lock (proxyServer)
                    {
                        // Pass the response to the client
                        proxyServer.PassResponse(serverResponse);
                    }
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
                    if(!serversAfterChange.Contains(server))
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
    }
}
