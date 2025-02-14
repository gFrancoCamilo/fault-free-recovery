import subprocess
import os
import numpy as np
import json
import sys

BASE_PORT = 10000
class Scenario:

    def __init__ (self, nodes, faults = 0, allow_communications = 50, network_delay=1):
        self.faults = faults
        self.allow_communications = allow_communications
        self.network_delay = network_delay
        self.nodes = int(nodes)


    def  _get_number_honest_parties (self):
        return self.faults + 1
    
    def _get_number_shadows (self):
        return self.faults * 2 * self.faults 
    
    def _get_total_number_nodes (self):
        return self.faults * 2 * (self.faults + 1) + self.faults + 1

    def _get_honest_parties(self):
        return [i for i in range(self._get_number_honest_parties())]
    
    def _get_cliques (self):
        nodes = [i for i in range(self._get_total_number_nodes())]
        nodes_minus_honest = nodes[self._get_number_honest_parties():]

        cliques = np.array_split(np.array(nodes_minus_honest), self.faults + 1)
        cliques = [clique.tolist() for clique in cliques]

        honest_parties = self._get_honest_parties()

        for i, clique in enumerate(cliques):
            clique.append(honest_parties[i])
        return cliques
    
    def _print(self):
        print('------------------------------------------------')
        print(' For {} faults'.format(self.faults))
        print('------------------------------------------------')
        print('Total number of nodes: {}'.format(self._get_total_number_nodes()))
        print('Cliques: {}'.format(self._get_cliques()))
        print('Number of shadows: {}'.format(self._get_number_shadows()))
        print('------------------------------------------------')
    
    def _create_network_params_file(self, path='./benchmark/.network_params.json'):
        nodes = {}
        cliques = self._get_cliques()
        for node in range(self.nodes):
            nodes['node_'+str(node)] = {}
            for i in range(0,4):
                nodes['node_'+str(node)][str(i)] = []
                nodes['node_'+str(node)][str(i)].append('111.111.111.111:111')
        nodes['num_of_twins'] = self._get_number_shadows()
        nodes['allow_communications_at_round'] = self.allow_communications
        nodes['network_delay'] = self.network_delay


        with open(path, 'w') as f:
            json.dump(nodes, f, indent=4, sort_keys=True)

        return nodes

if len(sys.argv) != 2:
        print("Usage: python get-results.py <num-nodes>")
        sys.exit(1)
scenario = Scenario(sys.argv[1])
scenario._create_network_params_file()
