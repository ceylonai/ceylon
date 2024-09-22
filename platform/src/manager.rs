use async_trait::async_trait;
use ceylon::{AdminAgent, AdminAgentConfig, AgentDetail, EventHandler, MessageHandler, Processor};
use std::fmt::Debug;
use std::sync::Arc;

// Dummy implementation for MessageHandler
#[derive(Clone, Debug)]
struct MyMessageHandler;

#[async_trait]
impl MessageHandler for MyMessageHandler {
    async fn on_message(&self, created_by: String, message: Vec<u8>, time: u64) {
        println!(
            "Received message from {} at {}: {:?}",
            created_by, time, message
        );
        // Add your message handling logic here
    }
}

// Dummy implementation for Processor
#[derive(Clone, Debug)]
struct MyProcessor;

#[async_trait]
impl Processor for MyProcessor {
    async fn run(&self, input: Vec<u8>) {
        println!("Processing input: {:?}", input);
        // Add your processing logic here
    }
}

// Dummy implementation for EventHandler
#[derive(Clone, Debug)]
struct MyEventHandler;


#[async_trait]
impl EventHandler for MyEventHandler {
    async fn on_agent_connected(&self, topic: String, agent_detail: AgentDetail) {
        println!(
            "Agent connected on topic {}: {:?}",
            topic, agent_detail
        );
        // Add your event handling logic here
    }
}


pub fn get_manager(name: String, port: u16) -> AdminAgent {
    let config = AdminAgentConfig {
        name,
        port,
    };
    let message_handler = Arc::new(MyMessageHandler) as Arc<dyn MessageHandler + Send + Sync>;
    let processor = Arc::new(MyProcessor) as Arc<dyn Processor + Send + Sync>;
    let event_handler = Arc::new(MyEventHandler) as Arc<dyn EventHandler + Send + Sync>;

    let admin_agent = AdminAgent::new(
        config,
        message_handler,
        processor,
        event_handler,
    );
    admin_agent
}