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
    pub name: String,
    pub position: String,
    pub is_leader: bool,
    pub instructions: Vec<String>,
    pub responsibilities: Vec<String>,
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct AgentConfig {
    pub memory_context_size: u16,
}