mod agent;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use agent::{
    agent_base::{
        AgentDefinition,
        AgentConfig,
        MessageHandler,
        Processor,
    },
    agent_impl::{
        AgentCore
    },
    workspace::{
        Workspace,
        WorkspaceConfig,
    },
};

pub use sangedama::node::node::{
    Message,
    MessageType,
    EventType,
};

uniffi::include_scaffolding!("ceylon");