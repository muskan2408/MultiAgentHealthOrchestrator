from src.agents.base_agent import BaseAgent
from src.agents.lifestyle_agent import LifestyleAgent
from src.agents.medication_agent import MedicationAgent
from src.agents.symptom_agent import SymptomAgent
from src.models.schemas import AgentType

AGENT_REGISTRY: dict[AgentType, BaseAgent] = {
    AgentType.SYMPTOM: SymptomAgent(),
    AgentType.MEDICATION: MedicationAgent(),
    AgentType.LIFESTYLE: LifestyleAgent(),
}