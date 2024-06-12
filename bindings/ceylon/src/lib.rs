mod agent;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use agent::{
    agent::{
        AgentCore,
        MessageHandler,
        Processor,
    },
    workspace::{
        Workspace,
        WorkspaceConfig,
    },
};

pub use sangedama::node::node::{
    Message,
    MessageType,
};

uniffi::include_scaffolding!("ceylon");