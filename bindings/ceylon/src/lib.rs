/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

fn cprint(val: String) {
    info!("{}", val);
}

fn enable_log(level: String) {
    let subscriber = tracing_subscriber::FmtSubscriber::builder()
        .with_level(true)
        .with_max_level(Level::from_str(&level).unwrap())
        .finish();

    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
}

use ceylon_core::{
    AdminAgent, AdminAgentConfig, AgentDetail, EventHandler, MessageHandler, PeerMode, Processor,
    UnifiedAgent, UnifiedAgentConfig, WorkerAgent, WorkerAgentConfig,
};
use std::str::FromStr;
use tracing::{info, Level};
uniffi::include_scaffolding!("ceylon");
