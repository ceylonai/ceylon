mod agent;
mod workspace;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use workspace::*;

// pub use agent::{
//     agent_base::{
//         MessageHandler,
//         Processor,
//         AgentDefinition,
//     },
//     agent::{
//         AgentCore
//     },
//     state::{
//         Message
//     },
//     workspace::{
//         Workspace,
//         WorkspaceConfig,
//     },
// };

uniffi::include_scaffolding!("ceylon");