use std::sync::Arc;
use serde_json::json;
use tokio::io;
use tokio::io::AsyncBufReadExt;

mod agent;
pub use agent::{
    agent::AgentCore,
    agent_base::{AgentDefinition, MessageHandler, Processor},
    workspace::{Workspace, WorkspaceConfig},
    state::{AgentState, Message, SystemMessage},
};

#[derive(Debug)]
struct AgentHandler {
    tx_0: tokio::sync::mpsc::Sender<Vec<u8>>,
}

#[async_trait::async_trait]
impl MessageHandler for AgentHandler {
    async fn on_message(&self, agent_id: String, data: Vec<u8>, time: u64) {
        println!("Agent {} received message {:?}", agent_id, String::from_utf8_lossy(&data));
    }
}

#[async_trait::async_trait]
impl Processor for AgentHandler {
    async fn run(&self, input: Vec<u8>) -> () {
        println!("Agent received input {:?}", input);
        let mut stdin = io::BufReader::new(io::stdin()).lines();
        loop {
            tokio::select! {
                line = stdin.next_line() => {
                    let line = line.unwrap();
                    if let Some(line) = line {
                        println!("Entered : {}" ,line.clone());
                        self.tx_0.send(
                            json!({
                                "data": format!("Human : {}", line),
                            }).to_string().into_bytes()
                        ).await.unwrap();
                    }
                },
            }
        }
    }
}

#[tokio::main]
async fn main() {
    tokio::spawn(async move {
        env_logger::init();
        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        let definition = AgentDefinition {
            id: None,
            name: "test".to_string(),
            position: "test".to_string(),
            responsibilities: vec!["test".to_string()],
            instructions: vec!["test".to_string()],
        };
        let ag = AgentCore::new(
            definition,
            Arc::new(AgentHandler { tx_0: tx_0.clone() }),
            Arc::new(AgentHandler { tx_0: tx_0.clone() }),
        );
        let ag_tx = ag.get_tx_0();
        tokio::spawn(async move {
            ag.start(
                "test_topic".to_string(),
                "/ip4/0.0.0.0/udp/0/quic-v1".to_string(),
                vec![],
            )
                .await;
        });

        loop {
            tokio::select! {
                message = rx_0.recv() => {
                    if let Some(raw_message) = message {
                        let msg = SystemMessage::Content(Message::new(raw_message, None, "test".to_string()));
                        ag_tx.send(msg).await.unwrap();
                    }
                }
            }
        }
    })
        .await
        .unwrap();
}
