mod agent;

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

pub use agent::{agent::{
    Agent,
    run_workspace,
}};

uniffi::include_scaffolding!("ceylon");