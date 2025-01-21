/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use crate::workspace::agent::{AgentDetail, EventHandler, MessageHandler, Processor};
use crate::workspace::message::{AgentMessage, MessageType};
use sangedama::peer::message::data::{NodeMessage, NodeMessageTransporter};
use sangedama::peer::node::node::{UnifiedPeerConfig, UnifiedPeerImpl};
use sangedama::peer::node::peer_builder::{create_key, create_key_from_bytes, get_peer_id};
use sangedama::peer::PeerMode;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::select;
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use tokio_util::sync::CancellationToken;
use tracing::{error, info};

#[derive(Clone)]
pub struct UnifiedAgentConfig {
    pub name: String,
    pub role: String,
    pub mode: PeerMode,
    pub work_space_id: String,
    pub port: Option<u16>,
    pub admin_peer: Option<String>,
    pub admin_ip: Option<String>,
    pub buffer_size: Option<usize>,
}

pub struct UnifiedAgent {
    pub config: UnifiedAgentConfig,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    _on_event: Arc<Mutex<Arc<dyn EventHandler>>>,

    pub broadcast_emitter: mpsc::Sender<NodeMessageTransporter>,
    pub broadcast_receiver: Arc<Mutex<mpsc::Receiver<NodeMessageTransporter>>>,

    _peer_id: String,
    _key: Vec<u8>,

    pub shutdown_send: mpsc::UnboundedSender<String>,
    pub shutdown_recv: Arc<Mutex<mpsc::UnboundedReceiver<String>>>,
}

impl UnifiedAgent {
    pub fn new(
        config: UnifiedAgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Arc<dyn Processor>,
        on_event: Arc<dyn EventHandler>,
    ) -> Self {
        let (broadcast_emitter, broadcast_receiver) = mpsc::channel(2);
        let admin_peer_key = create_key();
        let id = get_peer_id(&admin_peer_key).to_string();

        let (shutdown_send, shutdown_recv) = mpsc::unbounded_channel();

        Self {
            config,
            _processor: Arc::new(Mutex::new(processor)),
            _on_message: Arc::new(Mutex::new(on_message)),
            _on_event: Arc::new(Mutex::new(on_event)),

            broadcast_emitter,
            broadcast_receiver: Arc::new(Mutex::new(broadcast_receiver)),

            _peer_id: id,
            _key: admin_peer_key.to_protobuf_encoding().unwrap(),

            shutdown_send,
            shutdown_recv: Arc::new(Mutex::new(shutdown_recv)),
        }
    }

    pub async fn send_direct(&self, to_peer: String, message: Vec<u8>) {
        let node_message = AgentMessage::create_direct_message(message, to_peer.clone());
        info!("Sending direct message to {}", to_peer);
        match self
            .broadcast_emitter
            .send((self.details().id, node_message.to_bytes(), Some(to_peer)))
            .await
        {
            Ok(_) => {}
            Err(e) => {
                error!("Failed to send direct message: {:?}", e);
            }
        }
    }

    pub async fn broadcast(&self, message: Vec<u8>) {
        let node_message = AgentMessage::create_broadcast_message(message);
        match self
            .broadcast_emitter
            .send((self.details().id, node_message.to_bytes(), None))
            .await
        {
            Ok(_) => {}
            Err(e) => {
                error!("Failed to send broadcast message: {:?}", e);
            }
        }
    }

    pub fn details(&self) -> AgentDetail {
        AgentDetail {
            name: self.config.name.clone(),
            id: self._peer_id.clone(),
            role: self.config.role.clone(),
        }
    }

