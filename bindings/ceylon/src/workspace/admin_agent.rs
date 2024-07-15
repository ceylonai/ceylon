use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{AdminPeer, AdminPeerConfig};
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex};
use tokio::{select, signal};
use tracing::{debug, info};

#[derive(Clone)]
pub struct AdminAgentConfig {
    pub name: String,
    pub port: u16,
}
pub struct AdminAgent {
    pub config: AdminAgentConfig,
}

impl AdminAgent {
    pub fn new(config: AdminAgentConfig) -> AdminAgent {

        AdminAgent {
            config,
        }
    }

    pub async fn run(&self, inputs: Vec<u8>) {
        self.run_(inputs).await;
    }
    pub async fn run_(&self, inputs: Vec<u8>) {
        info!("Workspace {} running", self.config.name);

        let config = self.config.clone();
        let admin_config = AdminPeerConfig::new(config.port, config.name.clone());
        let (mut peer_, mut peer_listener_) = AdminPeer::create(admin_config.clone()).await;

        let admin_id = peer_.id.clone();
        let admin_emitter = peer_.emitter();

        let mut is_request_to_shutdown = false;


        let name = self.config.name.clone();
        loop {
            if is_request_to_shutdown {
                break;
            }
            select! {
               event = peer_listener_.recv() => {
                    if event.is_some() {
                        let event = event.unwrap();
                        match event{
                            NodeMessage::Message{ data,created_by, ..} => {
                                info!("Admin listener Message {:?} from {:?}",String::from_utf8(data),created_by);
                            }
                            _ => {
                                info!("peer1 listener {:?}", event);
                            }
                        }
                    }
                }

                 _ = signal::ctrl_c() => {
                    println!("Agent {:?} received exit signal", name);
                    // Perform any necessary cleanup here
                    is_request_to_shutdown = true;
                },
            }
        }
    }

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }
}
