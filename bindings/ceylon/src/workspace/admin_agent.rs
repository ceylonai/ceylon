use std::sync::Arc;
use tokio::{select, signal};
use tokio::sync::Mutex;
use tracing::{error, info};

use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{AdminPeer, AdminPeerConfig};
use crate::{MessageHandler, WorkerAgent, Processor};
use crate::agent::state::{Message, SystemMessage};

#[derive(Clone)]
pub struct AdminAgentConfig {
    pub name: String,
    pub port: u16,
}

pub struct AdminAgent {
    pub config: AdminAgentConfig,

    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,

    pub broadcast_emitter: tokio::sync::mpsc::Sender<Vec<u8>>,
    pub broadcast_receiver: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,
}

impl AdminAgent {
    pub fn new(config: AdminAgentConfig, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (broadcast_emitter, broadcast_receiver) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        Self {
            config,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),

            broadcast_emitter,
            broadcast_receiver: Arc::new(Mutex::new(broadcast_receiver)),
        }
    }

    pub async fn broadcast(&self, message: Vec<u8>) {
        match self.broadcast_emitter.send(message).await {
            Ok(_) => {}
            Err(_) => {
                error!("Failed to send broadcast message");
            }
        }
    }

    pub async fn start(&self, inputs: Vec<u8>, agents: Vec<Arc<WorkerAgent>>) {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        rt.block_on(async {
            self.run_(inputs, agents).await;
        });
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }
    async fn run_(&self, inputs: Vec<u8>, agents: Vec<Arc<WorkerAgent>>) {
        info!("Agent {} running", self.config.name);

        let config = self.config.clone();
        let admin_config = AdminPeerConfig::new(config.port, config.name.clone());
        let (mut peer_, mut peer_listener_) = AdminPeer::create(admin_config.clone()).await;


        let admin_emitter = peer_.emitter();


        let admin_id = peer_.id.clone();
        let admin_emitter = peer_.emitter();

        let mut is_request_to_shutdown = false;

        let task_admin = tokio::task::spawn(async move {
            peer_.run(None).await;
        });


        let name = self.config.name.clone();
        let on_message = self._on_message.clone();
        let task_admin_listener = tokio::spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                select! {
                   event = peer_listener_.recv() => {
                        if let Some(event) = event {
                            match event {
                                NodeMessage::Message{ data, created_by, time} => {
                                    on_message.lock().await.on_message(
                                        created_by,
                                        data,
                                        time
                                    ).await;
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
        let processor_input_clone = inputs.clone();
        let name_processor = self.config.name.clone();
        let run_process = tokio::spawn(async move {
            info!("Agent {} run_process", name_processor);
            processor.lock().await.run(processor_input_clone).await;
            info!("Agent {} run_proces edd", name_processor);
        });


        let broadcast_receiver = self.broadcast_receiver.clone();
        let run_broadcast = tokio::spawn(async move {
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


        let mut worker_tasks = vec![];

        let _inputs = inputs.clone();
        let admin_id_ = admin_id.clone();
        for agent in agents {
            let _inputs_ = _inputs.clone();
            let agent_ = agent.clone();
            let _admin_id_ = admin_id_.clone();
            let task = tokio::spawn(async move {
                let mut config = agent_.config.clone();
                config.admin_peer = _admin_id_.clone();
                agent_.run_with_config(_inputs_.clone(), config).await;
            });
            worker_tasks.push(task);
        }

        let mut worker_handler = tokio::task::JoinSet::from_iter(worker_tasks);

        tokio::spawn(async move {
            while let Some(res) = worker_handler.join_next().await {}
        });


        select! {
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
    }
}