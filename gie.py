"""
GIE — Geometric Invariant Explorer
Платформа для исследования структуры мышления и знаний.

Версия: 2.0
"""

import json
import re
import random
from datetime import datetime
from collections import Counter, defaultdict
from itertools import combinations

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


class CommunityStrategy:
    """Стратегии кластеризации."""
    LOUVAIN = "louvain"
    GIRVAN_NEWMAN = "girvan_newman"
    LABEL_PROPAGATION = "label_propagation"


class Node:
    """Узел графа."""

    def __init__(self, text, node_id, node_type="difference"):
        self.id = node_id
        self.text = text
        self.type = node_type  # difference, meta, collapsed
        self.timestamp = datetime.now().isoformat()
        self.relations = []
        self.tension = 0.0
        self.collapsed_into = None
        self.weight = 1.0
        self.confidence = 1.0
        
        # Мета-информация для свёрнутых узлов
        self.origin_nodes = []
        self.origin_edges = []
        self.creation_reason = ""
        self.creation_score = 0.0
        
        # Временные метки
        self.birth = datetime.now()
        self.last_activation = datetime.now()
        self.activation_count = 1
        self.decay_rate = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "timestamp": self.timestamp,
            "relations": self.relations,
            "tension": self.tension,
            "collapsed_into": self.collapsed_into,
            "weight": self.weight,
            "confidence": self.confidence,
            "origin_nodes": self.origin_nodes,
            "origin_edges": self.origin_edges,
            "creation_reason": self.creation_reason,
            "creation_score": self.creation_score,
            "birth": self.birth.isoformat(),
            "last_activation": self.last_activation.isoformat(),
            "activation_count": self.activation_count,
            "decay_rate": self.decay_rate,
        }

    @classmethod
    def from_dict(cls, data):
        node = cls(data["text"], data["id"], data.get("type", "difference"))
        node.timestamp = data.get("timestamp", datetime.now().isoformat())
        node.relations = data.get("relations", [])
        node.tension = data.get("tension", 0.0)
        node.collapsed_into = data.get("collapsed_into")
        node.weight = data.get("weight", 1.0)
        node.confidence = data.get("confidence", 1.0)
        node.origin_nodes = data.get("origin_nodes", [])
        node.origin_edges = data.get("origin_edges", [])
        node.creation_reason = data.get("creation_reason", "")
        node.creation_score = data.get("creation_score", 0.0)
        
        # Временные метки
        birth_str = data.get("birth")
        node.birth = datetime.fromisoformat(birth_str) if birth_str else datetime.now()
        last_act_str = data.get("last_activation")
        node.last_activation = datetime.fromisoformat(last_act_str) if last_act_str else datetime.now()
        node.activation_count = data.get("activation_count", 1)
        node.decay_rate = data.get("decay_rate", 0.0)
        
        return node


