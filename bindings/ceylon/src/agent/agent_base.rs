use std::fmt::Debug;

use serde::{Deserialize, Serialize};

use sangedama::node::node::Message;

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync + Debug {
    async fn on_message(&self, agent_id: String, message: Message);
}

#[async_trait::async_trait]
pub trait Processor: Send + Sync + Debug {
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
}