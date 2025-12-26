import json
import math
import random
from .node import Node, TipoNodo
from .aresta import Aresta, NivelTransito


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

    ################################
    # obter ID do nó por nome
    ################################
    def getNodeId(self, node_name):
        """Obtém o ID de um nó pelo seu nome."""
        for node in self.m_nodes:
            if node.getName() == node_name:
                return node.getId()
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

    def getRandomNodo(self):
        nodos = self.m_nodes
        weights = [n.getAtratividade() for n in nodos]

        if sum(weights) == 0:
            return random.choice(nodos)

        return random.choices(nodos, weights=weights, k=1)[0]

    def get_nodes_by_tipo(self, tipo: TipoNodo):
        """Retorna todos os nós de um determinado tipo.

        Args:
            tipo: Tipo de nó a procurar (TipoNodo.BOMBA_GASOLINA, TipoNodo.POSTO_CARREGAMENTO, etc.)

        Returns:
            Lista de nomes de nós do tipo especificado
        """
        return [node.getName() for node in self.m_nodes if node.getTipoNodo() == tipo]

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

    ####################
    # função  getneighbours, devolve vizinhos de um nó
    ##############################

    def getNeighbours(self, nodo):
        lista = []
        for (adjacente, peso) in self.m_graph[nodo]:
            lista.append((adjacente, peso))
        return lista

    def getNodeName(self, node_id_or_name):
        """
        Retorna o nome de um nodo dado o seu ID ou, se já for um nome, devolve-o.
        Se não encontrar, devolve None.
        """
        # Se já for string, assumir que é o nome e devolver tal como está
        if isinstance(node_id_or_name, str):
            return node_id_or_name

        # Se for inteiro, procurar o node com esse id
        try:
            for node in self.m_nodes:
                if node.getId() == node_id_or_name:
                    return node.getName()
        except Exception:
            pass

        return None

    def getEdge(self, from_node: str, to_node: str):
        """
        Devolve o objeto Aresta entre dois nós (nomes). Se não existir, devolve None.
        """
        if from_node not in self.m_graph:
            return None
        for (dest, aresta) in self.m_graph[from_node]:
            if dest == to_node:
                return aresta
        return None

        # nao seria mais facil guardar as arestas num dict com chave o nome da
        # aresta? em vez de percorrer o grafo todo para encontrar a aresta pelo
        # nome

    def getEdgeByName(self, nome_aresta: str):
        """
        Devolve o objeto Aresta pelo seu nome. Se não existir, devolve None.
        """
        for node_name in self.m_graph:
            for (dest, aresta) in self.m_graph[node_name]:
                if aresta.getNome() == nome_aresta:
                    return aresta
        return None

    ################################
    #  Cálculos auxiliares em rotas
    ################################

    def calcular_distancia_rota(self, rota) -> float:
        """Calcula a distância total (km) de uma rota.

        A rota é uma lista de nomes de nós. Para cada par consecutivo,
        obtém a aresta e soma o quilómetro associado.
        """
        if rota is None or len(rota) < 2:
            return 0.0

        distancia_total = 0.0
        for i in range(len(rota) - 1):
            aresta = self.getEdge(rota[i], rota[i + 1])
            if aresta:
                distancia_total += aresta.getQuilometro()

        return distancia_total

    def calcular_tempo_rota(self, rota) -> float:
        """Calcula o tempo total (horas) para percorrer uma rota.

        Usa o tempo de cada aresta (`getTempoPercorrer`). Lança um erro se
        alguma aresta não tiver informação de tempo.
        """
        if rota is None or len(rota) < 2:
            return 0.0

        tempo_total_horas = 0.0
        for i in range(len(rota) - 1):
            aresta = self.getEdge(rota[i], rota[i + 1])
            if aresta:
                tempo_segmento = aresta.getTempoPercorrer()
                if tempo_segmento is None:
                    raise ValueError(
                        f"Aresta {rota[i]} -> {rota[i + 1]} não tem informação de tempo."
                    )
                tempo_total_horas += tempo_segmento

        return tempo_total_horas

    def encontrar_posto_mais_proximo(
            self,
            localizacao_atual: str,
            tipo_posto: TipoNodo,
            navegador=None):
        """Encontra o posto de abastecimento/recarga mais próximo.

        Args:
            localizacao_atual: Nome do nó onde o veículo está
            tipo_posto: Tipo de posto (TipoNodo.BOMBA_GASOLINA ou TipoNodo.POSTO_CARREGAMENTO)
            navegador: Navegador para calcular rotas (se None, usa distância euclidiana aproximada)

        Returns:
            Tupla (nome_posto, rota, distancia) ou (None, None, None) se não encontrar
        """
        postos = self.get_nodes_by_tipo(tipo_posto)

        if not postos:
            return None, None, None

        # Se já estiver num posto do tipo certo, retornar ele mesmo
        if localizacao_atual in postos:
            return localizacao_atual, [localizacao_atual], 0.0

        melhor_posto = None
        melhor_rota = None
        menor_distancia = float('inf')

        for posto in postos:
            if navegador:
                # Usar navegador para calcular rota real
                rota = navegador.calcular_rota(self, localizacao_atual, posto)
                if rota:
                    distancia = self.calcular_distancia_rota(rota)
                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        melhor_posto = posto
                        melhor_rota = rota
            else:
                # Aproximação por distância euclidiana (se tiver coordenadas)
                node_atual = self.get_node_by_name(localizacao_atual)
                node_posto = self.get_node_by_name(posto)

                if node_atual and node_posto and node_atual.getX() is not None and node_posto.getX() is not None:
                    dx = node_posto.getX() - node_atual.getX()
                    dy = node_posto.getY() - node_atual.getY()
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < menor_distancia:
                        menor_distancia = dist
                        melhor_posto = posto
                        melhor_rota = None  # Rota será calculada depois

        return melhor_posto, melhor_rota, menor_distancia

    ##############################################
    # Importar grafo a partir de um ficheiro JSON
    ##############################################

    def alterarTransitoAresta(self, nome_aresta: str, nivel: NivelTransito) -> bool:
        """
        Altera o nível de trânsito de uma aresta pelo seu nome.

        Args:
            nome_aresta: Nome da aresta a alterar (ex: "Rua da Sé")
            nivel: Novo nível de trânsito (NivelTransito enum)

        Returns:
            True se a aresta foi encontrada e alterada, False caso contrário.
        """
        aresta = self.getEdgeByName(nome_aresta)
        if aresta:
            aresta.setNivelTransito(nivel)
            return True
        return False

    @staticmethod
    def from_json_file(filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        g = Grafo(directed=data.get("directed", False))

        # Criar nós (ler x/y se presentes)
        nodes_map = {}
        for n in data["nodes"]:
            tipo = TipoNodo[n["tipo"]] if isinstance(
                n["tipo"], str) else TipoNodo(n["tipo"])
            x = n.get("x")
            y = n.get("y")
            node = Node(n["name"], id=n.get("id", -1), tipo=tipo, x=x, y=y)
            g.m_nodes.append(node)
            g.m_graph[node.getName()] = []
            nodes_map[node.getName()] = node

        # Criar arestas
        for e in data["edges"]:
            src = e["source"]
            dst = e["target"]
            transito_value = e.get("transito", "NORMAL")
            transito = NivelTransito[transito_value] if isinstance(
                transito_value, str) else NivelTransito(transito_value)

            aresta = Aresta(
                quilometro=e["quilometro"],
                velocidadeMaxima=e["velocidadeMaxima"],
                nome=e["nome"],
                transito=transito,
            )
            g.add_edge(nodes_map[src], nodes_map[dst], aresta)

        return g
