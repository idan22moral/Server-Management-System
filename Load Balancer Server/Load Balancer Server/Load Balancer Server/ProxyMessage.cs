using System.Net;
using System.Net.Sockets;

namespace Load_Balancer_Server
{
    class ProxyMessage
    {
        public IPEndPoint ClientEndpoint { get; private set; }
        public Socket Socket { get; private set; }
        public byte[] Content { get; private set; }

        public ProxyMessage(IPEndPoint clientEndpoint, Socket socket, byte[] content)
        {
            ClientEndpoint = clientEndpoint;
            Socket = socket;
            Content = content;
        }

        ~ProxyMessage()
        {
            if (Socket != null)
                Socket.Dispose();
        }
    }
}
