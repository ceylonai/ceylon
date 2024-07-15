use sangedama::peer::message::data::NodeMessage;
use sangedama::peer::node::{AdminPeer, AdminPeerConfig};
use tokio::{select, signal};
use tracing::info;

#[derive(Clone)]
pub struct AgentConfig {
    pub name: String,
    pub port: u16,
}

pub struct Agent {
    pub config: AgentConfig,
}

impl Agent {
    pub fn new(config: AgentConfig) -> Agent {
        Agent { config }
    }

    pub async fn run(&self, inputs: Vec<u8>) {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        rt.block_on(async {
            self.run_(inputs).await;
        });
    }   

    pub async fn stop(&self) {
        info!("Agent {} stop called", self.config.name);
    }
}

#[async_trait::async_trait]
pub trait AgentBase{
    async fn run_(&self, inputs: Vec<u8>);
}