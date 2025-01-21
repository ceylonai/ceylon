use ceylon_core::{
    AgentDetail, EventHandler, MessageHandler, Processor, UnifiedAgent, UnifiedAgentConfig,
};
use sangedama::peer::PeerMode;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, Mutex};
use tokio::time::sleep;
use tracing::Level;

#[derive(Debug)]
enum AgentCommand {
    Broadcast(Vec<u8>),
    DirectMessage { to: String, message: Vec<u8> },
    Stop,
}

#[derive(Debug)]
struct TestMessageHandler {
    messages: Mutex<Vec<(String, Vec<u8>, u64)>>,
}

impl TestMessageHandler {
    fn new() -> Self {
        Self {
            messages: Mutex::new(Vec::new()),
        }
    }

    async fn get_messages(&self) -> Vec<(String, Vec<u8>, u64)> {
        self.messages.lock().await.clone()
    }
}

#[async_trait::async_trait]
impl MessageHandler for TestMessageHandler {
    async fn on_message(&self, agent_id: String, data: Vec<u8>, time: u64) {
        self.messages.lock().await.push((agent_id, data, time));
    }
}

#[derive(Debug)]
struct TestEventHandler {
    connections: Mutex<Vec<(String, AgentDetail)>>,
}

impl TestEventHandler {
    fn new() -> Self {
        Self {
            connections: Mutex::new(Vec::new()),
        }
    }

    async fn get_connections(&self) -> Vec<(String, AgentDetail)> {
        self.connections.lock().await.clone()
    }
}

#[async_trait::async_trait]
impl EventHandler for TestEventHandler {
    async fn on_agent_connected(&self, topic: String, agent: AgentDetail) {
        self.connections.lock().await.push((topic, agent));
    }
}

#[derive(Debug)]
struct TestProcessor {
    data: Mutex<Vec<Vec<u8>>>,
}

impl TestProcessor {
    fn new() -> Self {
        Self {
            data: Mutex::new(Vec::new()),
        }
    }

    async fn get_processed_data(&self) -> Vec<Vec<u8>> {
        self.data.lock().await.clone()
    }
}

#[async_trait::async_trait]
impl Processor for TestProcessor {
    async fn run(&self, input: Vec<u8>) {
        self.data.lock().await.push(input);
    }
}

async fn run_agent_with_commands(
    agent: UnifiedAgent,
    mut command_rx: mpsc::Receiver<AgentCommand>,
    inputs: Vec<u8>,
) {
    let agent = Arc::new(agent);
    let agent_clone = agent.clone();

    tokio::spawn(async move {
        while let Some(cmd) = command_rx.recv().await {
            match cmd {
                AgentCommand::Broadcast(message) => {
                    agent_clone.broadcast(message).await;
                }
                AgentCommand::DirectMessage { to, message } => {
                    agent_clone.send_direct(to, message).await;
                }
                AgentCommand::Stop => {
                    agent_clone.stop().await;
                    break;
                }
            }
        }
    });

    agent.start(inputs).await;
}

#[tokio::test]
async fn test_unified_agent_communication() {
    let subscriber = tracing_subscriber::FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .with_test_writer()
        .init();

    let (admin_tx, admin_rx) = mpsc::channel::<AgentCommand>(100);
    let (worker_tx, worker_rx) = mpsc::channel::<AgentCommand>(100);

    // Create admin components
    let admin_message_handler = Arc::new(TestMessageHandler::new());
    let admin_event_handler = Arc::new(TestEventHandler::new());
    let admin_processor = Arc::new(TestProcessor::new());

    // Create admin agent
    let admin_config = UnifiedAgentConfig {
        name: "admin-test".to_string(),
        role: "admin".to_string(),
        mode: PeerMode::Admin,
        work_space_id: "test-workspace".to_string(),
        port: Some(7846),
        admin_peer: None,
        admin_ip: None,
        buffer_size: Some(100),
    };

    let admin_agent = UnifiedAgent::new(
        admin_config,
        admin_message_handler.clone(),
        admin_processor.clone(),
        admin_event_handler.clone(),
    );

    let admin_id = admin_agent.details().id.clone();

    // Start admin agent
    let admin_handle = tokio::spawn(async move {
        run_agent_with_commands(admin_agent, admin_rx, "admin-input".as_bytes().to_vec()).await;
    });

    sleep(Duration::from_secs(1)).await;

    // Create worker components
    let worker_message_handler = Arc::new(TestMessageHandler::new());
    let worker_event_handler = Arc::new(TestEventHandler::new());
    let worker_processor = Arc::new(TestProcessor::new());

    // Create worker agent
    let worker_config = UnifiedAgentConfig {
        name: "worker-test".to_string(),
        role: "worker".to_string(),
        mode: PeerMode::Client,
        work_space_id: "test-workspace".to_string(),
        port: None,
        admin_peer: Some(admin_id.clone()),
        admin_ip: Some("127.0.0.1".to_string()),
        buffer_size: Some(100),
    };

    let worker_agent = UnifiedAgent::new(
        worker_config,
        worker_message_handler.clone(),
        worker_processor.clone(),
        worker_event_handler.clone(),
    );

    let worker_handle = tokio::spawn(async move {
        run_agent_with_commands(worker_agent, worker_rx, "worker-input".as_bytes().to_vec()).await;
    });

    sleep(Duration::from_secs(2)).await;

    // Test broadcast message
    worker_tx
        .send(AgentCommand::Broadcast(
            "test broadcast message".as_bytes().to_vec(),
        ))
        .await
        .unwrap();

    // Test direct message
    worker_tx
        .send(AgentCommand::DirectMessage {
            to: admin_id,
            message: "test direct message".as_bytes().to_vec(),
        })
        .await
        .unwrap();

    // sleep(Duration::from_secs(2)).await;

    // Verify messages and connections


    // Clean up
    // admin_tx.send(AgentCommand::Stop).await.unwrap();
    // worker_tx.send(AgentCommand::Stop).await.unwrap();

    tokio::try_join!(admin_handle, worker_handle).unwrap();
}