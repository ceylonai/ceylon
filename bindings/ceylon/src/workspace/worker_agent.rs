use serde::{Deserialize, Serialize};
use tokio::{select, signal};
use tracing::info;

use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{MemberPeer, MemberPeerConfig};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerAgentConfig {
    pub name: String,
    pub work_space_id: String,
    pub admin_peer: String,
    pub admin_port: u16,
}


pub struct WorkerAgent {
    pub config: WorkerAgentConfig,
}

impl WorkerAgent {
    pub fn new(config: WorkerAgentConfig) -> Self {
        Self { config }
    }

    pub async fn run(&self, inputs: Vec<u8>) {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        rt.block_on(async {
            self.run_with_config(inputs, self.config.clone()).await;
        });
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }
}

impl WorkerAgent {
    pub async fn run_with_config(&self, inputs: Vec<u8>, worker_agent_config: WorkerAgentConfig) {
        info!("Agent {} running", self.config.name);

        let config = worker_agent_config.clone();
        let member_config = MemberPeerConfig::new(
            config.name.clone(),
            config.work_space_id.clone(),
            config.admin_peer.clone(),
            config.admin_port,
        );
        let (mut peer_, mut peer_listener_) = MemberPeer::create(member_config.clone()).await;

        let peer_id = peer_.id.clone();
        let peer_emitter = peer_.emitter();

        let mut is_request_to_shutdown = false;

        let task_admin = tokio::task::spawn(async move {
            peer_.run().await;
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