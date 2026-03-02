"""

Execution graph orchestrator for Thalos Prime:

Seed -> Enumerate -> Retrieve -> Score -> Project

Provides deterministic provenance and entropy-indexed records for downstream storage.

"""

from typing import List, Dict, Any, Callable

from dataclasses import dataclass, field

import time

import uuid



from src.lob_babel_enumerator import enumerate_addresses

from src.lob_babel_search import search_and_fetch

from src.lob_decoder import score_coherence

from src.babel_search_expansion import babel_search_expansion





@dataclass

class GraphResult:

    token: str

    address: Dict[str, Any]

    text: str

    score: float

    stage: str

    provenance: Dict[str, Any] = field(default_factory=dict)





class ExecutionGraph:

    """Combinatorial pipeline with pluggable stages and provenance."""



    def __init__(self, mode: str = "hybrid"):

        # mode: live | deterministic | hybrid

        self.mode = mode



    def run(self, query: str, max_results: int = 5) -> List[GraphResult]:

        start = time.time()

        provenance: Dict[str, Any] = {

            "graph_id": str(uuid.uuid4()),

            "mode": self.mode,

            "ts": start,

            "query": query,

        }



        # Stage 1: enumerate candidate addresses (lightweight)

        addresses = enumerate_addresses(query, max_per_size=max_results)

        results: List[GraphResult] = []



        # Stage 2: retrieve pages (live search fallback)

        for addr in addresses:

            fragment = addr.get("fragment", query)

            pages = search_and_fetch(fragment, max_results=1)

            for page in pages:

                sc = score_coherence(page.get("text", ""), query)

                results.append(

                    GraphResult(

                        token=fragment,

                        address=page.get("address", {}),

                        text=page.get("text", ""),

                        score=sc,

                        stage="live_fetch",

                        provenance={**provenance, "source": "live", "fragment": fragment},

                    )

                )



        # Stage 3: deterministic expansion fallback ensures non-empty

        if not results:

            expanded = babel_search_expansion(query)

            results.append(

                GraphResult(

                    token=query,

                    address={"url": "deterministic://local"},

                    text=expanded,

                    score=100.0,

                    stage="deterministic_expansion",

                    provenance={**provenance, "source": "deterministic"},

                )

            )



        # Stage 4: project / rank

        results.sort(key=lambda r: r.score, reverse=True)

        return results





def execute_graph(query: str, max_results: int = 5, mode: str = "hybrid") -> List[GraphResult]:

    graph = ExecutionGraph(mode=mode)

    return graph.run(query, max_results=max_results)



