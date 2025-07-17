use anyhow::Result;
use chrono::{DateTime, Utc};
use serde_json::json;
use std::io::{self, Write};
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::mpsc;

// Import your agent communication library
use agent_communication::{
    AgentNode, AnpMessage,
};

// Import the types directly from the core::node module
use agent_communication::core::node::{AgentCommand, AgentNodeEvent};

// Internal events for communication between tasks
#[derive(Debug, Clone)]
enum InternalEvent {
    UserInput(String),
    NodeEvent(AgentNodeEvent),
    Shutdown,
}

pub struct P2PChat {
    node: AgentNode,
    username: String,
}

impl P2PChat {
    /// Create a new P2P chat instance
    pub async fn new(username: &str, port: u16) -> Result<Self> {
        let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);
        let node = AgentNode::new(username, &listen_addr).await?;

        Ok(Self {
            node,
            username: username.to_string(),
        })
    }

    /// Start the chat application
    pub async fn start(mut self) -> Result<()> {
        println!("🚀 Starting Enhanced P2P Chat for user: {}", self.username);
        println!("📡 Your Peer ID: {}", self.node.local_peer_id());
        println!("🎧 Listening for peers...");
        println!("📻 GossipSub enabled for topic-based messaging");
        println!("🌐 Auto-subscribed to 'agent-network' topic");
        println!();
        Self::print_help_static();

        // Set up command channel for sending messages to the node
        let node_command_tx = self.node.setup_command_channel();

        // Subscribe to events from the node
        let mut node_event_rx = self.node.subscribe_events();

        // Create internal communication channels
        let (internal_tx, mut internal_rx) = mpsc::unbounded_channel::<InternalEvent>();

        // Clone for tasks
        let username = self.username.clone();
        let input_tx = internal_tx.clone();
        let event_tx = internal_tx.clone();
        let node_cmd_tx = node_command_tx.clone();

        // Subscribe to some default topics
        let default_topics = vec!["general", "announcements"];
        for topic in default_topics {
            if let Err(e) = node_command_tx.send(AgentCommand::SubscribeToTopic {
                topic: topic.to_string(),
            }) {
                eprintln!("Failed to subscribe to {}: {:?}", topic, e);
            } else {
                println!("📡 Auto-subscribed to topic: {}", topic);
            }
        }

        // Spawn input handler task
        let input_task = tokio::spawn(async move {
            Self::handle_user_input(input_tx, username, node_cmd_tx).await;
        });

        // Spawn node event handler task
        let event_task = tokio::spawn(async move {
            while let Ok(event) = node_event_rx.recv().await {
                if event_tx.send(InternalEvent::NodeEvent(event)).is_err() {
                    break;
                }
            }
        });

        // Spawn node runner task
        let node_task = tokio::spawn(async move {
            if let Err(e) = self.node.run().await {
                eprintln!("Node error: {:?}", e);
            }
        });

        // Main event loop
        let username_for_display = self.username.clone();
        while let Some(event) = internal_rx.recv().await {
            match event {
                InternalEvent::UserInput(input) => {
                    // Handle user input
                    if input == "/quit" || input == "/q" || input == "/exit" {
                        println!("👋 Goodbye!");
                        let _ = node_command_tx.send(AgentCommand::Shutdown);
                        break;
                    }
                }
                InternalEvent::NodeEvent(node_event) => {
                    Self::handle_node_event(&username_for_display, node_event).await;
                }
                InternalEvent::Shutdown => {
                    break;
                }
            }
        }

        // Clean up tasks
        input_task.abort();
        event_task.abort();
        node_task.abort();

        Ok(())
    }

    /// Handle user input from stdin
    async fn handle_user_input(
        internal_tx: mpsc::UnboundedSender<InternalEvent>,
        username: String,
        command_tx: mpsc::UnboundedSender<AgentCommand>,
    ) {
        let stdin = tokio::io::stdin();
        let mut reader = BufReader::new(stdin);
        let mut line = String::new();

        loop {
            print!("{}> ", username);
            io::stdout().flush().unwrap();

            line.clear();
            match reader.read_line(&mut line).await {
                Ok(0) => break, // EOF
                Ok(_) => {
                    let input = line.trim();

                    if input.is_empty() {
                        continue;
                    }

                    // Send input to main loop for processing
                    if internal_tx
                        .send(InternalEvent::UserInput(input.to_string()))
                        .is_err()
                    {
                        break;
                    }

                    match input {
                        "/help" | "/h" => {
                            Self::print_help_static();
                        }
                        "/peers" | "/p" => {
                            if let Err(e) = command_tx.send(AgentCommand::GetPeers) {
                                eprintln!("Failed to send peers command: {:?}", e);
                            } else {
                                println!("ℹ️ Peer list requested (libp2p handles pings automatically)");
                            }
                        }
                        "/topics" | "/t" => {
                            if let Err(e) = command_tx.send(AgentCommand::GetTopics) {
                                eprintln!("Failed to get topics: {:?}", e);
                            } else {
                                println!("📋 Subscribed topics list requested");
                            }
                        }
                        "/ping" => {
                            // Send application-level ping to all peers via direct messaging
                            let payload = json!({
                                "action": "app_ping",
                                "sender": username,
                                "timestamp": Utc::now().to_rfc3339(),
                                "manual_ping": true
                            });

                            if let Err(e) =
                                command_tx.send(AgentCommand::BroadcastMessage { payload })
                            {
                                eprintln!("Failed to send ping: {:?}", e);
                            } else {
                                println!("📡 Application ping sent to all peers (direct)");
                            }
                        }
                        "/status" => {
                            println!("📊 Node Status:");
                            if let Err(e) = command_tx.send(AgentCommand::GetPeers) {
                                eprintln!("Failed to get peer status: {:?}", e);
                            }
                            if let Err(e) = command_tx.send(AgentCommand::GetTopics) {
                                eprintln!("Failed to get topic status: {:?}", e);
                            }
                        }
                        "/reconnect" => {
                            println!("🔄 Reconnection Info:");
                            println!("   - libp2p handles reconnections automatically via mDNS discovery");
                            println!("   - GossipSub mesh healing happens automatically");
                            println!("   - Connection state is managed transparently");
                        }
                        "/verbose" => {
                            println!("🔍 Verbose Mode Information:");
                            println!("   - Connection events are automatically displayed");
                            println!("   - Ping results are shown when they occur");
                            println!("   - Direct message send/receive events are logged");
                            println!("   - GossipSub topic messages are displayed");
                            println!("   - Topic subscription/unsubscription events are shown");
                        }
                        input if input.starts_with("/topic ") => {
                            // Subscribe to topic: /topic <topic_name>
                            let topic = &input[7..].trim();
                            if !topic.is_empty() {
                                if let Err(e) = command_tx.send(AgentCommand::SubscribeToTopic {
                                    topic: topic.to_string(),
                                }) {
                                    eprintln!("Failed to subscribe to topic: {:?}", e);
                                } else {
                                    println!("📡 Subscribing to topic: {}", topic);
                                }
                            } else {
                                println!("Usage: /topic <topic_name>");
                                println!("Example: /topic gaming");
                            }
                        }
                        input if input.starts_with("/untopic ") => {
                            // Unsubscribe from topic: /untopic <topic_name>
                            let topic = &input[9..].trim();
                            if !topic.is_empty() {
                                if let Err(e) = command_tx.send(AgentCommand::UnsubscribeFromTopic {
                                    topic: topic.to_string(),
                                }) {
                                    eprintln!("Failed to unsubscribe from topic: {:?}", e);
                                } else {
                                    println!("📡 Unsubscribing from topic: {}", topic);
                                }
                            } else {
                                println!("Usage: /untopic <topic_name>");
                                println!("Example: /untopic gaming");
                            }
                        }
                        input if input.starts_with("/pub ") => {
                            // Publish to topic: /pub <topic> <message>
                            let parts: Vec<&str> = input[5..].splitn(2, ' ').collect();
                            if parts.len() == 2 {
                                let topic = parts[0];
                                let message = parts[1];

                                if let Err(e) = command_tx.send(AgentCommand::PublishToTopic {
                                    topic: topic.to_string(),
                                    message: message.to_string(),
                                }) {
                                    eprintln!("Failed to publish to topic: {:?}", e);
                                } else {
                                    println!("📢 Publishing to topic '{}': {}", topic, message);
                                }
                            } else {
                                println!("Usage: /pub <topic> <message>");
                                println!("Example: /pub general Hello everyone!");
                            }
                        }
                        input if input.starts_with("/tpeers ") => {
                            // Get topic peers: /tpeers <topic>
                            let topic = &input[8..].trim();
                            if !topic.is_empty() {
                                if let Err(e) = command_tx.send(AgentCommand::GetTopicPeers {
                                    topic: topic.to_string(),
                                }) {
                                    eprintln!("Failed to get topic peers: {:?}", e);
                                } else {
                                    println!("👥 Getting peers for topic: {}", topic);
                                }
                            } else {
                                println!("Usage: /tpeers <topic>");
                                println!("Example: /tpeers general");
                            }
                        }
                        input if input.starts_with("/msg ") => {
                            // Private message: /msg <peer_id> <message>
                            let parts: Vec<&str> = input[5..].splitn(2, ' ').collect();
                            if parts.len() == 2 {
                                let peer_id = parts[0];
                                let message = parts[1];

                                let payload = json!({
                                    "action": "private_message",
                                    "message": message,
                                    "sender": username,
                                    "timestamp": Utc::now().to_rfc3339(),
                                    "message_type": "private"
                                });

                                if let Err(e) = command_tx.send(AgentCommand::SendMessage {
                                    to: peer_id.to_string(),
                                    payload,
                                }) {
                                    eprintln!("Failed to send private message: {:?}", e);
                                }
                            } else {
                                println!("Usage: /msg <peer_id> <message>");
                                println!("Tip: Use /peers to see available peer IDs");
                            }
                        }
                        input if input.starts_with("/broadcast ") => {
                            // Broadcast via direct messaging: /broadcast <message>
                            let message = &input[11..];
                            if !message.is_empty() {
                                let payload = json!({
                                    "action": "broadcast_message",
                                    "message": message,
                                    "sender": username,
                                    "timestamp": Utc::now().to_rfc3339(),
                                    "message_type": "broadcast"
                                });

                                if let Err(e) =
                                    command_tx.send(AgentCommand::BroadcastMessage { payload })
                                {
                                    eprintln!("Failed to broadcast message: {:?}", e);
                                } else {
                                    println!("📡 Broadcasting message to all peers");
                                }
                            } else {
                                println!("Usage: /broadcast <message>");
                                println!("Example: /broadcast Hello everyone!");
                            }
                        }
                        _ => {
                            // Default: Publish to general topic
                            if let Err(e) = command_tx.send(AgentCommand::PublishToTopic {
                                topic: "general".to_string(),
                                message: input.to_string(),
                            }) {
                                eprintln!("Failed to publish to general topic: {:?}", e);
                            }
                            // Also show it locally for immediate feedback
                            println!("📢 [general] {}: {}", username, input);
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Error reading input: {:?}", e);
                    break;
                }
            }
        }
    }

    /// Handle events from the agent node
    async fn handle_node_event(username: &str, event: AgentNodeEvent) {
        match event {
            AgentNodeEvent::PeerDiscovered { peer_id, address } => {
                println!("\n🔎 New peer discovered!");
                println!("   Peer ID: {}", peer_id);
                println!("   Address: {}", address);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PeerDisconnected { peer_id } => {
                println!("\n❌ Peer disconnected: {}", peer_id);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   Reason: Connection closed or expired");
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::ConnectionEstablished { peer_id } => {
                println!("\n🔗 Connected to peer: {}", peer_id);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   Status: Active connection established");
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::ConnectionClosed { peer_id } => {
                println!("\n🔌 Connection closed with peer: {}", peer_id);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   Note: Peer may still be discoverable for reconnection");
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PingSuccess { peer_id, rtt } => {
                println!("\n🏓 Ping success to peer: {}", peer_id);
                println!("   RTT: {:?}", rtt);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PingFailure { peer_id } => {
                println!("\n⏰ Ping failed to peer: {}", peer_id);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   Note: Connection may be having issues");
                Self::print_prompt_static(username);
            }

            // New GossipSub events
            AgentNodeEvent::GossipSubMessageReceived {
                topic,
                from,
                message,
                message_id
            } => {
                let time_str = Utc::now().format("%H:%M:%S");
                println!("\n📻 [{}] [{}] {}: {}", time_str, topic, from, message);
                println!("   Message ID: {}", message_id);
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::TopicSubscribed { topic } => {
                println!("\n📡 Subscribed to topic: {}", topic);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   You can now receive messages from this topic");
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::TopicUnsubscribed { topic } => {
                println!("\n📭 Unsubscribed from topic: {}", topic);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                println!("   You will no longer receive messages from this topic");
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PeerSubscribedToTopic { peer_id, topic } => {
                println!("\n👤 Peer {} joined topic: {}", peer_id, topic);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PeerUnsubscribedFromTopic { peer_id, topic } => {
                println!("\n👤 Peer {} left topic: {}", peer_id, topic);
                println!("   Time: {}", Utc::now().format("%H:%M:%S"));
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::MessageReceived { from, message } => {
                Self::handle_incoming_message(username, &from, &message).await;
            }

            AgentNodeEvent::MessageSent { to, message } => {
                // Only show confirmation for private messages
                if let Some(action) = message.payload.get("action").and_then(|v| v.as_str()) {
                    if action == "private_message" {
                        println!("\n📤 Private message sent to {}", to);
                        Self::print_prompt_static(username);
                    }
                }
            }

            AgentNodeEvent::Error { description } => {
                println!("\n⚠️ Error: {}", description);
                Self::print_prompt_static(username);
            }
        }
    }

    /// Handle incoming direct messages (RequestResponse)
    async fn handle_incoming_message(username: &str, from: &str, message: &AnpMessage) {
        let action = message.payload.get("action").and_then(|v| v.as_str());

        match action {
            Some("chat_message") => {
                let sender = message
                    .payload
                    .get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                let msg = message
                    .payload
                    .get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let timestamp = message
                    .payload
                    .get("timestamp")
                    .and_then(|v| v.as_str())
                    .and_then(|s| s.parse::<DateTime<Utc>>().ok());

                let time_str = if let Some(ts) = timestamp {
                    ts.format("%H:%M:%S").to_string()
                } else {
                    "??:??:??".to_string()
                };

                println!("\n💬 [{}] Direct from {}: {}", time_str, sender, msg);
                Self::print_prompt_static(username);
            }

            Some("private_message") => {
                let sender = message
                    .payload
                    .get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                let msg = message
                    .payload
                    .get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let timestamp = message
                    .payload
                    .get("timestamp")
                    .and_then(|v| v.as_str())
                    .and_then(|s| s.parse::<DateTime<Utc>>().ok());

                let time_str = if let Some(ts) = timestamp {
                    ts.format("%H:%M:%S").to_string()
                } else {
                    "??:??:??".to_string()
                };

                println!("\n📨 [{}] Private from {}: {}", time_str, sender, msg);
                Self::print_prompt_static(username);
            }

            Some("broadcast_message") => {
                let sender = message
                    .payload
                    .get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                let msg = message
                    .payload
                    .get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let timestamp = message
                    .payload
                    .get("timestamp")
                    .and_then(|v| v.as_str())
                    .and_then(|s| s.parse::<DateTime<Utc>>().ok());

                let time_str = if let Some(ts) = timestamp {
                    ts.format("%H:%M:%S").to_string()
                } else {
                    "??:??:??".to_string()
                };

                println!("\n📡 [{}] Broadcast from {}: {}", time_str, sender, msg);
                Self::print_prompt_static(username);
            }

            Some("app_ping") => {
                let sender = message
                    .payload
                    .get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                println!("\n🏓 Application ping received from {}", sender);
                Self::print_prompt_static(username);
            }

            Some("heartbeat") => {
                // Silently handle heartbeats (already logged by the library)
            }

            Some("ack") => {
                // Silently handle acknowledgments
            }

            _ => {
                // Handle other message types
                println!("\n📩 Direct message from {}: {:?}", from, message.payload);
                Self::print_prompt_static(username);
            }
        }
    }

    /// Print the user prompt (static version)
    fn print_prompt_static(username: &str) {
        print!("{}> ", username);
        io::stdout().flush().unwrap();
    }

    // Enhanced help text with GossipSub commands
    fn print_help_static() {
        println!("📋 Enhanced P2P Chat Commands:");
        println!();
        println!("🔹 Basic Messaging:");
        println!("   <message>             - Publish to 'general' topic (default)");
        println!("   /broadcast <message>  - Send direct message to all peers");
        println!("   /msg <peer> <text>    - Send private message to specific peer");
        println!();
        println!("🔹 Topic Commands (GossipSub):");
        println!("   /pub <topic> <msg>    - Publish message to specific topic");
        println!("   /topic <name>         - Subscribe to a topic");
        println!("   /untopic <name>       - Unsubscribe from a topic");
        println!("   /topics (/t)          - List your subscribed topics");
        println!("   /tpeers <topic>       - List peers subscribed to topic");
        println!();
        println!("🔹 Network Commands:");
        println!("   /peers (/p)           - List discovered peers");
        println!("   /ping                 - Send application ping to all peers");
        println!("   /status               - Show connection and topic status");
        println!();
        println!("🔹 Info & Control:");
        println!("   /reconnect            - Show reconnection info");
        println!("   /verbose              - Show verbose mode information");
        println!("   /help (/h)            - Show this help");
        println!("   /quit (/q)            - Exit chat");
        println!();
        println!("ℹ️ Notes:");
        println!("   • Default topics: 'agent-network', 'general', 'announcements'");
        println!("   • GossipSub provides efficient topic-based broadcasting");
        println!("   • Direct messages use RequestResponse for reliability");
        println!("   • libp2p handles connections and discovery automatically");
        println!();
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();

    let (username, port) = if args.len() >= 3 {
        let username = args[1].clone();
        let port = args[2]
            .parse::<u16>()
            .map_err(|_| anyhow::anyhow!("Invalid port number"))?;
        (username, port)
    } else {
        println!("Usage: {} <username> <port>", args[0]);
        println!("Example: {} Alice 4001", args[0]);
        println!();
        println!("🎯 Enhanced P2P Chat with GossipSub Support");
        println!("   • Topic-based messaging with /pub and /topic commands");
        println!("   • Direct peer messaging with /msg command");
        println!("   • Automatic peer discovery and connection management");
        println!("   • Real-time connection and ping status updates");
        std::process::exit(1);
    };

    // Create and start the chat
    let chat = P2PChat::new(&username, port).await?;
    chat.start().await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{Duration, timeout};

    #[tokio::test]
    async fn test_chat_creation() {
        let chat = P2PChat::new("TestUser", 0).await;
        assert!(chat.is_ok());

        let chat = chat.unwrap();
        assert_eq!(chat.username, "TestUser");
    }

    #[tokio::test]
    async fn test_multiple_chat_instances() {
        let chat1 = P2PChat::new("User1", 0).await;
        let chat2 = P2PChat::new("User2", 0).await;

        assert!(chat1.is_ok());
        assert!(chat2.is_ok());

        // Verify they have different peer IDs
        let chat1 = chat1.unwrap();
        let chat2 = chat2.unwrap();

        assert_ne!(chat1.node.local_peer_id(), chat2.node.local_peer_id());
    }

    #[tokio::test]
    async fn test_chat_with_custom_topics() {
        let chat = P2PChat::new("TopicUser", 0).await;
        assert!(chat.is_ok());

        // Chat instance should be ready for topic operations
        let chat = chat.unwrap();
        assert!(!chat.username.is_empty());
    }
}