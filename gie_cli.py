#!/usr/bin/env python3
"""
GIE CLI — Geometric Invariant Explorer Command Line Interface
"""

from gie import GIECore
import sys

HELP = """
Commands:
  add <text>                  Add a difference
  relate <s> <t> <type>       Connect two nodes
  status                      Show geometry summary
  view                        ASCII visualization
  view-force                  Force-layout visualization
  analyze                     Full geometric analysis
  communities [strategy]      Show communities (louvain|label|girvan)
  bridges                     Show bridge nodes
  centrality                  Show betweenness centrality
  clusters                    Show dense clusters
  motifs                      Show isomorphic motifs
  potential                   Show missing bridges + lexical bridges
  stability                   Run stability analysis
  spectral                    Show spectral signature
  distance <file>             Compare with another graph
  temporal                    Show temporal analysis
  bootstrap                   Bootstrap invariants stability
  invariants-2nd              Find second-order invariants
  semantic                    Suggest semantic relations (requires embeddings)
  collapse <ids> <text>       Collapse nodes into meta-node
  collapse-all                Recursive collapse to single node
  cleanup                     Physically remove collapsed nodes
  unfold                      Change invariant (new cycle)
  save [file]                 Save session
  history                     Show cycle history
  help                        Show this help
  done                        Finish session

Relation types:
  related_to, contradicts, bridges, supports, mirrors,
  contains, transforms, depends_on, analogous, same_pattern
"""

