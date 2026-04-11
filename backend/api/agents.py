from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.agent import Agent, AgentRole, AgentStatus
from backend.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse)
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    db_agent = Agent(
        name=agent.name,
        role=agent.role,
        description=agent.description,
        capabilities=agent.capabilities,
        model_profile=agent.model_profile,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent


@router.get("/", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: int, update: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.post("/seed")
def seed_agents(db: Session = Depends(get_db)):
    existing = db.query(Agent).count()
    if existing > 0:
        return {"message": f"{existing} agents already exist"}

    agents = [
        Agent(name="ProjectManager", role=AgentRole.PROJECT_MANAGER,
              description="Breaks requests into tasks, plans execution order",
              capabilities=["planning", "estimation", "coordination"]),
        Agent(name="UXDesigner", role=AgentRole.UX_DESIGNER,
              description="Creates wireframes, user flows, design specs",
              capabilities=["wireframing", "prototyping", "accessibility"]),
        Agent(name="FrontendDev", role=AgentRole.FRONTEND_DEV,
              description="Implements React + TypeScript UI components",
              capabilities=["react", "typescript", "css", "responsive"]),
        Agent(name="BackendDev", role=AgentRole.BACKEND_DEV,
              description="Builds FastAPI endpoints and business logic",
              capabilities=["python", "fastapi", "sql", "api_design"]),
        Agent(name="FullStackEngineer", role=AgentRole.FULLSTACK,
              description="End-to-end feature implementation",
              capabilities=["react", "python", "api", "integration"]),
        Agent(name="Researcher", role=AgentRole.RESEARCH,
              description="Technical research, analysis, and recommendations",
              capabilities=["research", "analysis", "architecture"]),
        Agent(name="DBEngineer", role=AgentRole.DB_ENGINEER,
              description="Database schema design, optimization, migrations",
              capabilities=["sql", "schema_design", "performance", "migrations"]),
    ]
    for agent in agents:
        db.add(agent)
    db.commit()
    return {"message": f"Seeded {len(agents)} agents"}
