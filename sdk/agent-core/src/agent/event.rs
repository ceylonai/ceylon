/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */
// src/agent/event.rs

use agent_communication::protocol::anp::AnpMessage;
use crate::agent::task::Task;

#[derive(Debug)]
pub enum AgentEvent {
    SendANPMessage(AnpMessage),
    ReceivedANPMessage(AnpMessage),
    ExecuteTask(Task),
    Shutdown,
}
