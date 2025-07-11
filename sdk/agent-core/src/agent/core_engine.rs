/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */
// src/agent/core_engine.rs

use crate::agent::{
    event::AgentEvent,
    task::{Task, TaskExecutor},
};
use tokio::sync::mpsc::{Receiver, Sender};
use agent_communication::anp::AnpMessage;

pub struct CoreEngine {
    rx: Receiver<AgentEvent>,
    task_executor: TaskExecutor,
}

impl CoreEngine {
    pub fn new(rx: Receiver<AgentEvent>, task_executor: TaskExecutor) -> Self {
        Self { rx, task_executor }
    }

    pub async fn start_event_loop(mut self) {
        println!("Starting CoreEngine event loop...");
        while let Some(event) = self.rx.recv().await {
            match event {
                AgentEvent::ReceivedANPMessage(msg) => {
                    println!("CoreEngine received ANP message: {:?}", msg);
                    if let Some(task) = Self::parse_task_from_anp(msg) {
                        self.task_executor.execute(task).await;
                    }
                }
                AgentEvent::ExecuteTask(task) => {
                    self.task_executor.execute(task).await;
                }
                AgentEvent::Shutdown => {
                    println!("CoreEngine received shutdown signal.");
                    break;
                }

                AgentEvent::SendANPMessage(anp_message) => {
                    println!("CoreEngine received ANP message to send: {:?}", anp_message);
                }
            }
        }
    }

    fn parse_task_from_anp(msg: AnpMessage) -> Option<Task> {
        Some(Task {
            id: msg.version,
            payload: serde_json::to_string(&msg.payload).unwrap(),
        })
    }
}