    pub async fn start(&self, inputs: Vec<u8>) {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        let handle = runtime.handle().clone();
        let cancel_token = CancellationToken::new();

        let peer_config = match self.config.mode {
            PeerMode::Admin => UnifiedPeerConfig::new_admin(
                self.config.work_space_id.clone(),
                self.config.port.unwrap_or(0),
                self.config.buffer_size,
            ),
            PeerMode::Client => UnifiedPeerConfig::new_member(
                self.config.name.clone(),
                self.config.work_space_id.clone(),
                self.config.admin_peer.clone().unwrap(),
                self.config.port.unwrap_or(0),
                self.config.admin_ip.clone().unwrap_or_default(),
                self.config.buffer_size,
            ),
        };

        let peer_key = create_key_from_bytes(self._key.clone());
        let (mut peer, mut peer_listener) =
            UnifiedPeerImpl::create(peer_config.clone(), peer_key).await;

        let worker_details: Arc<Mutex<HashMap<String, AgentDetail>>> =
            Arc::new(Mutex::new(HashMap::new()));
        let cancel_token_clone = cancel_token.clone();

        // Spawn peer runner
        let task_peer = handle.spawn(async move {
            peer.run(cancel_token_clone).await;
        });

        let on_message = self._on_message.clone();
        let on_event = self._on_event.clone();
        let peer_id = self._peer_id.clone();
        let cancel_token_clone = cancel_token.clone();

        // Handle peer events
        let task_peer_listener = handle.spawn(async move {
            let mut is_call_agent_on_connect_list: HashMap<String, bool> = HashMap::new();

            loop {
                select! {
                    _ = cancel_token_clone.cancelled() => {
                        break;
                    }
                    event = peer_listener.recv() => {
                        if let Some(event) = event {
                            match event {
                                NodeMessage::Message{ data, created_by, time, message_type } => {
                                    let agent_message = AgentMessage::from_bytes(data);
                                    match agent_message {
                                        AgentMessage::NodeMessage { message, message_type, .. } => {
                                            match message_type {
                                                MessageType::Direct { to_peer } => {
                                                    if to_peer == peer_id {
                                                        on_message.lock().await.on_message(
                                                            created_by,
                                                            message,
                                                            time,
                                                        ).await;
                                                    }
                                                }
                                                MessageType::Broadcast => {
                                                    on_message.lock().await.on_message(
                                                        created_by,
                                                        message,
                                                        time,
                                                    ).await;
                                                }
                                            }
                                        }
                                        AgentMessage::AgentIntroduction { id, name, role, topic } => {
                                            let agent_detail = AgentDetail {
                                                name,
                                                id: id.clone(),
                                                role,
                                            };

                                            worker_details.lock().await.insert(id.clone(), agent_detail.clone());

                                            if !is_call_agent_on_connect_list.get(&id).unwrap_or(&false) {
                                                on_event.lock().await.on_agent_connected(topic, agent_detail).await;
                                                is_call_agent_on_connect_list.insert(id, true);
                                            }
                                        }
                                        _ => {}
                                    }
                                }
                                NodeMessage::Event { event, .. } => {
                                    // Handle events as needed
                                }
                            }
                        }
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let cancel_token_clone = cancel_token.clone();
        let task_processor = handle.spawn(async move {
            processor.lock().await.run(inputs).await;
            loop {
                if cancel_token_clone.is_cancelled() {
                    break;
                }
            }
        });

        let broadcast_receiver = self.broadcast_receiver.clone();
        let cancel_token_clone = cancel_token.clone();
        let task_broadcast = handle.spawn(async move {
            loop {
                if cancel_token_clone.is_cancelled() {
                    break;
                } else if let Some(raw_data) = broadcast_receiver.lock().await.recv().await {
                    // Handle broadcasting
                }
            }
        });

        let shutdown_recv = self.shutdown_recv.clone();
        let admin_id = self._peer_id.clone();
        let task_shutdown = handle.spawn(async move {
            loop {
                if let Some(raw_data) = shutdown_recv.lock().await.recv().await {
                    if raw_data == admin_id {
                        info!("Received shutdown signal");
                        cancel_token.cancel();
                        break;
                    }
                }
            }
        });

        select! {
            _ = task_peer => {
                info!("Peer task completed");
            }
            _ = task_peer_listener => {
                info!("Peer listener task completed");
            }
            _ = task_processor => {
                info!("Processor task completed");
            }
            _ = task_broadcast => {
                info!("Broadcast task completed");
            }
            _ = task_shutdown => {
                info!("Shutdown task completed");
            }
        }
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
        self.shutdown_send.send(self._peer_id.clone()).unwrap();
    }
}
