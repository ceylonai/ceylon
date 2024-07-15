use async_trait::async_trait;
use tokio::{select, signal};
use tracing::info;
use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{AdminPeer, AdminPeerConfig};
use crate::workspace::agent::{Agent, AgentBase, AgentConfig};

pub type AdminAgent = Agent;
pub type AdminAgentConfig = AgentConfig;

#[async_trait::async_trait]
impl AgentBase for AdminAgent {
    async fn run_(&self, inputs: Vec<u8>) {
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