mod agent;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use agent::{agent::{
    Agent,
    AgentRunner,
    AgentConnectionError,
    AgentStartError
}};

uniffi::include_scaffolding!("ceylon");