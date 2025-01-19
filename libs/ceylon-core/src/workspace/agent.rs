/*
 * Copyright (c) 2023-2025 SYIGEN LTD.
 * Author: Dewmal - dewmal@syigen.com
 * Created: 2025-01-19
 * Ceylon Project - https://github.com/ceylonai/ceylon
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * This file is part of Ceylon Project.
 * Original authors: Dewmal - dewmal@syigen.com
 * For questions and support: https://github.com/ceylonai/ceylon/issues
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