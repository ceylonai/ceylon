use serde::{Deserialize, Serialize};
use std::sync::{Arc};
use std::time::SystemTime;
use tokio::sync::{Mutex};
use tokio::{select};
use tokio::runtime::{Handle};
use tokio::task::JoinHandle;
use tokio_util::sync::CancellationToken;
use tracing::{error, info};

use crate::workspace::agent::AgentDetail;
use crate::workspace::message::AgentMessage;
use crate::{MessageHandler, Processor};
use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{
    create_key, create_key_from_bytes, get_peer_id, MemberPeer, MemberPeerConfig,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerAgentConfig {
    pub name: String,
    pub role: String,
    pub work_space_id: String,
    pub admin_peer: String,
    pub admin_port: u16,
}

pub struct WorkerAgent {
    pub config: WorkerAgentConfig,

    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,

    pub broadcast_emitter: tokio::sync::mpsc::Sender<Vec<u8>>,
    pub broadcast_receiver: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,

    _peer_id: String,
    _key: Vec<u8>,
}

impl WorkerAgent {
    pub fn new(
        config: WorkerAgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Arc<dyn Processor>,
    ) -> Self {
        let (broadcast_emitter, broadcast_receiver) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        let admin_peer_key = create_key();
        let id = get_peer_id(&admin_peer_key).to_string();
        Self {
            config,
            _processor: Arc::new(Mutex::new(processor)),
            _on_message: Arc::new(Mutex::new(on_message)),

            broadcast_emitter,
            broadcast_receiver: Arc::new(Mutex::new(broadcast_receiver)),

            _peer_id: id,
            _key: admin_peer_key.to_protobuf_encoding().unwrap(),
        }
    }
    pub async fn broadcast(&self, message: Vec<u8>) {
        let id = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos();
        let node_message = AgentMessage::NodeMessage { message, id: id as u64 };
        let message = node_message.to_bytes();

        match self.broadcast_emitter.send(message).await {
            Ok(_) => {}
            Err(_) => {
                error!("Failed to send broadcast message");
            }
        }
    }
    pub async fn start(&self, _: Vec<u8>) {
        info!("Not yet implemented");
        // self.run_with_config(inputs, self.config.clone()).await;
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
    pub async fn run_with_config(&self, inputs: Vec<u8>, worker_agent_config: WorkerAgentConfig, runtime: Handle, cancellation_token: CancellationToken) -> Vec<JoinHandle<()>> {
        info!("Agent {} running", self.config.name);

        let config = worker_agent_config.clone();
        let member_config = MemberPeerConfig::new(
            config.name.clone(),
            config.work_space_id.clone(),
            config.admin_peer.clone(),
            config.admin_port,
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
                                NodeMessage::Message{ data, created_by, time} => {
                                   let agent_message = AgentMessage::from_bytes(data);

                                    match agent_message {
                                        AgentMessage::NodeMessage { message,.. } => {
                                            on_message.lock().await.on_message(
                                                created_by,
                                                message,
                                                time
                                            ).await;
                                        }
                                        _ => {
                                            info!("Agent listener {:?}", agent_message);
                                        }
                                    }
                                }
                                _ => {
                                    info!("Agent listener {:?}", event);
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
        let run_broadcast = runtime.spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                if let Some(raw_data) = broadcast_receiver.lock().await.recv().await {
                    peer_emitter.send(raw_data).await.unwrap();
                }
                if cancellation_token_clone.is_cancelled() {
                    break;
                }
            }
        });

        vec![task_admin, task_admin_listener, run_process, run_broadcast]
    }
}