def main():
    print("=" * 60)
    print("GIE — Geometric Invariant Explorer")
    print("=" * 60)
    print()
    print("This tool holds your tension as geometry.")
    print("It analyzes structure, finds bridges, suggests invariants.")
    print("You look. You hold. You see — or you don't.")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--load":
        fn = sys.argv[2] if len(sys.argv) > 2 else "gie_session.json"
        core = GIECore.load(fn)
        print(f"Loaded: {core.invariant} ({len(core._active_nodes())} active nodes)")
    else:
        inv = input("What invariant are you trying to hold?\n> ").strip()
        w = input("Enable witness display? (y/n) [n]: ").strip().lower() == "y"
        core = GIECore(invariant=inv, witness_enabled=w)

    print(HELP)

    while True:
        raw = input("> ").strip()
        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "done":
            print("\nFinal geometry:")
            print(core.visualize_ascii())
            break

        elif cmd == "help":
            print(HELP)

        elif cmd == "add":
            if not arg:
                print("Usage: add <text>")
                continue
            r = core.add_difference(arg)
            print(f"Added [{r['node'].id}] | Tension: {r['tension']}")
            if r["suggestions"]:
                for s in r["suggestions"][:3]:
                    print(f"  💡 [{s['source']}] ↔ [{s['target']}] "
                          f"({', '.join(s['common_words'])})")

        elif cmd == "relate":
            try:
                rp = arg.split()
                s, t = int(rp[0]), int(rp[1])
                rt = rp[2] if len(rp) > 2 else "related_to"
                r = core.relate(s, t, rt)
                if "error" in r:
                    print(f"Error: {r['error']}")
                else:
                    print(f"[{s}] → [{t}] ({rt}) | Tension: {r['tension']}")
            except (ValueError, IndexError):
                print("Usage: relate <source> <target> <type>")

        elif cmd == "status":
            g = core.geometry()
            print(f"\nInvariant: {core.invariant}")
            print(f"Nodes: {g['nodes']} | Edges: {g['edges']} | "
                  f"Clusters: {g['clusters']} | Isolated: {g['isolated']}")
            print(f"Tension: {core.total_tension()}")
            w = core.witness_display()
            if w:
                print(f"\nWitness:\n{w}")
            print()

        elif cmd == "view":
            print("\n" + core.visualize_ascii() + "\n")

        elif cmd == "view-force":
            print("\n" + core.visualize_force_layout() + "\n")

        elif cmd == "analyze":
            print("\n" + core.full_report() + "\n")

        elif cmd == "communities":
            strategy = arg.strip() or "louvain"
            comms = core.find_communities(strategy=strategy)
            if not comms:
                print("No communities found.")
            else:
                print(f"Strategy: {strategy}")
                for c in comms:
                    print(f"Community {c['id']} ({c['size']} nodes):")
                    for t in c["texts"][:5]:
                        print(f"  - {t}")
                    print()

        elif cmd == "bridges":
            br = core.find_bridges()
            if not br:
                print("No bridge nodes found.")
            else:
                for b in br:
                    print(f"  [{b['node_id']}] {b['text']} (t={b['tension']})")
            print()

        elif cmd == "centrality":
            c = core.calculate_centrality()
            if not c:
                print("Not enough data.")
            else:
                for x in c[:10]:
                    print(f"  [{x['node_id']}] b={x['betweenness']:.3f} "
                          f"d={x['degree']} | {x['text']}")
            print()

        elif cmd == "clusters":
            cands = core.find_dense_clusters()
            if not cands:
                print("No dense clusters found.")
            else:
                for c in cands[:5]:
                    print(f"  Nodes {c['nodes']} | density={c['density']} "
                          f"score={c['score']}")
                    for t in c["texts"][:2]:
                        print(f"    - {t}")
            print()

        elif cmd == "motifs":
            motifs = core.find_motifs_isomorphic(size=3)
            if not motifs:
                print("No motifs found.")
            elif motifs and "error" in motifs[0]:
                print(f"Error: {motifs[0]['error']}")
            else:
                for m in motifs:
                    print(f"Motif size {m['size']}: {m['count']} instances")
                    for inst in m["instances"][:3]:
                        print(f"  Nodes: {inst}")
                print()

        elif cmd == "potential":
            missing = core.find_missing_bridges()
            if missing:
                print("MISSING BRIDGES:")
                for m in missing[:5]:
                    print(f"  [{m['source']}] ↔ [{m['target']}] "
                          f"(reduces clusters by {m['reduction']})")
            unifying = core.find_lexical_bridges()
            if unifying:
                print(f"\nLEXICAL BRIDGES: {unifying['suggested_concept']}")
                print(f"  {unifying['reason']}")
            print()

        elif cmd == "stability":
            s = core.stability_analysis()
            print(f"Stability: {s['reason']}")
            if "fragility" in s:
                print(f"Fragility: {s['fragility']}")
            print()

        elif cmd == "spectral":
            spec = core.spectral_signature()
            if "error" in spec:
                print(f"Error: {spec['error']}")
            else:
                print(f"Spectral Signature (normalized):")
                print(f"  Laplacian: {spec['laplacian'][:10]}")
                print(f"  Adjacency: {spec['adjacency'][:10]}")
                print(f"  Nodes: {spec['n_nodes']}, Edges: {spec['n_edges']}")
            print()

        elif cmd == "distance":
            fn = arg.strip()
            if not fn:
                print("Usage: distance <file>")
            else:
                try:
                    other = GIECore.load(fn)
                    dist = core.spectral_distance(other)
                    print(f"Spectral distance: {dist}")
                except Exception as e:
                    print(f"Error: {e}")
            print()

        elif cmd == "temporal":
            analysis = core.temporal_analysis()
            print(f"Temporal Analysis:")
            print(f"  Recent (active <24h): {len(analysis['recent'])}")
            print(f"  Active (active <48h): {len(analysis['active'])}")
            print(f"  Old: {len(analysis['old'])}")
            print()

        elif cmd == "bootstrap":
            print("Running bootstrap analysis (100 iterations)...")
            result = core.bootstrap_invariants()
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Bootstrap Results:")
                print(f"  Avg stability: {result['avg_stability']}")
                print(f"  Std: {result['std_stability']}")
                print(f"  Range: [{result['min_stability']}, {result['max_stability']}]")
                print(f"  Confidence: {result['confidence']}")
            print()

        elif cmd == "invariants-2nd":
            print("Comparing collapse trees across strategies...")
            result = core.find_second_order_invariants()
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                for comp in result["comparisons"]:
                    print(f"  {comp['strategy1']} vs {comp['strategy2']}: similarity={comp['similarity']}")
                print(f"\nAverage similarity: {result['avg_similarity']}")
                print(f"Stability: {result['stability']}")
            print()

        elif cmd == "semantic":
            suggestions = core.suggest_semantic_relations()
            if not suggestions:
                print("No semantic suggestions (embeddings not available or no matches).")
            else:
                for s in suggestions:
                    print(f"  [{s['source']}] ↔ [{s['target']}] similarity={s['similarity']}")
                print()

        elif cmd == "collapse":
            cp = arg.split()
            ids = [int(x) for x in cp if x.isdigit()]
            text = " ".join(x for x in cp if not x.isdigit()) or "Meta-node"
            if not ids:
                print("Usage: collapse <id1> <id2> ... <text>")
                continue
            r = core.collapse_cluster(ids, text)
            if "error" in r:
                print(f"Error: {r['error']}")
            else:
                print(f"Collapsed {r['collapsed']} → [{r['meta_node_id']}]")

        elif cmd == "collapse-all":
            r = core.recursive_collapse()
            print(f"Recursive collapse: {r['steps']} steps, "
                  f"{r['remaining_active']} active nodes remaining")

        elif cmd == "cleanup":
            r = core.cleanup_collapsed()
            print(f"Removed {r['removed']} collapsed nodes from memory.")

        elif cmd == "unfold":
            new_inv = input("New invariant: ").strip()
            if not new_inv:
                continue
            r = core.change_invariant(new_inv)
            print(f"Unfold: '{r['old_invariant']}' → '{r['new_invariant']}'")
            print(f"Cycle #{r['history_length']} saved.")

        elif cmd == "save":
            fn = arg.strip() or "gie_session.json"
            core.save(fn)
            print(f"Saved to {fn}")

        elif cmd == "history":
            if not core.history:
                print("No history yet.")
            else:
                for i, h in enumerate(core.history, 1):
                    print(f"Cycle #{i}: {h['invariant']} "
                          f"({len(h['nodes'])} nodes, t={h['final_tension']})")
            print()

        else:
            # По умолчанию — add
            r = core.add_difference(raw)
            print(f"Added [{r['node'].id}] | Tension: {r['tension']}")

if __name__ == "__main__":
    main()
