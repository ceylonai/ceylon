/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use crate::workspace::agent::{
    AgentDetail, ENV_WORKSPACE_ID, ENV_WORKSPACE_IP, ENV_WORKSPACE_PEER, ENV_WORKSPACE_PORT,
};
use crate::workspace::agent::{EventHandler, MessageHandler, Processor};
use crate::workspace::message::{AgentMessage, MessageType};
use crate::WorkerAgent;
use futures::future::join_all;
use log::log_enabled;
use sangedama::peer::message::data::{NodeMessage, NodeMessageTransporter};
use sangedama::peer::node::node::{UnifiedPeerConfig, UnifiedPeerImpl};
use sangedama::peer::node::peer_builder::{create_key, create_key_from_bytes, get_peer_id};
use sangedama::peer::PeerMode;
use std::collections::HashMap;
use std::fs;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;
use tokio::{select, signal};
use tokio_util::sync::CancellationToken;
use tracing::{error, info};

#[derive(Clone, Default, Debug)]
pub struct UnifiedAgentConfig {
    pub name: String,
    pub mode: PeerMode,
    pub role: Option<String>,
    pub work_space_id: Option<String>,
    pub port: Option<u16>,
    pub admin_peer: Option<String>,
    pub admin_ip: Option<String>,
    pub buffer_size: Option<u16>,
}

impl UnifiedAgentConfig {
    fn to_str(&self) -> String {
        format!(
            "name: {}, role: {:?}, work_space_id: {:?}, admin_peer: {:?}, admin_port: {:?}, admin_ip: {:?}, config_file {:?} ",
            self.name, self.role, self.work_space_id, self.admin_peer, self.port, self.admin_ip, self.buffer_size
        )
    }
}

impl UnifiedAgentConfig {
    pub fn update_from_file(&mut self, config_path: String) -> Result<(), std::io::Error> {
        let config_content = fs::read_to_string(config_path)?;
        let config: HashMap<String, String> = config_content
            .lines()
            .filter_map(|line| {
                let parts: Vec<&str> = line.splitn(2, '=').collect();
                if parts.len() == 2 {
                    Some((parts[0].to_string(), parts[1].to_string()))
                } else {
                    None
                }
            })
            .collect();

        if let Some(workspace_id) = config.get(ENV_WORKSPACE_ID) {
            self.work_space_id = Some(workspace_id.clone());
        }
        if let Some(admin_peer) = config.get(ENV_WORKSPACE_PEER) {
            self.admin_peer = Some(admin_peer.clone());
        }
        if let Some(port) = config.get(ENV_WORKSPACE_PORT) {
            self.port = port.parse().ok();
        }
        if let Some(ip) = config.get(ENV_WORKSPACE_IP) {
            self.admin_ip = Some(ip.clone());
        }

        Ok(())
    }

    pub fn write_to_file(&self, config_path: String) -> Result<(), std::io::Error> {
        let mut config = HashMap::new();
        config.insert(ENV_WORKSPACE_ID.to_string(), self.work_space_id.clone());
        config.insert(
            ENV_WORKSPACE_PEER.to_string(),
            Option::from(self.admin_peer.clone().unwrap()),
        );
        config.insert(
            ENV_WORKSPACE_PORT.to_string(),
            Option::from(self.port.unwrap().to_string()),
        );
        config.insert(
            ENV_WORKSPACE_IP.to_string(),
            Option::from(self.admin_ip.clone().unwrap_or("127.0.0.1".to_string())),
        );
        let config_content = config
            .iter()
            .map(|(k, v)| format!("{}={}", k, v.clone().unwrap()))
            .collect::<Vec<String>>()
            .join("\n");
        fs::write(config_path, config_content)
    }

    pub fn copy_with(&mut self, _conf: UnifiedAgentConfig) {
        self.name = _conf.name.clone();
        self.mode = _conf.mode;
        self.role = _conf.role.clone();
        self.work_space_id = _conf.work_space_id.clone();
        self.port = _conf.port.clone();
        self.admin_peer = _conf.admin_peer.clone();
        self.admin_ip = _conf.admin_ip.clone();
        self.buffer_size = _conf.buffer_size.clone();
    }
}

