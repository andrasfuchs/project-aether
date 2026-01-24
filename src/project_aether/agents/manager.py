import logging
from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage

# Import (future) agent nodes
# We use conditional imports or mocks for now so this file compiles immediately
try:
    from project_aether.agents.researcher import research_jurisdiction
    from project_aether.agents.analyst import analyze_batch
except ImportError:
    # Mocks for testing flow before other agents are built
    async def research_jurisdiction(state): return {"raw_patents": [{"id": "RU-MOCK-1", "status": "FC9A"}]}
    async def analyze_batch(state): return {"artifacts": [{"id": "RU-MOCK-1", "score": 95}]}

# Configure Logging
logger = logging.getLogger("ManagerAgent")

# 1. Define the Mission State
# This dict holds the data as it flows between agents
class MissionState(TypedDict):
    mission_id: str
    target_jurisdictions: List[str]
    date_range: tuple[str, str]
    
    # Data Accumulation
    raw_patents: Annotated[List[Dict], "extend_list"]  # Researcher adds to this
    analyzed_artifacts: List[Dict]                     # Analyst produces these
    
    # Execution Flags
    error_log: List[str]
    is_complete: bool

# 2. Define the Nodes (The Agent Steps)

async def planning_node(state: MissionState):
    """
    The Manager Agent determines the scope of the mission.
    """
    logger.info(f"--- 🕵️ MANAGER: Planning Mission {state.get('mission_id')} ---")
    
    # In a real scenario, this could query a DB for 'last_run_date'
    # For now, we pass through the user-defined state
    jurisdictions = state.get("target_jurisdictions", [])
    
    if not jurisdictions:
        logger.warning("No jurisdictions defined. Defaulting to RU (Russia).")
        return {"target_jurisdictions": ["RU"]}
    
    return {"target_jurisdictions": jurisdictions}

async def execution_router(state: MissionState):
    """
    Decides if we found patents worth analyzing.
    """
    count = len(state.get("raw_patents", []))
    logger.info(f"--- 🕵️ MANAGER: Reviewing Search Results ({count} found) ---")
    
    if count > 0:
        return "analyze"
    else:
        logger.info("No patents found. Skipping analysis.")
        return "end"

# 3. Build the Graph (The "Antigravity" Engine)

def build_mission_graph():
    """
    Constructs the LangGraph state machine.
    """
    workflow = StateGraph(MissionState)

    # Add Nodes
    workflow.add_node("planner", planning_node)
    workflow.add_node("researcher", research_jurisdiction)
    workflow.add_node("analyst", analyze_batch)

    # Define the Entry Point
    workflow.set_entry_point("planner")

    # Define Edges (The Logic Flow)
    
    # 1. Plan -> Research
    workflow.add_edge("planner", "researcher")

    # 2. Research -> Decision (Analyze or End?)
    workflow.add_conditional_edges(
        "researcher",
        execution_router,
        {
            "analyze": "analyst",
            "end": END
        }
    )

    # 3. Analyze -> End
    workflow.add_edge("analyst", END)

    # Compile the graph
    return workflow.compile()

# 4. Entry Point for the "Monday Morning" Run
async def run_weekly_mission(mission_id: str = "weekly_run"):
    app = build_mission_graph()
    
    initial_state = {
        "mission_id": mission_id,
        "target_jurisdictions": ["RU", "PL", "RO", "CZ"],
        "date_range": ("2025-01-01", "2025-01-07"), # Example window
        "raw_patents": [],
        "analyzed_artifacts": [],
        "error_log": [],
        "is_complete": False
    }

    logger.info("Initializing Agent Swarm...")
    
    # Run the graph
    async for output in app.astream(initial_state):
        for key, value in output.items():
            logger.info(f"Finished Node: {key}")

    return "Mission Complete"