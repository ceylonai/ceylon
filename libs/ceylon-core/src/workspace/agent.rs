/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

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

pub static ENV_WORKSPACE_ID: &str = "WORKSPACE_ID";
pub static ENV_WORKSPACE_PEER: &str = "WORKSPACE_PEER";
pub static ENV_WORKSPACE_PORT: &str = "WORKSPACE_PORT";
pub static ENV_WORKSPACE_IP: &str = "WORKSPACE_IP";