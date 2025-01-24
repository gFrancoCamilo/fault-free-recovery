import subprocess
import os
import numpy as np
import json

BASE_PORT = 10000
class Scenario:

    def __init__ (self, faults, allow_communications = 50, network_delay=1):
        self.faults = faults
        self.allow_communications = allow_communications
        self.network_delay = network_delay


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
        all_nodes = [i for i in range(self._get_total_number_nodes())]
        honest_parties = [i for i in range(self._get_number_honest_parties())]
        nodes = {}
        cliques = self._get_cliques()
        for node in all_nodes:
            nodes['node_'+str(node)] = {}
            for number in range(self.faults + 1):
                nodes['node_'+str(node)][str(number)] = []
            for clique in cliques:
                if node not in clique:
                    for node_not_in_clique in clique:
                        for number1 in range(self.faults + 1):
                            nodes['node_'+str(node)][str(number1)].append('127.0.0.1:'+str(BASE_PORT+node_not_in_clique))
        for node in honest_parties:
            nodes_to_remove = 0
            for i,firewall in enumerate(nodes['node_'+str(node)]):
                #if int(firewall[len(firewall)-1]) >= node:
                if int(firewall) >= node:
                    for number in range(nodes_to_remove+1):
                        if '127.0.0.1:'+str(BASE_PORT+number) in nodes['node_'+str(node)][firewall]:
                            nodes['node_'+str(node)][str(i)].remove('127.0.0.1:'+str(BASE_PORT+number))
                nodes_to_remove += 1;
        nodes['num_of_twins'] = self._get_number_shadows()
        nodes['allow_communications_at_round'] = self.allow_communications
        nodes['network_delay'] = self.network_delay
        for node in all_nodes:
            nodes['node_'+str(node)][str(i+1)] = []
            for clique in cliques:
                if node not in clique:
                    for node_not_in_clique in clique:
                        if node_not_in_clique >= self.faults + 1:
                            nodes['node_'+str(node)][str(i+1)].append('127.0.0.1:'+str(BASE_PORT+node_not_in_clique))

        for node in nodes:
            print('{}: {}\n-----------------------------------------------------'.format(node, nodes[node]))


        with open(path, 'w') as f:
            json.dump(nodes, f, indent=4, sort_keys=True)

        #    for other_node in honest_parties:
        #        string_to_remove = '127.0.0.1:'+str(BASE_PORT+other_node)
        #        if string_to_remove in nodes['node_'+str(node)]['new_firewall']:
        #            nodes['node_'+str(node)]['new_firewall'].remove(string_to_remove)
        
        return nodes

#for i in range(1,4):
#    scenario = Scenario(i)
scenario = Scenario(2)
scenario._print()
scenario._create_network_params_file()
