use std::sync::Arc;
use tokio::{select, signal};
use tracing::info;

use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{AdminPeer, AdminPeerConfig};

use crate::WorkerAgent;

#[derive(Clone)]
pub struct AdminAgentConfig {
    pub name: String,
    pub port: u16,
}

pub struct AdminAgent {
    pub config: AdminAgentConfig,
}

impl AdminAgent {
    pub fn new(config: AdminAgentConfig) -> Self {
        Self { config }
    }

    pub async fn run(&self, inputs: Vec<u8>, agents: Vec<Arc<WorkerAgent>>) {
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

        let admin_id = peer_.id.clone();
        let admin_emitter = peer_.emitter();

        let mut is_request_to_shutdown = false;

        let task_admin = tokio::task::spawn(async move {
            peer_.run(None).await;
        });

        let name = self.config.name.clone();
        let task_admin_listener = tokio::spawn(async move {
            loop {
                if is_request_to_shutdown {
                    break;
                }
                select! {
                   event = peer_listener_.recv() => {
                        if let Some(event) = event {
                            match event {
                                NodeMessage::Message{ data, created_by, ..} => {
                                    info!("Agent listener Message {:?} from {:?}", String::from_utf8(data), created_by);
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
            _ = signal::ctrl_c() => {
                println!("Agent {:?} received exit signal", name);
                // Perform any necessary cleanup here
                is_request_to_shutdown = true;
            }
        }
    }
}