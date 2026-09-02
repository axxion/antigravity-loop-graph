"""
LoopGraph StateGraph & Execution Engine.
Provides a flexible, DAG / cyclic workflow graph with conditional routing and state checkpointing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from loopgraph.core.state import ProjectState

logger = logging.getLogger("loopgraph.graph")

END = "__END__"
START = "__START__"


class BaseNode(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, state: ProjectState) -> Union[str, None]:
        """
        Executes node logic on the state.
        Returns optional transition signal or None.
        """
        pass


@dataclass
class Edge:
    from_node: str
    to_node: str


@dataclass
class ConditionalEdge:
    from_node: str
    router: Callable[[ProjectState, Optional[str]], str]


class StateGraph:
    def __init__(self):
        self.nodes: Dict[str, BaseNode] = {}
        self.edges: List[Edge] = []
        self.conditional_edges: List[ConditionalEdge] = []
        self.entry_point: Optional[str] = None

    def add_node(self, node: BaseNode) -> StateGraph:
        self.nodes[node.name] = node
        return self

    def set_entry_point(self, node_name: str) -> StateGraph:
        if node_name not in self.nodes:
            raise ValueError(f"Düğüm bulunamadı: {node_name}")
        self.entry_point = node_name
        return self

    def add_edge(self, from_node: str, to_node: str) -> StateGraph:
        if from_node not in self.nodes and from_node != START:
            raise ValueError(f"Başlangıç düğümü bulunamadı: {from_node}")
        if to_node not in self.nodes and to_node != END:
            raise ValueError(f"Hedef düğüm bulunamadı: {to_node}")
        self.edges.append(Edge(from_node=from_node, to_node=to_node))
        return self

    def add_conditional_edge(
        self, from_node: str, router: Callable[[ProjectState, Optional[str]], str]
    ) -> StateGraph:
        if from_node not in self.nodes:
            raise ValueError(f"Düğüm bulunamadı: {from_node}")
        self.conditional_edges.append(ConditionalEdge(from_node=from_node, router=router))
        return self

    def compile(self) -> GraphRunner:
        if not self.entry_point:
            raise ValueError("Graf için entry_point belirlenmedi.")
        return GraphRunner(self)


class GraphRunner:
    def __init__(self, graph: StateGraph):
        self.graph = graph

    def _get_next_node(
        self, current_node: str, state: ProjectState, signal: Optional[str]
    ) -> str:
        # Check conditional edges first
        for ce in self.graph.conditional_edges:
            if ce.from_node == current_node:
                return ce.router(state, signal)

        # Check static edges
        for e in self.graph.edges:
            if e.from_node == current_node:
                return e.to_node

        # If no edge found, graph terminates
        return END

    def run(
        self,
        state: ProjectState,
        max_steps: int = 100,
        on_node_start: Optional[Callable[[str, ProjectState], None]] = None,
        on_node_finish: Optional[Callable[[str, Optional[str], ProjectState], None]] = None,
    ) -> ProjectState:
        current_node_name = self.graph.entry_point
        step_count = 0

        while current_node_name != END and step_count < max_steps:
            if current_node_name not in self.graph.nodes:
                logger.error(f"Bilinmeyen düğüm: {current_node_name}")
                break

            node = self.graph.nodes[current_node_name]
            step_count += 1
            state.iteration = step_count

            if on_node_start:
                on_node_start(current_node_name, state)

            try:
                signal = node.run(state)
            except Exception as e:
                logger.exception(f"[{current_node_name}] düğümünde hata oluştu: {e}")
                signal = "ERROR"

            if on_node_finish:
                on_node_finish(current_node_name, signal, state)

            next_node_name = self._get_next_node(current_node_name, state, signal)
            current_node_name = next_node_name

        return state
