using System;
using System.Collections.Generic;
using System.Linq;

namespace Load_Balancer_Server
{
    class LoadBalancer<TLoadCarrier>
    {
        private Dictionary<TLoadCarrier, int> _loadCarrierPairs;

        /// <summary>
        /// Creates an instance of the LoadBalancer class.
        /// </summary>
        /// <param name="loadCarriers">A collection of load carriers to balance.</param>
        public LoadBalancer(ICollection<TLoadCarrier> loadCarriers)
        {
            _loadCarrierPairs = new Dictionary<TLoadCarrier, int>();

            // Set all the loads to zero
            foreach (var loadCarrier in loadCarriers)
                _loadCarrierPairs[loadCarrier] = 0;
        }

        /// <summary>
        /// Creates an instance of the LoadBalancer class.
        /// </summary>
        /// <param name="loadCarriers">A dictionary-like set of the load carriers and their loads.</param>
        public LoadBalancer(IDictionary<TLoadCarrier, int> loadCarriers)
        {
            _loadCarrierPairs = new Dictionary<TLoadCarrier, int>(loadCarriers);
        }


        /// <summary>
        /// Picks the most available carrier from the load carriers and returns it.
        /// </summary>
        /// <returns>Returns the <typeparamref name="TLoadCarrier"/> with the smallest load.</returns>
        public TLoadCarrier PickMostAvailableCarrier()
        {
            // Make sure that there are any load carrier
            if (_loadCarrierPairs.Count == 0)
                throw new Exception("Cannot pick a Load Carrier because there are not any.");

            var mostAvailable = _loadCarrierPairs.First();

            // For each pair of carrier and load
            foreach (var pair in _loadCarrierPairs)
                // Save the pair if the load is the smallest yet
                if (pair.Value < mostAvailable.Value)
                    mostAvailable = pair;

            // Return the carrier with the smallest load
            return mostAvailable.Key;
        }

        /// <summary>
        /// Adds the given load carrier to the load balancer.
        /// </summary>
        /// <param name="newLoadCarrier">The new load carrier to add</param>
        /// <param name="load">The load of the new carrier.</param>
        public void AddLoadCarrier(TLoadCarrier newLoadCarrier, int load = 0)
        {
            if (_loadCarrierPairs.ContainsKey(newLoadCarrier))
                throw new Exception("The given load carrier is already in.");
            _loadCarrierPairs[newLoadCarrier] = load;
        }

        /// <summary>
        /// Removes 1 load unit from the load of the given load carrier if it exists.
        /// </summary>
        /// <param name="loadCarrier">The load carrier to remove from/param>
        private void RemoveLoad(TLoadCarrier loadCarrier)
        {
            if (_loadCarrierPairs.ContainsKey(loadCarrier))
                _loadCarrierPairs[loadCarrier] -= 1;
        }

        /// <summary>
        /// Adds 1 load unit to the load of the given load carrier if it exists.
        /// </summary>
        /// <param name="loadCarrier">The load carrier to add to/param>
        private void AddLoad(TLoadCarrier loadCarrier)
        {
            if (_loadCarrierPairs.ContainsKey(loadCarrier))
                _loadCarrierPairs[loadCarrier] += 1;
        }
    }
}
