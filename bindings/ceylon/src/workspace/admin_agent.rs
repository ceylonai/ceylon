use std::alloc::System;
use futures::future::join_all;
use std::collections::HashMap;
use std::sync::{Arc};
use std::time::SystemTime;
use tokio::runtime::Runtime;
use tokio::sync::{Mutex, RwLock};
use tokio::{select, signal};
use tracing::{error, info};

use crate::workspace::agent::{AgentDetail, EventHandler};
use crate::workspace::message::AgentMessage;
use crate::{MessageHandler, Processor, WorkerAgent};
use sangedama::peer::message::data::{EventType, NodeMessage};
use sangedama::peer::node::{
    create_key, create_key_from_bytes, get_peer_id, AdminPeer, AdminPeerConfig,
};

#[derive(Clone)]
pub struct AdminAgentConfig {
    pub name: String,
    pub port: u16,
}

pub struct AdminAgent {
    pub config: AdminAgentConfig,

    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    _on_event: Arc<Mutex<Arc<dyn EventHandler>>>,

    pub broadcast_emitter: tokio::sync::mpsc::Sender<Vec<u8>>,
    pub broadcast_receiver: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,

    runtime: Runtime,
    _peer_id: String,

    _key: Vec<u8>,
}

impl AdminAgent {
    pub fn new(
        config: AdminAgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Arc<dyn Processor>,
        on_event: Arc<dyn EventHandler>,
    ) -> Self {
        let (broadcast_emitter, broadcast_receiver) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();
        let admin_peer_key = create_key();
        let id = get_peer_id(&admin_peer_key).to_string();

        Self {
            config,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            _on_event: Arc::new(Mutex::new(on_event)),

            broadcast_emitter,
            broadcast_receiver: Arc::new(Mutex::new(broadcast_receiver)),

            runtime: rt,

            _peer_id: id,

            _key: admin_peer_key.to_protobuf_encoding().unwrap(),
        }
    }

    pub async fn broadcast(&self, message: Vec<u8>) {
        let id = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos() as u64;
        let node_message = AgentMessage::NodeMessage { message, id };
        match self.broadcast_emitter.send(node_message.to_bytes()).await {
            Ok(_) => {}
            Err(_) => {
                error!("Failed to send broadcast message");
            }
        }
    }

    pub async fn start(&self, inputs: Vec<u8>, agents: Vec<Arc<WorkerAgent>>) {
        self.run_(inputs, agents).await;
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }

    pub fn details(&self) -> AgentDetail {
        AgentDetail {
            name: self.config.name.clone(),
            id: self._peer_id.clone(),
            role: "admin".to_string(),
        }
    }
    async fn run_(&self, inputs: Vec<u8>, agents: Vec<Arc<WorkerAgent>>) {
        info!("Agent {} running", self.config.name);

        let worker_details: RwLock<HashMap<String, AgentDetail>> = RwLock::new(HashMap::new());

        let config = self.config.clone();
        let admin_config = AdminPeerConfig::new(config.port, config.name.clone());

        let peer_key = create_key_from_bytes(self._key.clone());

        let (mut peer_, mut peer_listener_) =
            AdminPeer::create(admin_config.clone(), peer_key).await;

        if peer_.id == self._peer_id {
            info!("Admin peer created {}", peer_.id.clone());
        } else {
            panic!("Id mismatch");
        }
        let admin_id = peer_.id.clone();
        let admin_emitter = peer_.emitter();

        let mut is_request_to_shutdown = false;

        let task_admin = self.runtime.spawn(async move {
            peer_.run(None).await;
        });


        let mut worker_tasks = vec![];

        let _inputs = inputs.clone();
        let admin_id_ = admin_id.clone();
        for agent in agents {
            let _inputs_ = _inputs.clone();
            let agent_ = agent.clone();
            let _admin_id_ = admin_id_.clone();
            let mut config = agent_.config.clone();
            config.admin_peer = _admin_id_.clone();
            let tasks = agent_
                .run_with_config(_inputs_.clone(), config, self.runtime.handle())
                .await;
            let agent_detail = agent_.details();

            worker_details
                .write()
                .await
                .insert(agent_detail.id.clone(), agent_detail);

            for task in tasks {
                worker_tasks.push(task);
            }
        }

        error!("Worker tasks created");

        let worker_tasks = join_all(worker_tasks);


        let name = self.config.name.clone();
        let on_message = self._on_message.clone();
        let on_event = self._on_event.clone();
        let task_admin_listener = self.runtime.spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                select! {
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
                                NodeMessage::Event {
                                    event,
                                    ..
                                }=>{
                                   match event{
                                        EventType::Subscribe{
                                            peer_id,
                                            topic,
                                        }=>{
                                            if let Some(agent) = worker_details.read().await.get(&peer_id) {
                                                let agent = agent.clone();
                                                 on_event.lock().await.on_agent_connected(topic,agent)
                                                .await;
                                            }
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
        let processor_input_clone = inputs.clone();
        let run_process = self.runtime.spawn(async move {
            processor.lock().await.run(processor_input_clone).await;
            loop {
                if is_request_to_shutdown {
                    break;
                }
            }
        });

        let broadcast_receiver = self.broadcast_receiver.clone();
        let run_broadcast = self.runtime.spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                if let Some(raw_data) = broadcast_receiver.lock().await.recv().await {
                    info!("Agent broadcast {:?}", raw_data);
                    admin_emitter.send(raw_data).await.unwrap();
                }
            }
        });


        self.runtime
            .spawn(async move {
                select! {
                   _ = worker_tasks => {
                        info!("Agent {} task_admin_listener done", name);
                    }
                    _ = task_admin => {
                        info!("Agent {} task_admin done", name);
                    }
                    _ = task_admin_listener => {
                        info!("Agent {} task_admin_listener done", name);
                    }
                    _ = run_process => {
                        info!("Agent {} run_process done", name);
                    }
                    _ = run_broadcast => {
                        info!("Agent {} run_broadcast done", name);
                    }
                    _ = signal::ctrl_c() => {
                        println!("Agent {:?} received exit signal", name);
                        // Perform any necessary cleanup here
                        is_request_to_shutdown = true;
                    }
                }
            })
            .await
            .unwrap();

        loop {
            if is_request_to_shutdown {
                break;
            }
        }
    }
}
