/*
 *
 *  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 *  * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *  *
 *
 */
// src/agent/communication.rs

use anyhow::Result;
use serde_json::Value;
use tokio::sync::mpsc::Sender;
use tokio::task::JoinHandle;

// Import from agent-communication crate
use agent_communication::{PeerId, anp::AnpMessage, data::AgentConfig, handlers::handle_message, messaging::ANP_PROTOCOL, node::run_node, peer_builder::AgentNodeBuilder, Multiaddr};

use crate::agent::event::AgentEvent;

pub struct CommunicationModule {
    tx: Sender<AgentEvent>,
    config: AgentConfig,
    node_handle: Option<JoinHandle<Result<()>>>,
}

impl CommunicationModule {
    pub fn new(tx: Sender<AgentEvent>) -> Self {
        // Create default configuration using the existing builder
        let config = AgentNodeBuilder::new()
            .with_listen_addr("/ip4/0.0.0.0/tcp/0")
            .with_protocol(ANP_PROTOCOL)
            .build();

        Self {
            tx,
            config,
            node_handle: None,
        }
    }

    pub fn with_config(tx: Sender<AgentEvent>, config: AgentConfig) -> Self {
        Self {
            tx,
            config,
            node_handle: None,
        }
    }

    pub async fn start(&mut self) -> Result<()> {
        println!("🚀 Starting communication module...");

        // Just use the existing run_node function
        let handle = tokio::spawn(async move { run_node().await });

        self.node_handle = Some(handle);
        println!("✅ Communication module started");
        Ok(())
    }

    pub async fn stop(&mut self) {
        println!("🛑 Stopping communication module...");

        if let Some(handle) = self.node_handle.take() {
            handle.abort();
            println!("✅ Communication module stopped");
        }
    }

    pub async fn handle_incoming(&self, msg: AnpMessage) {
        println!("📨 Handling incoming ANP message: {:?}", msg);

        // Use the existing handler
        handle_message(msg.clone()).await;

        // Forward to agent event system
        let _ = self.tx.send(AgentEvent::ReceivedANPMessage(msg)).await;
    }

    pub async fn send_message(&self, to: PeerId, action: String, data: Value) -> Result<()> {
        // Create ANP message using existing structure
        let anp_msg = AnpMessage::new(
            self.config.peer_id.to_string(),
            to.to_string(),
            serde_json::json!({
                "action": action,
                "data": data
            }),
            "".to_string(), // Signature handled by existing code
        );

        // Send via event channel
        self.tx
            .send(AgentEvent::SendANPMessage {
                0: anp_msg,
            })
            .await
            .map_err(|e| anyhow::anyhow!("Failed to send message: {}", e))?;

        Ok(())
    }

    pub fn get_peer_id(&self) -> PeerId {
        self.config.peer_id
    }

    pub fn get_listen_addresses(&self) -> &[Multiaddr] {
        &self.config.listen_addrs
    }
}

impl Drop for CommunicationModule {
    fn drop(&mut self) {
        if let Some(handle) = self.node_handle.take() {
            handle.abort();
        }
    }
}

// Helper function to create a communication module with custom configuration
pub fn create_communication_module(
    tx: Sender<AgentEvent>,
    listen_addrs: Vec<&str>,
    protocol: Option<&str>,
) -> CommunicationModule {
    let mut builder = AgentNodeBuilder::new();

    for addr in listen_addrs {
        builder = builder.with_listen_addr(addr);
    }

    if let Some(proto) = protocol {
        builder = builder.with_protocol(proto);
    }

    let config = builder.build();
    CommunicationModule::with_config(tx, config)
}
