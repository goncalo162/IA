import json
import math
from graph.node import Node, TipoNodo
from graph.aresta import Aresta, NivelTransito


class Grafo:
    def __init__(self, directed=False):
        self.m_nodes = []
        self.m_directed = directed
        self.m_graph = {}  # { node_name: [(dest_name, Aresta), ...] }

    def __str__(self):
        out = ""
        for key in self.m_graph.keys():
            out += f"node {key}: {self.m_graph[key]}\n"
        return out

    ################################
    #   encontrar nodo pelo nome
    ################################
    def get_node_by_name(self, name):
        for node in self.m_nodes:
            if node.getName() == name:
                return node
        return None

    ##############################
    #   imprimir arestas
    ##############################
    def imprime_aresta(self):
        listaA = ""
        for nodo in self.m_graph.keys():
            for (nodo2, aresta) in self.m_graph[nodo]:
                tempo = aresta.getTempoPercorrer()
                listaA += f"{nodo} -> {nodo2} | {aresta.getNome()} | tempo: {tempo:.2f}\n"
        return listaA

    ##############################
    #   adicionar aresta
    ##############################
    def add_edge(self, node1: Node, node2: Node, aresta: Aresta):
        n1_name = node1.getName()
        n2_name = node2.getName()

        if node1 not in self.m_nodes:
            node1.setId(len(self.m_nodes))
            self.m_nodes.append(node1)
            self.m_graph[n1_name] = []

        if node2 not in self.m_nodes:
            node2.setId(len(self.m_nodes))
            self.m_nodes.append(node2)
            self.m_graph[n2_name] = []

        self.m_graph[n1_name].append((n2_name, aresta))
        if not self.m_directed:
            self.m_graph[n2_name].append((n1_name, aresta))

    #############################
    # devolver nodos
    ##########################
    def getNodes(self):
        return self.m_nodes

    #######################
    # devolver o custo (tempo) de uma aresta
    #######################
    def get_arc_cost(self, node1, node2):
        name1 = node1.getName() if isinstance(node1, Node) else node1
        name2 = node2.getName() if isinstance(node2, Node) else node2

        if name1 not in self.m_graph:
            return math.inf
        for (nodo, aresta) in self.m_graph[name1]:
            if nodo == name2:
                return aresta.getTempoPercorrer()
        return math.inf

    ##############################
    # calcular custo total de um caminho
    ##############################
    def calcula_custo(self, caminho):
        custo = 0
        for i in range(len(caminho) - 1):
            custo += self.get_arc_cost(caminho[i], caminho[i + 1])
        return custo

    ##############################################
    # Importar grafo a partir de um ficheiro JSON
    ##############################################
    @staticmethod
    def from_json_file(filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        g = Grafo(directed=data.get("directed", False))

        # Criar nós
        nodes_map = {}
        for n in data["nodes"]:
            tipo = TipoNodo[n["tipo"]] if isinstance(n["tipo"], str) else TipoNodo(n["tipo"])
            node = Node(n["name"], id=n.get("id", -1), tipo=tipo)
            g.m_nodes.append(node)
            g.m_graph[node.getName()] = []
            nodes_map[node.getName()] = node

        # Criar arestas
        for e in data["edges"]:
            src = e["source"]
            dst = e["target"]
            transito_value = e.get("transito", "NORMAL")
            transito = NivelTransito[transito_value] if isinstance(transito_value, str) else NivelTransito(transito_value)

            aresta = Aresta(
                quilometro=e["quilometro"],
                velocidadeMaxima=e["velocidadeMaxima"],
                nome=e["nome"],
                transito=transito,
            )
            g.add_edge(nodes_map[src], nodes_map[dst], aresta)

        return g