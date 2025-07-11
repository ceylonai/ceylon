/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */
// src/main.rs

mod agent;

use agent::{
    communication::{AnpMessage, CommunicationModule},
    core_engine::CoreEngine,
    task::TaskExecutor,
};
use tokio::sync::mpsc;

#[tokio::main]
async fn main() {
    let (tx, rx) = mpsc::channel(100);

    let comms = CommunicationModule::new(tx.clone());
    let task_executor = TaskExecutor::new();
    let core_engine = CoreEngine::new(rx, task_executor);

    // Start communication (libp2p setup, etc.)
    tokio::spawn(async move {
        comms.start().await;
        // Simulate receiving a message
        let msg = AnpMessage {
            version: "1.0".into(),
            action: "executeTask".into(),
            data: "Hello from ANP".into(),
        };
        comms.handle_incoming(msg).await;
    });

    // Start core event loop
    core_engine.start_event_loop().await;
}
