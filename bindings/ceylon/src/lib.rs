mod agent;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use agent::{
    agent_base::{
        AgentDefinition,
        AgentConfig,
        MessageHandler,
        EventHandler,
        Processor,
        AgentHandler
    },
    agent_impl::{
        AgentCore
    },
    workspace::{
        Workspace,
        WorkspaceConfig,
        agent_runner_multi_thread,
        agent_run_single
    },
};

pub use sangedama::node::node::{
    Message,
    MessageType,
    EventType,
};

uniffi::include_scaffolding!("ceylon");