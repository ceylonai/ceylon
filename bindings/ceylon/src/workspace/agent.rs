use std::fmt::Debug;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDetail {
    pub name: String,
    pub id: String,
    pub role: String,
}

#[async_trait::async_trait]
pub trait AgentBase {
    async fn run_(&self, inputs: Vec<u8>);
}

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync + Debug {
    async fn on_message(&self, agent_id: String, data: Vec<u8>, time: u64);
}

#[async_trait::async_trait]
pub trait Processor: Send + Sync + Debug {
    async fn run(&self, input: Vec<u8>) -> ();
}

#[async_trait::async_trait]
pub trait EventHandler: Send + Sync + Debug {
    async fn on_agent_connected(&self, topic: String, agent: AgentDetail) -> ();
}
