// The call-answer, callback interface.

use serde::{Deserialize, Serialize};
use sangedama::node::node::Message;

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync {
    async fn on_message(&self, agent_id: String, message: Message);
}

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait Processor: Send + Sync {
    async fn run(&self, input: Vec<u8>) -> ();
}

#[derive(Deserialize, Serialize, Debug, Clone, Default)]
pub struct AgentDefinition {
    pub id: Option<String>,
    pub name: String,
    pub position: String,
    pub is_leader: bool,
    pub instructions: Vec<String>,
    pub responsibilities: Vec<String>,
    pub is_completed: bool,
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct AgentConfig {
    pub memory_context_size: u16,
}


// Builders
pub struct AgentDefinitionBuilder {
    id: Option<String>,
    name: String,
    position: String,
    is_leader: bool,
    instructions: Vec<String>,
    responsibilities: Vec<String>,
    is_completed: bool,
}

impl AgentDefinitionBuilder {
    pub fn new() -> Self {
        AgentDefinitionBuilder {
            id: None,
            name: String::new(),
            position: String::new(),
            is_leader: false,
            instructions: Vec::new(),
            responsibilities: Vec::new(),
            is_completed: false,
        }
    }

    pub fn id(mut self, id: String) -> Self {
        self.id = Some(id);
        self
    }

    pub fn name(mut self, name: String) -> Self {
        self.name = name;
        self
    }

    pub fn position(mut self, position: String) -> Self {
        self.position = position;
        self
    }

    pub fn is_leader(mut self, is_leader: bool) -> Self {
        self.is_leader = is_leader;
        self
    }

    pub fn instructions(mut self, instructions: Vec<String>) -> Self {
        self.instructions = instructions;
        self
    }

    pub fn responsibilities(mut self, responsibilities: Vec<String>) -> Self {
        self.responsibilities = responsibilities;
        self
    }
    pub fn complete(mut self, is_completed: bool) -> Self {
        self.is_completed = is_completed;
        self
    }

    pub fn build(self) -> AgentDefinition {
        AgentDefinition {
            id: self.id,
            name: self.name,
            position: self.position,
            is_leader: self.is_leader,
            instructions: self.instructions,
            responsibilities: self.responsibilities,
            is_completed: self.is_completed,
        }
    }
}
