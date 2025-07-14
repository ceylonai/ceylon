use anyhow::Result;
use serde_json::json;
use std::io::{self, Write};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::{broadcast, mpsc};
use chrono::{DateTime, Utc};

// Import your agent communication library
use agent_communication::{AgentNode, core::node::AgentCommand, core::node::AgentNodeEvent, AnpMessage};

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
        println!("🚀 Starting P2P Chat for user: {}", self.username);
        println!("📡 Your Peer ID: {}", self.node.local_peer_id());
        println!("🎧 Listening for peers...");
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
                    if internal_tx.send(InternalEvent::UserInput(input.to_string())).is_err() {
                        break;
                    }

                    match input {
                        "/help" | "/h" => {
                            Self::print_help_static();
                        }
                        "/peers" | "/p" => {
                            if let Err(e) = command_tx.send(AgentCommand::GetPeers) {
                                eprintln!("Failed to send peers command: {:?}", e);
                            }
                        }
                        "/quit" | "/q" | "/exit" => {
                            // This will be handled by the main loop
                            break;
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
                            }
                        }
                        _ => {
                            // Regular chat message (broadcast)
                            let payload = json!({
                                "action": "chat_message",
                                "message": input,
                                "sender": username,
                                "timestamp": Utc::now().to_rfc3339(),
                                "message_type": "broadcast"
                            });

                            if let Err(e) = command_tx.send(AgentCommand::BroadcastMessage { payload }) {
                                eprintln!("Failed to send message: {:?}", e);
                            }
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
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::PeerDisconnected { peer_id } => {
                println!("\n❌ Peer disconnected: {}", peer_id);
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

            AgentNodeEvent::ConnectionEstablished { peer_id } => {
                println!("\n🔗 Connected to peer: {}", peer_id);
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::ConnectionClosed { peer_id } => {
                println!("\n🔌 Connection closed with peer: {}", peer_id);
                Self::print_prompt_static(username);
            }

            AgentNodeEvent::Error { description } => {
                println!("\n⚠️ Error: {}", description);
                Self::print_prompt_static(username);
            }
        }
    }

    /// Handle incoming messages
    async fn handle_incoming_message(username: &str, from: &str, message: &AnpMessage) {
        let action = message.payload.get("action").and_then(|v| v.as_str());

        match action {
            Some("chat_message") => {
                let sender = message.payload.get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                let msg = message.payload.get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let timestamp = message.payload.get("timestamp")
                    .and_then(|v| v.as_str())
                    .and_then(|s| s.parse::<DateTime<Utc>>().ok());

                let time_str = if let Some(ts) = timestamp {
                    ts.format("%H:%M:%S").to_string()
                } else {
                    "??:??:??".to_string()
                };

                println!("\n💬 [{}] {}: {}", time_str, sender, msg);
                Self::print_prompt_static(username);
            }

            Some("private_message") => {
                let sender = message.payload.get("sender")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown");
                let msg = message.payload.get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let timestamp = message.payload.get("timestamp")
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

            Some("heartbeat") => {
                // Silently handle heartbeats (already logged by the library)
            }

            Some("ack") => {
                // Silently handle acknowledgments
            }

            _ => {
                // Handle other message types
                println!("\n📩 Message from {}: {:?}", from, message.payload);
                Self::print_prompt_static(username);
            }
        }
    }

    /// Print the user prompt (static version)
    fn print_prompt_static(username: &str) {
        print!("{}> ", username);
        io::stdout().flush().unwrap();
    }

    fn print_help_static() {
        println!("📋 P2P Chat Commands:");
        println!("   <message>           - Send message to all peers");
        println!("   /msg <peer> <text>  - Send private message to specific peer");
        println!("   /peers (/p)         - List discovered peers");
        println!("   /help (/h)          - Show this help");
        println!("   /quit (/q)          - Exit chat");
        println!();
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();

    let (username, port) = if args.len() >= 3 {
        let username = args[1].clone();
        let port = args[2].parse::<u16>()
            .map_err(|_| anyhow::anyhow!("Invalid port number"))?;
        (username, port)
    } else {
        println!("Usage: {} <username> <port>", args[0]);
        println!("Example: {} Alice 4001", args[0]);
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
    use tokio::time::{timeout, Duration};

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
}