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

use crate::workspace::agent::{
    AgentDetail, ENV_WORKSPACE_ID, ENV_WORKSPACE_IP, ENV_WORKSPACE_PEER, ENV_WORKSPACE_PORT,
};
use crate::workspace::message::{AgentMessage, MessageType};
use crate::{EventHandler, MessageHandler, Processor};
use futures::future::join_all;
use sangedama::peer::message::data::{EventType, NodeMessage, NodeMessageTransporter};
use sangedama::peer::node::{
    create_key, create_key_from_bytes, get_peer_id, MemberPeer, MemberPeerConfig,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::sync::Arc;
use tokio::runtime::Handle;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;
use tokio::{select, signal};
use tokio_util::sync::CancellationToken;
use tracing::{error, info};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerAgentConfig {
    pub name: String,
    pub role: String,
    pub conf_file: Option<String>,
    pub work_space_id: String,
    pub admin_peer: String,
    pub admin_port: u16,
    pub admin_ip: String,
    pub buffer_size: u16,
}

impl WorkerAgentConfig {
    pub fn update_admin_config(&mut self, config_path: String) {
        let config_content = fs::read_to_string(config_path).unwrap();
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

        self.work_space_id = config.get(ENV_WORKSPACE_ID).cloned().unwrap_or_default();
        self.admin_peer = config.get(ENV_WORKSPACE_PEER).cloned().unwrap_or_default();
        self.admin_port = config
            .get(ENV_WORKSPACE_PORT)
            .and_then(|s| s.parse().ok())
            .unwrap_or_default();
        self.admin_ip = config.get(ENV_WORKSPACE_IP).cloned().unwrap_or_default();
    }

    fn to_str(&self) -> String {
        format!(
            "name: {}, role: {}, work_space_id: {}, admin_peer: {}, admin_port: {}, admin_ip: {}, config_file {:?} ",
            self.name, self.role, self.work_space_id, self.admin_peer, self.admin_port, self.admin_ip, self.conf_file
        )
    }
}

pub struct WorkerAgent {
    pub config: WorkerAgentConfig,

    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    _on_event: Arc<Mutex<Arc<dyn EventHandler>>>,

    pub broadcast_emitter: tokio::sync::mpsc::Sender<NodeMessageTransporter>,
    pub broadcast_receiver: Arc<Mutex<tokio::sync::mpsc::Receiver<NodeMessageTransporter>>>,

    _peer_id: String,
    _key: Vec<u8>,
}

impl WorkerAgent {
    pub fn new(
        config: WorkerAgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Arc<dyn Processor>,
        on_event: Arc<dyn EventHandler>,
    ) -> Self {
        let (broadcast_emitter, broadcast_receiver) =
            tokio::sync::mpsc::channel::<NodeMessageTransporter>(2);
        let admin_peer_key = create_key();
        let id = get_peer_id(&admin_peer_key).to_string();

        let mut config = config.clone();
        info!("Config: {}", config.to_str());
        if config.conf_file.is_some() {
            let conf_file = config.clone().conf_file.unwrap().clone().to_string();
            info!(
                "Checking .ceylon_network config {}",
                fs::metadata(conf_file.clone()).is_ok()
            );
            // check .ceylon_network exists
            if fs::metadata(conf_file.clone()).is_ok() {
                config.update_admin_config(conf_file.clone());
                info!("--------------------------------");
                info!("Using .ceylon_network config");
                info!("{} = {}", ENV_WORKSPACE_ID, config.work_space_id);
                info!("{} = {}", ENV_WORKSPACE_PEER, config.admin_peer);
                info!("{} = {}", ENV_WORKSPACE_PORT, config.admin_port);
                info!("{} = {}", ENV_WORKSPACE_IP, config.admin_ip);
                info!("--------------------------------");
            }
        }

        Self {
            config,
            _processor: Arc::new(Mutex::new(processor)),
            _on_message: Arc::new(Mutex::new(on_message)),
            _on_event: Arc::new(Mutex::new(on_event)),

            broadcast_emitter,
            broadcast_receiver: Arc::new(Mutex::new(broadcast_receiver)),

            _peer_id: id,
            _key: admin_peer_key.to_protobuf_encoding().unwrap(),
        }
    }
    pub async fn start(&self, _inputs: Vec<u8>) {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        let _inputs_ = _inputs.clone();
        let config = self.config.clone();

        let handle = runtime.handle().clone();
        let cancel_token = CancellationToken::new();
        let cancel_token_clone = cancel_token.clone();

        let tasks = self
            .run_with_config(
                _inputs_.clone(),
                config,
                handle.clone(),
                cancel_token_clone.clone(),
            )
            .await;

        let task_runner = join_all(tasks);

        let name = self.config.name.clone();
        select! {
           _ = task_runner => {
                info!("Agent {} task_runner done ", name);
            }
            _ = signal::ctrl_c() => {
                println!("Agent {:?} received exit signal", name);
                cancel_token_clone.cancel();
            }
        }
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }

    pub fn details(&self) -> AgentDetail {
        AgentDetail {
            name: self.config.name.clone(),
            id: self._peer_id.clone(),
            role: self.config.role.clone(),
        }
    }
}

impl WorkerAgent {
    pub async fn send_direct(&self, to_peer: String, message: Vec<u8>) {
        let node_message = AgentMessage::create_direct_message(message, to_peer.clone());
        info!("Sending direct message to {}", to_peer.clone());
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
    pub async fn run_with_config(
        &self,
        inputs: Vec<u8>,
        worker_agent_config: WorkerAgentConfig,
        runtime: Handle,
        cancellation_token: CancellationToken,
    ) -> Vec<JoinHandle<()>> {
        info!("Agent {} running", self.config.name);

        let config = worker_agent_config.clone();

        info!("Config {:?}", config.to_str());

        let member_config = MemberPeerConfig::new(
            config.name.clone(),
            config.work_space_id.clone(),
            config.admin_peer.clone(),
            config.admin_port,
            config.admin_ip,
            Some(config.buffer_size as usize),
        );
        let peer_key = create_key_from_bytes(self._key.clone());
        let (mut peer_, mut peer_listener_) =
            MemberPeer::create(member_config.clone(), peer_key).await;
        if peer_.id == self._peer_id {
            info!("Worker peer created {}", peer_.id.clone());
        } else {
            panic!("Id mismatch");
        }
        let peer_emitter = peer_.emitter();

        let is_request_to_shutdown = false;
        let cancellation_token_clone = cancellation_token.clone();
        let task_admin = runtime.spawn(async move {
            peer_.run(cancellation_token_clone).await;
        });

        let on_message = self._on_message.clone();
        let cancellation_token_clone = cancellation_token.clone();
        let peer_emitter_clone = peer_emitter.clone();

        let agent_details = self.details().clone();

        let on_event = self._on_event.clone();
        let peer_id = self._peer_id.clone();
        let task_admin_listener = runtime.spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                select! {
                    _ = cancellation_token_clone.cancelled() => {
                        break;
                    }
                   event = peer_listener_.recv() => {
                        if let Some(event) = event {
                            match event {
                                NodeMessage::Message{ data, created_by, time,..} => {
                                   let agent_message = AgentMessage::from_bytes(data);

                                    match agent_message {
                                        AgentMessage::NodeMessage { message,message_type,.. } => {
                                             match message_type {
                                                MessageType::Direct { to_peer } => {
                                                    // Only process if we're the intended recipient
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
                                            let agent_detail = AgentDetail{
                                                name,
                                                id,
                                                role
                                            };
                                            on_event.lock().await.on_agent_connected(
                                                topic,
                                                agent_detail
                                            ).await;
                                        }
                                        _ => {
                                            info!("Agent listener {:?}", agent_message);
                                        }
                                    }
                                }
                                NodeMessage::Event {
                                    event,
                                    ..
                                }=>{
                                   match event{
                                        EventType::Subscribe{
                                            topic,
                                            ..
                                        }=>{
                                            info!("Worker {} Subscribed to topic {:?}", agent_details.id, topic);
                                            let agent_intro_message = AgentMessage::AgentIntroduction {
                                                id: agent_details.id.clone(),
                                                name: agent_details.name.clone(),
                                                role:agent_details.role.clone(),
                                                topic,
                                            };
                                            peer_emitter_clone.send(
                                                (agent_details.id.clone(),agent_intro_message.to_bytes(),None)
                                            ).await.unwrap();
                                        }
                                        _ => {
                                            info!("Admin Received Event {:?}", event);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let run_process = runtime.spawn(async move {
            processor.lock().await.run(inputs).await;
        });

        let broadcast_receiver = self.broadcast_receiver.clone();
        let cancellation_token_clone = cancellation_token.clone();
        let agent_details = self.details().clone();
        let run_broadcast = runtime.spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }

                if cancellation_token_clone.is_cancelled() {
                    break;
                } else if let Some(raw_data) = broadcast_receiver.lock().await.recv().await {
                    peer_emitter
                        .send(raw_data)
                        .await
                        .unwrap();
                }
            }
        });

        vec![task_admin, task_admin_listener, run_process, run_broadcast]
    }
}