class GIECore:
    """
    Geometric Invariant Explorer (GIE).
    Хранит граф, распространяет напряжение, анализирует структуру,
    находит инварианты.
    """

    RELATION_TYPES = [
        "related_to", "contradicts", "bridges",
        "supports", "mirrors", "contains", "transforms",
        "depends_on", "analogous", "same_pattern",
    ]

    def __init__(self, invariant, witness_enabled=False, use_embeddings=False):
        self.invariant = invariant
        self.nodes = {}
        self.next_id = 1
        self.history = []
        self.witness_enabled = witness_enabled
        self.created_at = datetime.now().isoformat()
        
        # Эмбеддинги (опционально)
        self.use_embeddings = use_embeddings and HAS_EMBEDDINGS
        self.embedding_model = None
        if self.use_embeddings:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception:
                self.use_embeddings = False

    # ── Basic operations ──────────────────────────────

    def add_difference(self, text):
        """Добавляет узел различия."""
        node = Node(text, self.next_id, "difference")
        self.nodes[self.next_id] = node
        self.next_id += 1
        self._propagate_tension_diffusion()
        return {
            "node": node,
            "tension": self.total_tension(),
            "geometry": self.geometry(),
            "suggestions": self.suggest_relations(),
        }

    def relate(self, source_id, target_id, relation_type="related_to"):
        """Создаёт связь между узлами."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return {"error": "Node not found"}
        if relation_type not in self.RELATION_TYPES:
            return {"error": f"Invalid type. Use: {', '.join(self.RELATION_TYPES)}"}

        self.nodes[source_id].relations.append({
            "target": target_id,
            "type": relation_type,
            "created_at": datetime.now().isoformat(),
        })
        
        # Активируем оба узла
        self.nodes[source_id].last_activation = datetime.now()
        self.nodes[source_id].activation_count += 1
        self.nodes[target_id].last_activation = datetime.now()
        self.nodes[target_id].activation_count += 1
        
        self._propagate_tension_diffusion()
        return {
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "tension": self.total_tension(),
            "geometry": self.geometry(),
        }

    # ── Tension Field ─────────────────────────────────

    def _propagate_tension_diffusion(self, iterations=10, alpha=0.3):
        """
        Диффузионное обновление напряжения с гарантированной сходимостью.
        T_new = (1-alpha)*T_old + alpha*Field
        """
        active = self._active_nodes()
        if not active:
            return
        
        G = self._build_nx()
        
        # Инициализация локального напряжения
        local_tensions = {}
        for nid, node in active.items():
            local = 0.0
            local += len(node.relations) * 0.5 * node.weight
            for rel in node.relations:
                if rel["type"] == "contradicts":
                    local += 2.0
                elif rel["type"] == "supports":
                    local -= 0.3
            if not node.relations:
                local = 1.0
            local_tensions[nid] = max(0, local)
            node.tension = local_tensions[nid]
        
        # Вычисляем геометрические компоненты
        closeness_map = {}
        if G and G.number_of_nodes() > 0:
            try:
                closeness_map = nx.closeness_centrality(G)
            except Exception:
                pass
        
        # Итеративная диффузия
        for iteration in range(iterations):
            new_tensions = {}
            
            for nid, node in active.items():
                # Локальное напряжение
                T_local = local_tensions[nid]
                
                # Влияние соседей (усредненное)
                neighbor_sum = 0.0
                neighbor_count = 0
                for rel in node.relations:
                    target_id = rel["target"]
                    if target_id in active:
                        weight = 0.5 if rel["type"] == "contradicts" else 0.3
                        neighbor_sum += active[target_id].tension * weight
                        neighbor_count += 1
                
                T_neighbors = neighbor_sum / neighbor_count if neighbor_count > 0 else 0.0
                
                # Геометрический компонент (центростремительный)
                T_geometry = closeness_map.get(nid, 0) * 2.0
                
                # Плотность кластера
                cluster_density = self._get_cluster_density(nid)
                T_density = cluster_density * 1.5
                
                # Поле
                Field = T_local + T_neighbors + T_geometry + T_density
                
                # Диффузионное обновление
                T_old = node.tension
                T_new = (1 - alpha) * T_old + alpha * Field
                
                new_tensions[nid] = max(0, round(T_new, 3))
            
            # Обновление
            for nid, tension in new_tensions.items():
                active[nid].tension = tension
            
            # Проверка сходимости
            if iteration > 0:
                delta = sum(abs(active[nid].tension - new_tensions[nid]) for nid in active)
                if delta < 0.01:
                    break

    def _get_cluster_density(self, node_id):
        """Вычисляет плотность кластера, в котором находится узел."""
        communities = self.find_communities()
        for comm in communities:
            if node_id in comm["nodes"]:
                sub_nodes = comm["nodes"]
                internal_edges = 0
                for nid in sub_nodes:
                    if nid in self.nodes:
                        for rel in self.nodes[nid].relations:
                            if rel["target"] in sub_nodes:
                                internal_edges += 1
                max_edges = len(sub_nodes) * (len(sub_nodes) - 1) / 2
                return internal_edges / max_edges if max_edges > 0 else 0
        return 0

    def total_tension(self):
        """Суммарное напряжение графа."""
        return round(
            sum(n.tension for n in self.nodes.values() if n.type != "collapsed"), 1
        )

    # ── Geometry ──────────────────────────────────────

    def _active_nodes(self):
        """Возвращает только активные (несвёрнутые) узлы."""
        return {nid: n for nid, n in self.nodes.items() if n.type != "collapsed"}

    def _build_nx(self):
        """Строит NetworkX граф из активных узлов."""
        if not HAS_NETWORKX:
            return None
        G = nx.Graph()
        active = self._active_nodes()
        for nid, node in active.items():
            G.add_node(nid, text=node.text, type=node.type, tension=node.tension)
            for rel in node.relations:
                if rel["target"] in active:
                    G.add_edge(nid, rel["target"], type=rel["type"])
        return G

    def geometry(self):
        """Возвращает геометрические метрики графа."""
        active = self._active_nodes()
        if not active:
            return {"nodes": 0, "edges": 0, "clusters": 0, "isolated": 0,
                    "hot_spots": [], "central_nodes": []}

        edges = sum(len(n.relations) for n in active.values())
        isolated = [nid for nid, n in active.items() if not n.relations]
        hot = sorted(
            [{"id": nid, "tension": n.tension, "text": n.text[:60]}
             for nid, n in active.items() if n.tension > 2.0],
            key=lambda x: x["tension"], reverse=True,
        )
        central = sorted(
            [{"id": nid, "degree": len(n.relations), "text": n.text[:60]}
             for nid, n in active.items() if n.relations],
            key=lambda x: x["degree"], reverse=True,
        )

        G = self._build_nx()
        clusters = nx.number_connected_components(G) if G else 1

        return {
            "nodes": len(active),
            "edges": edges,
            "clusters": clusters,
            "isolated": len(isolated),
            "hot_spots": hot[:5],
            "central_nodes": central[:5],
        }

    # ── Suggestions ───────────────────────────────────

    def suggest_relations(self):
        """Предлагает связи на основе лексического сходства."""
        suggestions = []
        active = self._active_nodes()
        if len(active) < 2:
            return suggestions

        words = {}
        for nid, n in active.items():
            words[nid] = set(w.lower() for w in re.findall(r'\w+', n.text) if len(w) > 3)

        for a, b in combinations(active.keys(), 2):
            has_rel = any(r["target"] == b for r in active[a].relations)
            if not has_rel:
                common = words[a] & words[b]
                if len(common) >= 2:
                    suggestions.append({
                        "source": a, "target": b,
                        "common_words": list(common)[:3],
                        "suggested_type": "related_to",
                    })
        return suggestions[:5]

    def suggest_semantic_relations(self, threshold=0.7):
        """Предлагает связи на основе семантического сходства (эмбеддинги)."""
        if not self.use_embeddings or not self.embedding_model or not HAS_NUMPY:
            return []
        
        active = self._active_nodes()
        if len(active) < 2:
            return []
        
        embeddings = {}
        for nid, node in active.items():
            try:
                emb = self.embedding_model.encode(node.text)
                embeddings[nid] = emb
            except Exception:
                continue
        
        suggestions = []
        for a, b in combinations(active.keys(), 2):
            if a not in embeddings or b not in embeddings:
                continue
            
            has_rel = any(r["target"] == b for r in active[a].relations)
            if has_rel:
                continue
            
            similarity = np.dot(embeddings[a], embeddings[b]) / (
                np.linalg.norm(embeddings[a]) * np.linalg.norm(embeddings[b])
            )
            
            if similarity >= threshold:
                suggestions.append({
                    "source": a,
                    "target": b,
                    "similarity": round(float(similarity), 3),
                    "suggested_type": "analogous",
                })
        
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)
        return suggestions[:5]

    # ── Analysis ──────────────────────────────────────

    def find_bridges(self):
        """Находит узлы-мосты (articulation points)."""
        G = self._build_nx()
        if not G or G.number_of_nodes() == 0:
            return []
        try:
            art_points = list(nx.articulation_points(G))
        except Exception:
            art_points = []
        bridges = []
        for nid in art_points:
            if nid in self.nodes:
                bridges.append({
                    "node_id": nid,
                    "text": self.nodes[nid].text[:60],
                    "tension": self.nodes[nid].tension,
                })
        return bridges

    def find_communities(self, strategy=CommunityStrategy.LOUVAIN):
        """Находит сообщества разными алгоритмами."""
        G = self._build_nx()
        if not G or G.number_of_nodes() < 2:
            return []
        
        try:
            if strategy == CommunityStrategy.LOUVAIN:
                communities = nx.community.louvain_communities(G, seed=42)
            elif strategy == CommunityStrategy.LABEL_PROPAGATION:
                communities = list(nx.community.label_propagation_communities(G))
            elif strategy == CommunityStrategy.GIRVAN_NEWMAN:
                comp = nx.community.girvan_newman(G)
                communities = list(next(comp))
            else:
                communities = nx.community.louvain_communities(G, seed=42)
            
            return [
                {
                    "id": i,
                    "nodes": list(c),
                    "size": len(c),
                    "strategy": strategy,
                    "texts": [self.nodes[nid].text[:40] for nid in c if nid in self.nodes],
                }
                for i, c in enumerate(communities)
            ]
        except Exception:
            return []

    def find_motifs_isomorphic(self, size=3):
        """Находит мотивы через проверку изоморфизма подграфов."""
        G = self._build_nx()
        if not G or G.number_of_nodes() < size:
            return []
        
        # Защитные лимиты
        limits = {3: 50, 4: 25, 5: 15}
        if G.number_of_nodes() > limits.get(size, 15):
            return [{"error": f"Graph too large ({G.number_of_nodes()} nodes) for motif size {size}. Limit is {limits.get(size, 15)}."}]
        
        motifs = {}
        for nodes in combinations(G.nodes(), size):
            subgraph = G.subgraph(nodes)
            if subgraph.number_of_edges() == 0:
                continue
            
            # Проверяем изоморфизм с уже найденными мотивами
            found = False
            for motif_key, motif_data in motifs.items():
                template = motif_data["template"]
                if nx.is_isomorphic(subgraph, template):
                    motif_data["instances"].append(list(nodes))
                    found = True
                    break
            
            if not found:
                motifs[len(motifs)] = {
                    "template": subgraph,
                    "instances": [list(nodes)],
                    "size": size,
                }
        
        return [
            {
                "count": len(data["instances"]),
                "instances": data["instances"][:5],
                "size": data["size"],
            }
            for data in motifs.values()
            if len(data["instances"]) >= 2
        ]

    def calculate_centrality(self):
        """Вычисляет betweenness centrality."""
        G = self._build_nx()
        if not G or G.number_of_nodes() == 0:
            return []
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {}
        result = []
        for nid in G.nodes():
            result.append({
                "node_id": nid,
                "text": self.nodes[nid].text[:50] if nid in self.nodes else "",
                "betweenness": round(betweenness.get(nid, 0), 3),
                "degree": G.degree(nid),
            })
        result.sort(key=lambda x: x["betweenness"], reverse=True)
        return result

    def find_dense_clusters(self, min_size=3, min_density=0.4):
        """Находит плотные подграфы (геометрические кандидаты на абстракцию)."""
        G = self._build_nx()
        if not G or G.number_of_nodes() < min_size:
            return []
        candidates = []
        try:
            communities = nx.community.louvain_communities(G, seed=42)
        except Exception:
            communities = [set(G.nodes())]

        for comm in communities:
            if len(comm) < min_size:
                continue
            sub = G.subgraph(comm)
            max_edges = len(comm) * (len(comm) - 1) / 2
            density = sub.number_of_edges() / max_edges if max_edges else 0
            if density < min_density:
                continue
            avg_tension = sum(
                self.nodes[n].tension for n in comm if n in self.nodes
            ) / len(comm)
            candidates.append({
                "nodes": list(comm),
                "size": len(comm),
                "density": round(density, 3),
                "avg_tension": round(avg_tension, 2),
                "score": round(density * len(comm) * (1 + avg_tension / 10), 2),
                "texts": [self.nodes[n].text[:40] for n in comm if n in self.nodes],
            })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    # ── Spectral Analysis ─────────────────────────────

    def spectral_signature(self, n_eigenvalues=20):
        """Возвращает спектральные инварианты графа."""
        if not HAS_NUMPY:
            return {"error": "NumPy not available", "laplacian": [], "adjacency": []}
        
        G = self._build_nx()
        if not G or G.number_of_nodes() < 2:
            return {"laplacian": [], "adjacency": [], "normalized": False}
        
        try:
            # Лапласиан
            L = nx.laplacian_matrix(G).toarray()
            eigenvalues_L = np.linalg.eigvalsh(L)
            eigenvalues_L = np.sort(eigenvalues_L)[::-1]
            
            # Матрица смежности
            A = nx.adjacency_matrix(G).toarray()
            eigenvalues_A = np.linalg.eigvalsh(A)
            eigenvalues_A = np.sort(eigenvalues_A)[::-1]
            
            # Нормализация
            max_L = eigenvalues_L[0] if len(eigenvalues_L) > 0 else 1
            max_A = eigenvalues_A[0] if len(eigenvalues_A) > 0 else 1
            
            norm_L = (eigenvalues_L[:n_eigenvalues] / max_L).tolist() if max_L > 0 else []
            norm_A = (eigenvalues_A[:n_eigenvalues] / max_A).tolist() if max_A > 0 else []
            
            return {
                "laplacian": [round(float(x), 4) for x in norm_L],
                "adjacency": [round(float(x), 4) for x in norm_A],
                "normalized": True,
                "n_nodes": G.number_of_nodes(),
                "n_edges": G.number_of_edges(),
            }
        except Exception as e:
            return {"error": str(e), "laplacian": [], "adjacency": [], "normalized": False}

    def spectral_distance(self, other_core):
        """Вычисляет расстояние между двумя графами через спектр."""
        if not HAS_NUMPY:
            return float('inf')
        
        spec1 = self.spectral_signature()
        spec2 = other_core.spectral_signature()
        
        if "error" in spec1 or "error" in spec2:
            return float('inf')
        
        try:
            # Выравниваем длины
            len_L = min(len(spec1["laplacian"]), len(spec2["laplacian"]))
            len_A = min(len(spec1["adjacency"]), len(spec2["adjacency"]))
            
            if len_L == 0 or len_A == 0:
                return float('inf')
            
            # L2 расстояние
            dist_L = np.linalg.norm(
                np.array(spec1["laplacian"][:len_L]) - 
                np.array(spec2["laplacian"][:len_L])
            )
            dist_A = np.linalg.norm(
                np.array(spec1["adjacency"][:len_A]) - 
                np.array(spec2["adjacency"][:len_A])
            )
            
            distance = (dist_L + dist_A) / 2
            return round(float(distance), 4)
        except Exception:
            return float('inf')

    # ── Potential analysis ────────────────────────────

    def find_missing_bridges(self, top_n=5):
        """Какие отсутствующие рёбра сильнее всего уменьшат фрагментацию."""
        G = self._build_nx()
        if not G or G.number_of_nodes() < 3:
            return []

        components = list(nx.connected_components(G))
        if len(components) < 2:
            return []

        # Выбираем представителей (узлы с максимальной степенью)
        representatives = []
        for comp in components:
            rep = max(comp, key=lambda n: G.degree(n))
            representatives.append(rep)

        candidates = []
        for i in range(len(representatives)):
            for j in range(i + 1, len(representatives)):
                u = representatives[i]
                v = representatives[j]
                if not G.has_edge(u, v):
                    candidates.append({
                        "source": u,
                        "target": v,
                        "reduction": 1,
                        "text_a": self.nodes[u].text[:40],
                        "text_b": self.nodes[v].text[:40],
                    })

        candidates.sort(key=lambda x: G.degree(x["source"]) + G.degree(x["target"]), reverse=True)
        return candidates[:top_n]

    def find_lexical_bridges(self):
        """Какая общая лексика присутствует в разных кластерах."""
        communities = self.find_communities()
        if len(communities) < 2:
            return None

        cluster_texts = []
        for c in communities:
            words = []
            for nid in c["nodes"]:
                if nid in self.nodes:
                    words.extend(
                        w.lower() for w in re.findall(r'\w+', self.nodes[nid].text)
                        if len(w) > 3
                    )
            counter = Counter(words)
            cluster_texts.append(set(w for w, _ in counter.most_common(10)))

        if len(cluster_texts) >= 2:
            common = cluster_texts[0]
            for ct in cluster_texts[1:]:
                common = common & ct
            if common:
                return {
                    "suggested_concept": ", ".join(list(common)[:5]),
                    "connects_clusters": len(communities),
                    "reason": "Shared vocabulary across clusters",
                }

        return {
            "suggested_concept": "(no common vocabulary found)",
            "connects_clusters": len(communities),
            "reason": "Clusters are lexically distinct — consider a structural bridge",
        }

    def stability_analysis(self, sample_size=5):
        """Какие структуры устойчивы при удалении случайных узлов."""
        G = self._build_nx()
        if not G or G.number_of_nodes() < 4:
            return {"stable": True, "reason": "Graph too small for stability analysis"}

        original_components = nx.number_connected_components(G)
        fragility_count = 0
        active = list(self._active_nodes().keys())

        for nid in active[:sample_size]:
            G_test = G.copy()
            G_test.remove_node(nid)
            if nx.number_connected_components(G_test) > original_components + 1:
                fragility_count += 1

        fragility = fragility_count / min(sample_size, len(active))
        return {
            "stable": fragility < 0.3,
            "fragility": round(fragility, 2),
            "reason": "Low fragility — structure holds" if fragility < 0.3
                      else "High fragility — structure depends on few nodes",
        }

    # ── Collapse ──────────────────────────────────────

    def collapse_cluster(self, node_ids, meta_text, reason=""):
        """Сворачивает кластер в мета-узел."""
        if not all(nid in self.nodes for nid in node_ids):
            return {"error": "Some nodes not found"}

        meta = Node(meta_text, self.next_id, "meta")
        self.nodes[self.next_id] = meta
        meta_id = self.next_id
        self.next_id += 1

        # Сохраняем происхождение
        meta.origin_nodes = node_ids.copy()
        meta.origin_edges = []
        for nid in node_ids:
            for rel in self.nodes[nid].relations:
                if rel["target"] in node_ids:
                    meta.origin_edges.append({
                        "source": nid,
                        "target": rel["target"],
                        "type": rel["type"],
                    })
        
        internal_edges = len(meta.origin_edges)
        max_possible = len(node_ids) * (len(node_ids) - 1) / 2
        meta.creation_score = round(internal_edges / max_possible if max_possible > 0 else 0, 3)
        meta.creation_reason = reason or f"Collapsed {len(node_ids)} nodes"

        for nid in node_ids:
            for rel in self.nodes[nid].relations:
                if rel["target"] not in node_ids and rel["target"] in self.nodes:
                    meta.relations.append({
                        "target": rel["target"],
                        "type": rel["type"],
                        "created_at": datetime.now().isoformat(),
                    })
            self.nodes[nid].type = "collapsed"
            self.nodes[nid].collapsed_into = meta_id

        self._propagate_tension_diffusion()
        return {"meta_node_id": meta_id, "collapsed": node_ids, "action": "collapse"}

    def recursive_collapse(self, max_iterations=10):
        """Сжимает граф итеративно до одного мета-узла."""
        steps = []
        for i in range(max_iterations):
            active = self._active_nodes()
            if len(active) <= 1:
                break

            communities = self.find_communities()
            if not communities or len(communities) <= 1:
                all_ids = list(active.keys())
                if len(all_ids) < 2:
                    break
                meta_text = f"Meta-level {i+1}: {self.invariant}"
                result = self.collapse_cluster(all_ids, meta_text)
                steps.append(result)
                break

            largest = max(communities, key=lambda c: c["size"])
            if largest["size"] < 2:
                break
                
            meta_text = f"Cluster {largest['id']} (level {i+1})"
            result = self.collapse_cluster(largest["nodes"], meta_text)
            steps.append(result)
            
            # Проверка прогресса
            if len(self._active_nodes()) >= len(active):
                break

        return {"steps": len(steps), "remaining_active": len(self._active_nodes())}

    def cleanup_collapsed(self):
        """Физически удаляет схлопнутые узлы из памяти."""
        to_remove = [nid for nid, n in self.nodes.items() if n.type == "collapsed"]
        for nid in to_remove:
            del self.nodes[nid]
        return {"removed": len(to_remove)}

    # ── Second-order Invariants ───────────────────────

    def build_collapse_tree(self, strategy=CommunityStrategy.LOUVAIN, max_depth=3):
        """Строит дерево свёрток как граф."""
        if not HAS_NETWORKX:
            return None
        
        tree = nx.DiGraph()
        
        temp_core = GIECore(self.invariant)
        temp_core.nodes = {nid: Node.from_dict(n.to_dict()) for nid, n in self.nodes.items()}
        temp_core.next_id = self.next_id
        
        level_nodes = {}
        
        for depth in range(max_depth):
            active = temp_core._active_nodes()
            if len(active) <= 1:
                break
            
            communities = temp_core.find_communities(strategy=strategy)
            if not communities or len(communities) <= 1:
                break
            
            level_nodes[depth] = []
            
            for comm in communities:
                if comm["size"] < 2:
                    continue
                
                node_id = f"L{depth}_C{comm['id']}"
                tree.add_node(node_id, level=depth, size=comm["size"], nodes=comm["nodes"])
                level_nodes[depth].append(node_id)
                
                # Связи с предыдущим уровнем
                if depth > 0 and depth - 1 in level_nodes:
                    for parent_id in level_nodes[depth - 1]:
                        parent_nodes = set(tree.nodes[parent_id]["nodes"])
                        comm_nodes = set(comm["nodes"])
                        
                        if parent_nodes & comm_nodes:
                            overlap = len(parent_nodes & comm_nodes)
                            tree.add_edge(parent_id, node_id, overlap=overlap)
                
                # Сворачиваем
                meta_text = f"Level {depth+1} ({strategy})"
                temp_core.collapse_cluster(comm["nodes"], meta_text)
        
        return tree

    def find_second_order_invariants(self, strategies=None, max_depth=3):
        """Ищет инварианты второго порядка через сравнение деревьев свёрток."""
        if not HAS_NETWORKX:
            return {"error": "NetworkX not available"}
        
        if strategies is None:
            strategies = [
                CommunityStrategy.LOUVAIN,
                CommunityStrategy.LABEL_PROPAGATION,
            ]
        
        trees = {}
        for strategy in strategies:
            trees[strategy] = self.build_collapse_tree(strategy=strategy, max_depth=max_depth)
        
        # Сравниваем деревья
        comparisons = []
        for i, (s1, t1) in enumerate(trees.items()):
            for j, (s2, t2) in enumerate(trees.items()):
                if i >= j:
                    continue
                
                try:
                    is_iso = nx.is_isomorphic(t1, t2)
                    
                    # Сравниваем структуры уровней
                    levels1 = {}
                    levels2 = {}
                    
                    for node in t1.nodes():
                        level = t1.nodes[node]["level"]
                        if level not in levels1:
                            levels1[level] = []
                        levels1[level].append(t1.nodes[node]["size"])
                    
                    for node in t2.nodes():
                        level = t2.nodes[node]["level"]
                        if level not in levels2:
                            levels2[level] = []
                        levels2[level].append(t2.nodes[node]["size"])
                    
                    # Вычисляем сходство
                    similarity = 0.0
                    common_levels = set(levels1.keys()) & set(levels2.keys())
                    
                    for level in common_levels:
                        sizes1 = sorted(levels1[level])
                        sizes2 = sorted(levels2[level])
                        
                        if sizes1 == sizes2:
                            similarity += 1.0
                        else:
                            overlap = len(set(sizes1) & set(sizes2))
                            similarity += overlap / max(len(sizes1), len(sizes2))
                    
                    similarity /= len(common_levels) if common_levels else 1
                    
                    comparisons.append({
                        "strategy1": s1,
                        "strategy2": s2,
                        "isomorphic": is_iso,
                        "similarity": round(similarity, 3),
                    })
                except Exception as e:
                    comparisons.append({
                        "strategy1": s1,
                        "strategy2": s2,
                        "isomorphic": False,
                        "similarity": 0.0,
                        "error": str(e),
                    })
        
        # Общая устойчивость
        if comparisons:
            avg_similarity = sum(c["similarity"] for c in comparisons) / len(comparisons)
            n_isomorphic = sum(1 for c in comparisons if c["isomorphic"])
            
            return {
                "comparisons": comparisons,
                "avg_similarity": round(avg_similarity, 3),
                "n_isomorphic": n_isomorphic,
                "stability": "high" if avg_similarity > 0.8 else "medium" if avg_similarity > 0.5 else "low",
            }
        else:
            return {"error": "No comparisons possible"}

    # ── Bootstrap ─────────────────────────────────────

    def bootstrap_invariants(self, n_iterations=100, perturbation=0.1):
        """Оценивает устойчивость инвариантов через многократные возмущения."""
        original_communities = self.find_communities()
        if not original_communities:
            return {"error": "No communities to analyze"}
        
        stability_scores = []
        
        for iteration in range(n_iterations):
            # Создаем возмущенную копию
            perturbed_core = GIECore(self.invariant)
            perturbed_core.nodes = {nid: Node.from_dict(n.to_dict()) for nid, n in self.nodes.items()}
            perturbed_core.next_id = self.next_id
            
            # Возмущение
            active = perturbed_core._active_nodes()
            active_ids = list(active.keys())
            
            # Удаляем случайные ребра
            for nid, node in active.items():
                if random.random() < perturbation and node.relations:
                    idx = random.randint(0, len(node.relations) - 1)
                    node.relations.pop(idx)
            
            # Добавляем случайные ребра
            for _ in range(int(len(active_ids) * perturbation)):
                if len(active_ids) >= 2:
                    a, b = random.sample(active_ids, 2)
                    if not any(r["target"] == b for r in active[a].relations):
                        active[a].relations.append({
                            "target": b,
                            "type": "related_to",
                            "created_at": datetime.now().isoformat(),
                        })
            
            # Пересчитываем кластеры
            perturbed_communities = perturbed_core.find_communities()
            
            # Сравниваем с оригиналом
            if perturbed_communities:
                original_sets = [set(c["nodes"]) for c in original_communities]
                perturbed_sets = [set(c["nodes"]) for c in perturbed_communities]
                
                max_similarity = 0.0
                for o_set in original_sets:
                    for p_set in perturbed_sets:
                        intersection = len(o_set & p_set)
                        union = len(o_set | p_set)
                        jaccard = intersection / union if union > 0 else 0
                        max_similarity = max(max_similarity, jaccard)
                
                stability_scores.append(max_similarity)
        
        # Статистика
        if stability_scores:
            avg_stability = sum(stability_scores) / len(stability_scores)
            std_stability = (sum((x - avg_stability) ** 2 for x in stability_scores) / len(stability_scores)) ** 0.5
            
            return {
                "iterations": n_iterations,
                "avg_stability": round(avg_stability, 3),
                "std_stability": round(std_stability, 3),
                "min_stability": round(min(stability_scores), 3),
                "max_stability": round(max(stability_scores), 3),
                "confidence": "high" if std_stability < 0.1 else "medium" if std_stability < 0.2 else "low",
            }
        else:
            return {"error": "No stability data"}

    # ── Temporal Analysis ─────────────────────────────

    def temporal_analysis(self, window_hours=24):
        """Анализирует эволюцию графа во времени."""
        now = datetime.now()
        
        active_nodes = []
        recent_nodes = []
        old_nodes = []
        
        for nid, node in self.nodes.items():
            if node.type == "collapsed":
                continue
            
            hours_since_birth = (now - node.birth).total_seconds() / 3600
            hours_since_activation = (now - node.last_activation).total_seconds() / 3600
            
            node_info = {
                "id": nid,
                "text": node.text[:40],
                "age_hours": round(hours_since_birth, 2),
                "last_active_hours": round(hours_since_activation, 2),
                "activation_count": node.activation_count,
                "tension": node.tension,
            }
            
            if hours_since_activation <= window_hours:
                recent_nodes.append(node_info)
            elif hours_since_birth <= window_hours * 2:
                active_nodes.append(node_info)
            else:
                old_nodes.append(node_info)
        
        return {
            "recent": recent_nodes,
            "active": active_nodes,
            "old": old_nodes,
            "total_active": len(recent_nodes) + len(active_nodes),
        }

    # ── Unfold ────────────────────────────────────────

    def change_invariant(self, new_invariant):
        """Меняет инвариант (новый цикл)."""
        old = self.invariant
        if self._active_nodes():
            self.history.append({
                "invariant": old,
                "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
                "final_tension": self.total_tension(),
                "geometry": self.geometry(),
                "completed_at": datetime.now().isoformat(),
            })
        self.invariant = new_invariant
        self.nodes = {}
        self.next_id = 1
        return {"old_invariant": old, "new_invariant": new_invariant,
                "action": "unfold", "history_length": len(self.history)}

    # ── Full analysis report ──────────────────────────

    def full_report(self):
        """Полный аналитический отчёт."""
        lines = []
        lines.append("=" * 60)
        lines.append("GIE — GEOMETRIC ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append(f"Invariant: {self.invariant}")
        lines.append(f"Total tension: {self.total_tension()}")
        geo = self.geometry()
        lines.append(f"Nodes: {geo['nodes']} | Edges: {geo['edges']} | "
                      f"Clusters: {geo['clusters']} | Isolated: {geo['isolated']}")
        lines.append("")

        if not HAS_NETWORKX:
            lines.append("(Install networkx for full analysis: pip install networkx)")
            return "\n".join(lines)

        comms = self.find_communities()
        if comms:
            lines.append("COMMUNITIES (Louvain):")
            for c in comms:
                lines.append(f"  Community {c['id']}: {c['size']} nodes")
                for t in c["texts"][:3]:
                    lines.append(f"    - {t}")
            lines.append("")

        bridges = self.find_bridges()
        if bridges:
            lines.append("BRIDGES (articulation points):")
            for b in bridges:
                lines.append(f"  [{b['node_id']}] {b['text']} (t={b['tension']})")
            lines.append("")

        cent = self.calculate_centrality()
        if cent:
            lines.append("CENTRALITY (betweenness):")
            for c in cent[:5]:
                lines.append(f"  [{c['node_id']}] b={c['betweenness']:.3f} | {c['text']}")
            lines.append("")

        cands = self.find_dense_clusters()
        if cands:
            lines.append("DENSE CLUSTERS (Geometric candidates for abstraction):")
            for c in cands[:3]:
                lines.append(f"  Nodes {c['nodes']}, density={c['density']}, score={c['score']}")
                for t in c["texts"][:2]:
                    lines.append(f"    - {t}")
            lines.append("")

        missing = self.find_missing_bridges()
        if missing:
            lines.append("POTENTIAL BRIDGES (missing edges that reduce fragmentation):")
            for m in missing[:3]:
                lines.append(f"  [{m['source']}] ↔ [{m['target']}] "
                              f"(reduces clusters by {m['reduction']})")
            lines.append("")

        unifying = self.find_lexical_bridges()
        if unifying:
            lines.append("LEXICAL BRIDGES (Shared vocabulary across clusters):")
            lines.append(f"  {unifying['suggested_concept']}")
            lines.append(f"  Reason: {unifying['reason']}")
            lines.append("")

        stab = self.stability_analysis()
        lines.append(f"STABILITY: {stab['reason']} (fragility={stab.get('fragility', 'N/A')})")
        lines.append("")

        if geo["hot_spots"]:
            lines.append("HOT SPOTS 🔥:")
            for h in geo["hot_spots"]:
                lines.append(f"  [{h['id']}] t={h['tension']} | {h['text']}")
            lines.append("")

        return "\n".join(lines)

    # ── Witness ───────────────────────────────────────

    def witness_display(self):
        """Отображение состояния для witness."""
        if not self.witness_enabled:
            return None
        geo = self.geometry()
        lines = [
            f"Nodes: {geo['nodes']}",
            f"Edges: {geo['edges']}",
            f"Clusters: {geo['clusters']}",
            f"Isolated: {geo['isolated']}",
            f"Tension: {self.total_tension()}",
        ]
        if geo["hot_spots"]:
            lines.append(f"Hot spots: {len(geo['hot_spots'])}")
        return "\n".join(lines)

    # ── Serialization ─────────────────────────────────

    def to_dict(self):
        return {
            "invariant": self.invariant,
            "nodes": {str(nid): n.to_dict() for nid, n in self.nodes.items()},
            "next_id": self.next_id,
            "history": self.history,
            "witness_enabled": self.witness_enabled,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data):
        core = cls(data["invariant"], data.get("witness_enabled", False))
        core.next_id = data.get("next_id", 1)
        core.history = data.get("history", [])
        core.created_at = data.get("created_at", datetime.now().isoformat())
        for nid, nd in data.get("nodes", {}).items():
            core.nodes[int(nid)] = Node.from_dict(nd)
        return core

    def save(self, filename="gie_session.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filename="gie_session.json"):
        with open(filename, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ── Visualization ─────────────────────────────────

    def visualize_ascii(self):
        """ASCII визуализация графа."""
        active = self._active_nodes()
        if not active:
            return "(empty graph)"

        lines = [f"INVARIANT: {self.invariant}", f"Tension: {self.total_tension()}", ""]

        G = self._build_nx()
        if G and HAS_NETWORKX:
            try:
                comms = nx.community.louvain_communities(G, seed=42)
                for i, comm in enumerate(comms):
                    lines.append(f"Community {i}:")
                    for nid in sorted(comm):
                        n = self.nodes[nid]
                        fire = " 🔥" if n.tension > 2.0 else ""
                        lines.append(f"  [{nid}] {n.text} (t={n.tension}){fire}")
                        for rel in n.relations:
                            if rel["target"] in comm:
                                lines.append(f"      → [{rel['target']}] ({rel['type']})")
                    lines.append("")
            except Exception:
                pass

        isolated = [nid for nid, n in active.items() if not n.relations]
        if isolated:
            lines.append("Isolated:")
            for nid in isolated:
                n = self.nodes[nid]
                lines.append(f"  [{nid}] {n.text} (t={n.tension})")

        return "\n".join(lines)

    def visualize_force_layout(self):
        """Force-layout визуализация с координатами."""
        G = self._build_nx()
        if not G or G.number_of_nodes() == 0:
            return "(empty graph)"
        
        try:
            pos = nx.spring_layout(G, k=1.0, iterations=50, seed=42)
            
            lines = [f"INVARIANT: {self.invariant}", f"Tension: {self.total_tension()}", ""]
            
            communities = self.find_communities()
            for comm in communities:
                lines.append(f"Community {comm['id']}:")
                for nid in comm["nodes"]:
                    node = self.nodes[nid]
                    x, y = pos[nid]
                    fire = " 🔥" if node.tension > 2.0 else ""
                    lines.append(f"  [{nid}] {node.text[:30]} (t={node.tension}){fire} @ ({x:.2f}, {y:.2f})")
                lines.append("")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Visualization error: {e}"
