# GIE — Geometric Invariant Explorer

A platform for exploring the structure of thinking and knowledge.

## What this is

GIE holds your problems, ideas, and contradictions as a graph. Then it analyzes the geometry: finds bridges between clusters, detects repeating motifs, measures centrality, suggests missing connections, and proposes candidate invariants.

It does not solve problems. It reveals the shape of your stuckness.

## What this is NOT

- NOT an AI assistant
- NOT a problem solver
- NOT a mind map tool
- NOT a knowledge graph database

No one will tell you what to think. The tool holds geometry. You do the seeing.

## Quick start

```bash
pip install -r requirements.txt
python gie_cli.py

## Features
Core Analysis
Tension Field: Diffusion-based tension propagation with guaranteed convergence
Community Detection: Multiple strategies (Louvain, Label Propagation, Girvan-Newman)
Bridge Detection: Articulation points and missing bridges
Centrality: Betweenness centrality analysis
Dense Clusters: Geometric candidates for abstraction
Advanced Analysis
Spectral Signature: Laplacian and adjacency eigenvalues for graph comparison
Spectral Distance: Measure similarity between different graphs
Isomorphic Motifs: Find structurally identical subgraphs
Second-order Invariants: Compare collapse trees across different strategies
Bootstrap Stability: Statistical reliability of discovered structures
Temporal Analysis: Track graph evolution over time
Semantic Analysis (Optional)
Semantic Relations: Suggest connections using sentence embeddings (requires sentence-transformers)

## Commands
Command       Description
add <text> -Add a difference node
relate <s> <t> <type> -Connect two nodes
status -Geometry summary
view -ASCII visualization
view-force -Force-layout visualization
analyze -Full geometric analysis
communities [strategy] -Community detection (louvain|label|girvan)
bridges -Articulation points
centrality -Betweenness centrality
clusters -Dense clusters
motifs -Isomorphic motifs
potential -Missing bridges + lexical bridges
stability -Structural stability analysis
spectral -Spectral signature
distance <file> -Compare with another graph
temporal -Temporal analysis
bootstrap -Bootstrap invariants stability
invariants-2nd -Second-order invariants
semantic -Semantic relation suggestions
collapse <ids> <text> -Collapse nodes into meta-node
collapse-all -Recursive collapse
cleanup -Remove collapsed nodes
unfold -Change invariant (new cycle)
save [file] -Save session
history -Show cycle history

> add API returns 500 under load
Added [1] | Tension: 1.0

> add Database locks on concurrent requests
Added [2] | Tension: 2.0

> relate 1 2 contradicts
[1] → [2] (contradicts) | Tension: 8.0

> analyze
============================================================
GIE — GEOMETRIC ANALYSIS REPORT
============================================================
Invariant: The system must remain responsive
Total tension: 8.0
Nodes: 2 | Edges: 1 | Clusters: 1 | Isolated: 0

COMMUNITIES (Louvain):
  Community 0: 2 nodes
    - API returns 500 under load
    - Database locks on concurrent requests

STABILITY: Low fragility — structure holds (fragility=0.0)


User
  │
CLI (gie_cli.py)
  │
GIECore (gie.py)
  │
NetworkX + NumPy Analysis

from gie import GIECore

core = GIECore(invariant="System coherence")
core.add_difference("Module A fails under load")
core.add_difference("Module B has circular dependency")
core.relate(1, 2, "contradicts")

print(core.full_report())

# Spectral analysis
spec = core.spectral_signature()
print(f"Laplacian eigenvalues: {spec['laplacian'][:5]}")

# Second-order invariants
invariants = core.find_second_order_invariants()
print(f"Stability: {invariants['stability']}")

!!!  Philosophy
GIE is based on TGS (Theory of Geometric Self-Unfolding). See MANIFESTO.md for the full framework.
Core ideas:
Errors are curvature data, not bugs
Tension is the condition for recognition, not a problem
Invariants emerge through friction, not in isolation
Recognition requires an Other

License MIT.