pub struct UnifiedAgent {
    _config: UnifiedAgentConfig,
    _config_path: Option<String>,
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
        config: Option<UnifiedAgentConfig>,
        config_path: Option<String>,
        on_message: Arc<dyn MessageHandler>,
        processor: Arc<dyn Processor>,
        on_event: Arc<dyn EventHandler>,
    ) -> Self {
        let (broadcast_emitter, broadcast_receiver) = mpsc::channel(2);
        let admin_peer_key = create_key();
        let id = get_peer_id(&admin_peer_key).to_string();

        let (shutdown_send, shutdown_recv) = mpsc::unbounded_channel();

        let mut _config = UnifiedAgentConfig::default();

        let conf = config.clone();
        if let Some(_conf) = conf {
            _config.copy_with(_conf);
        }

        if _config.mode == PeerMode::Admin {
            _config.admin_peer = Some(id.clone());
            _config
                .write_to_file(".ceylon_network".to_string())
                .expect("Failed to write config");
        }

        Self {
            _config,
            _config_path: if config_path.is_some() {
                Some(config_path.unwrap())
            } else {
                Some("./.ceylon_network".to_string())
            },
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
            name: self._config.name.clone(),
            id: self._peer_id.clone(),
            role: self._config.role.clone().unwrap_or("".to_string()),
        }
    }

    pub async fn start(&self, inputs: Vec<u8>, agents: Option<Vec<Arc<UnifiedAgent>>>) {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        let cancel_token = CancellationToken::new();
        let cancel_token_clone = cancel_token.clone();

        // Get all task handlers but don't await them yet
        let mut self_agent_handlers = self
            .run(inputs.clone(), Some(vec![]), cancel_token.clone())
            .await;

        if agents.is_some() {
            let agents = agents.unwrap();
            for agent in agents {
                let mut agent_handler = agent.run(inputs.clone(), None, cancel_token.clone()).await;
                self_agent_handlers.append(&mut agent_handler);
            }
        }

        // Create a single future that completes when all tasks are done
        let all_tasks = async move {
            join_all(self_agent_handlers).await;
        };

        // Use select to handle either ctrl-c or task completion
        runtime.block_on(async {
            select! {
                _ = all_tasks => {
                    info!("All agent tasks completed normally");
                }
                // _ = signal::ctrl_c() => {
                //     info!("Received ctrl-c, initiating shutdown");
                //     cancel_token_clone.cancel();
                // }
            }
        })
    }

    pub async fn run(
        &self,
        inputs: Vec<u8>,
        agents: Option<Vec<Arc<UnifiedAgent>>>,
        cancel_token: CancellationToken,
    ) -> Vec<JoinHandle<()>> {
        let mut config = self._config.clone();
        let config_path = self._config_path.clone();
        info!("Config: {}", config.to_str());
        if config_path.is_some() {
            let conf_file = config_path.unwrap().clone();
            info!(
                "Checking .ceylon_network config {}",
                fs::metadata(conf_file.clone()).is_ok()
            );
            // check .ceylon_network exists
            if fs::metadata(conf_file.clone()).is_ok() {
                config.update_from_file(conf_file.clone());
                info!("--------------------------------");
                info!("Using .ceylon_network config");
                info!("{} = {:?}", ENV_WORKSPACE_ID, config.work_space_id);
                info!("{} = {:?}", ENV_WORKSPACE_PEER, config.admin_peer);
                info!("{} = {:?}", ENV_WORKSPACE_PORT, config.port);
                info!("{} = {:?}", ENV_WORKSPACE_IP, config.admin_ip);
                info!("--------------------------------");
            }
        }

        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        let handle = runtime.handle().clone();
        let peer_config = match self._config.mode {
            PeerMode::Admin => UnifiedPeerConfig::new_admin(
                config
                    .work_space_id
                    .clone()
                    .unwrap_or("CEYLON-AI-AGENT-NETWORK".to_string()),
                config.port.unwrap_or(0),
                config.buffer_size,
            ),
            PeerMode::Client => UnifiedPeerConfig::new_member(
                config.name.clone(),
                config
                    .work_space_id
                    .clone()
                    .unwrap_or("CEYLON-AI-AGENT-NETWORK".to_string()),
                config.admin_peer.clone().unwrap(),
                config.port.unwrap_or(0),
                config.admin_ip.clone().unwrap_or_default(),
                config.buffer_size,
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
            select! {
                _ = peer.run(cancel_token_clone.clone()) => {
                    info!("Peer run completed");
                }
                _ = cancel_token_clone.cancelled() => {
                    info!("Peer run cancelled");
                }
            }
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
                        info!("Peer listener shutting down");
                        break;
                    }
                    event = peer_listener.recv() => {
                        if let Some(event) = event {
                             if cancel_token_clone.is_cancelled() {
                                break;
                            }
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

        let cancel_token_clone = cancel_token.clone();
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

        let tasks = handle.spawn(async move {
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
        });

        vec![tasks]
    }

    async fn cleanup(&self) {
        // Release any resources that need explicit cleanup
        info!("Cleaning up agent resources");
        // Close channels
        drop(self.broadcast_emitter.clone());
        // Any other cleanup...
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self._config.name);
        self.shutdown_send.send(self._peer_id.clone()).unwrap();
        self.cleanup().await;
    }
}
