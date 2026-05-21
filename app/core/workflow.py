from __future__ import annotations

from langgraph.graph import START, END, StateGraph

from app.agents.planner import planner_agent
from app.agents.researcher import researcher_agent
from app.agents.writer import writer_agent
from app.core.llm import OpenAIClient
from app.models.schemas import LearningState


class LearningWorkflow:
    def __init__(self, llm_client: OpenAIClient | None = None) -> None:
        self.llm_client = llm_client or OpenAIClient()
        self.graph = self._build_graph()
        self.compiled = self.graph.compile()

    def _build_graph(self) -> StateGraph[LearningState, None, LearningState, LearningState]:
        graph = StateGraph(LearningState)
        graph.add_node("planner", self._planner_node)
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("writer", self._writer_node)
        graph.set_entry_point("planner")
        graph.add_edge("planner", "researcher")
        graph.add_edge("researcher", "writer")
        graph.set_finish_point("writer")
        return graph

    def _planner_node(self, state: LearningState) -> LearningState:
        planner_result = planner_agent(state, self.llm_client)
        return {"planner_result": planner_result}

    def _researcher_node(self, state: LearningState) -> LearningState:
        researcher_result = researcher_agent(state, self.llm_client)
        return {"researcher_result": researcher_result}

    def _writer_node(self, state: LearningState) -> LearningState:
        final_markdown = writer_agent(state)
        return {"final_markdown": final_markdown}

    def run(self, goal: str, level: str, duration: str) -> LearningState:
        initial_state: LearningState = {
            "goal": goal,
            "level": level,
            "duration": duration,
        }
        return self.compiled.invoke(initial_state)
