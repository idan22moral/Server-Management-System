using System.Net;

namespace Load_Balancer_Server
{
    class ProxyMessage
    {
        public IPEndPoint ClientEndpoint { get; private set; }
        public byte[] Content { get; private set; }

        public ProxyMessage(IPEndPoint clientEndpoint, byte[] content)
        {
            ClientEndpoint = clientEndpoint;
            Content = content;
        }
    }
}
