mod agent;
mod workspace;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

fn enable_log(level :String) {
    let subscriber = tracing_subscriber::FmtSubscriber::builder()
        .with_level(true)
        .with_max_level(Level::from_str(&level).unwrap())
        .finish();

    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
}

use std::str::FromStr;
use tracing::Level;
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