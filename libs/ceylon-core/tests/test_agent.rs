// /*
//  * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
//  * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
//  *
//  */
// use ceylon_core::{EventHandler, MessageHandler, Processor};
// #[cfg(test)]
// mod tests {
//     use ceylon_core::{
//        AgentDetail, EventHandler, MessageHandler, Processor,
//     };
//     use log::log;
//     use std::sync::Arc;
//     use std::time::Duration;
//     use tokio::sync::Mutex;
//     use tokio::time::sleep;
//     use tracing::info;
//
//     #[derive(Debug)]
//     struct TestMessageHandler {
//         received_messages: Arc<Mutex<Vec<(String, Vec<u8>, u64)>>>,
//     }
//
//     #[async_trait::async_trait]
//     impl MessageHandler for TestMessageHandler {
//         async fn on_message(&self, agent_id: String, data: Vec<u8>, time: u64) {
//             info!("Received message from agent {}", agent_id);
//             self.received_messages
//                 .lock()
//                 .await
//                 .push((agent_id, data, time));
//         }
//     }
//
//     #[derive(Debug)]
//     struct TestProcessor {}
//
//     #[async_trait::async_trait]
//     impl Processor for TestProcessor {
//         async fn run(&self, _input: Vec<u8>) {}
//     }
//
//     #[derive(Debug)]
//     struct TestEventHandler {
//         connected_agents: Arc<Mutex<Vec<(String, AgentDetail)>>>,
//     }
//
//     #[async_trait::async_trait]
//     impl EventHandler for TestEventHandler {
//         async fn on_agent_connected(&self, topic: String, agent: AgentDetail) {
//             self.connected_agents.lock().await.push((topic, agent));
//         }
//     }
//
//     #[tokio::test]
//     async fn test_admin_agent_creation() {
//         let config = AdminAgentConfig {
//             name: "test_admin".to_string(),
//             port: 8080,
//             buffer_size: 10,
//         };
//
//         let message_handler = Arc::new(TestMessageHandler {
//             received_messages: Arc::new(Mutex::new(Vec::new())),
//         });
//
//         let processor = Arc::new(TestProcessor {});
//
//         let event_handler = Arc::new(TestEventHandler {
//             connected_agents: Arc::new(Mutex::new(Vec::new())),
//         });
//
//         let admin_agent = AdminAgent::new(
//             config,
//             message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         );
//
//         assert_eq!(admin_agent.config.name, "test_admin");
//         assert_eq!(admin_agent.config.port, 8080);
//         assert_eq!(admin_agent.config.buffer_size, 10);
//
//         let agent_details = admin_agent.details();
//         assert_eq!(agent_details.name, "test_admin");
//         assert_eq!(agent_details.role, "admin");
//     }
//
//     #[tokio::test]
//     async fn test_worker_agent_creation() {
//         let config = WorkerAgentConfig {
//             name: "test_worker".to_string(),
//             role: "worker".to_string(),
//             conf_file: None,
//             work_space_id: "test_workspace".to_string(),
//             admin_peer: "admin_peer_id".to_string(),
//             admin_port: 8080,
//             admin_ip: "127.0.0.1".to_string(),
//             buffer_size: 10,
//         };
//
//         let message_handler = Arc::new(TestMessageHandler {
//             received_messages: Arc::new(Mutex::new(Vec::new())),
//         });
//
//         let processor = Arc::new(TestProcessor {});
//
//         let event_handler = Arc::new(TestEventHandler {
//             connected_agents: Arc::new(Mutex::new(Vec::new())),
//         });
//
//         let worker_agent = WorkerAgent::new(
//             config.clone(),
//             message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         );
//
//         let agent_details = worker_agent.details();
//         assert_eq!(agent_details.name, config.name);
//         assert_eq!(agent_details.role, config.role);
//     }
//
//     #[tokio::test]
//     async fn test_admin_worker_communication() {
//         let admin_config = AdminAgentConfig {
//             name: "test_admin".to_string(),
//             port: 8081,
//             buffer_size: 10,
//         };
//
//         let worker_config = WorkerAgentConfig {
//             name: "test_worker".to_string(),
//             role: "worker".to_string(),
//             conf_file: None,
//             work_space_id: "test_workspace".to_string(),
//             admin_peer: "".to_string(), // Will be set after admin agent starts
//             admin_port: 8081,
//             admin_ip: "127.0.0.1".to_string(),
//             buffer_size: 10,
//         };
//
//         // Create handlers with shared state for verification
//         let admin_messages = Arc::new(Mutex::new(Vec::new()));
//         let worker_messages = Arc::new(Mutex::new(Vec::new()));
//         let connected_agents = Arc::new(Mutex::new(Vec::new()));
//
//         let admin_message_handler = Arc::new(TestMessageHandler {
//             received_messages: admin_messages.clone(),
//         });
//
//         let worker_message_handler = Arc::new(TestMessageHandler {
//             received_messages: worker_messages.clone(),
//         });
//
//         let event_handler = Arc::new(TestEventHandler {
//             connected_agents: connected_agents.clone(),
//         });
//
//         let processor = Arc::new(TestProcessor {});
//
//         // Create and start admin agent
//         let admin_agent = AdminAgent::new(
//             admin_config,
//             admin_message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         );
//
//         // Create worker agent
//         let worker_agent = Arc::new(WorkerAgent::new(
//             worker_config,
//             worker_message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         ));
//
//         // Start admin agent with worker
//         let admin_handle = tokio::spawn(async move {
//             admin_agent
//                 .start(Vec::new(), vec![worker_agent.clone()])
//                 .await;
//         });
//
//         // Wait for agents to initialize
//         sleep(Duration::from_secs(1)).await;
//
//         // Verify communication
//         let connected = connected_agents.lock().await;
//         assert!(!connected.is_empty(), "Worker agent should be connected");
//
//         // Clean up
//         admin_handle.abort();
//     }
//
//     #[tokio::test]
//     async fn test_message_broadcasting() {
//         let admin_config = AdminAgentConfig {
//             name: "broadcast_admin".to_string(),
//             port: 8082,
//             buffer_size: 10,
//         };
//
//         let worker_config = WorkerAgentConfig {
//             name: "broadcast_worker".to_string(),
//             role: "worker".to_string(),
//             conf_file: None,
//             work_space_id: "broadcast_workspace".to_string(),
//             admin_peer: "".to_string(),
//             admin_port: 8082,
//             admin_ip: "127.0.0.1".to_string(),
//             buffer_size: 10,
//         };
//
//         let admin_messages = Arc::new(Mutex::new(Vec::new()));
//         let worker_messages = Arc::new(Mutex::new(Vec::new()));
//         let connected_agents = Arc::new(Mutex::new(Vec::new()));
//
//         let admin_message_handler = Arc::new(TestMessageHandler {
//             received_messages: admin_messages.clone(),
//         });
//
//         let worker_message_handler = Arc::new(TestMessageHandler {
//             received_messages: worker_messages.clone(),
//         });
//
//         let event_handler = Arc::new(TestEventHandler {
//             connected_agents: connected_agents.clone(),
//         });
//
//         let processor = Arc::new(TestProcessor {});
//
//         let admin_agent = AdminAgent::new(
//             admin_config,
//             admin_message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         );
//
//         let worker_agent = Arc::new(WorkerAgent::new(
//             worker_config,
//             worker_message_handler.clone(),
//             processor.clone(),
//             event_handler.clone(),
//         ));
//
//         // Start admin agent
//         let admin_handle = tokio::spawn(async move {
//             admin_agent
//                 .start(Vec::new(), vec![worker_agent.clone()])
//                 .await;
//         });
//
//         // Wait for initialization
//         sleep(Duration::from_secs(1)).await;
//
//         // Verify initial connection
//         let connected = connected_agents.lock().await;
//         assert!(!connected.is_empty(), "Worker agent should be connected");
//
//         // Clean up
//         admin_handle.abort();
//     }
// }
