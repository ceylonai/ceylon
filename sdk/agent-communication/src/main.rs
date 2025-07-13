// main.rs - Example demonstrating node discovery and welcome messages

use anyhow::Result;
use futures::StreamExt;
use libp2p::request_response::{Event, Message, OutboundRequestId};
use libp2p::{
    Multiaddr, PeerId, Swarm, SwarmBuilder, Transport, core::upgrade, identity, mdns, noise,
    request_response, swarm::SwarmEvent, tcp, yamux,
};
use serde_json::json;
use std::collections::HashMap;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::time::{Instant, interval};

// Import your existing modules
use agent_communication::anp::AnpMessage;
use agent_communication::behaviour::{AgentBehaviour, AgentEvent};
use agent_communication::handlers::handle_message;
use agent_communication::messaging::{ANP_PROTOCOL, AnpCodec, AnpRequest, AnpResponse};

pub struct DiscoveryNode {
    pub name: String,
    pub swarm: Swarm<AgentBehaviour>,
    pub discovered_peers: HashMap<PeerId, Multiaddr>,
    pub welcomed_peers: HashMap<PeerId, bool>, // Track which peers we've welcomed
    pub last_discovery_time: Instant,
    pub pending_requests: HashMap<OutboundRequestId, PeerId>,
}

impl DiscoveryNode {
    pub async fn new(name: &str, listen_addr: &str) -> Result<Self> {
        // 1️⃣ Generate unique identity for this node
        let id_keys = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(id_keys.public());
        println!("🔑 {} Peer ID: {}", name, peer_id);

        // 2️⃣ Create transport with noise encryption and yamux multiplexing
        let transport = tcp::tokio::Transport::new(tcp::Config::default().nodelay(true))
            .upgrade(upgrade::Version::V1)
            .authenticate(noise::Config::new(&id_keys)?)
            .multiplex(yamux::Config::default())
            .boxed();

        // 3️⃣ Configure RequestResponse behavior for ANP protocol
        let mut req_resp_config = request_response::Config::default();
        // req_resp_config.set_request_timeout(Duration::from_secs(10));
        // req_resp_config.set_connection_keep_alive(Duration::from_secs(30));

        let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
        let request_response = request_response::Behaviour::new(protocols, req_resp_config);

        // 4️⃣ Configure mDNS for local network peer discovery
        let mdns = mdns::Behaviour::new(mdns::Config::default(), peer_id)?;

        // 5️⃣ Combine behaviors
        let behaviour = AgentBehaviour {
            request_response,
            mdns,
        };

        // 6️⃣ Create and configure swarm
        let mut swarm = Swarm::new(
            transport,
            behaviour,
            peer_id,
            libp2p_swarm::Config::with_tokio_executor(),
        );

        // 7️⃣ Start listening on specified address
        let addr: Multiaddr = listen_addr.parse()?;
        swarm.listen_on(addr.clone())?;
        println!("🎧 {} listening on {}", name, addr);

        Ok(Self {
            name: name.to_string(),
            swarm,
            discovered_peers: HashMap::new(),
            welcomed_peers: HashMap::new(),
            last_discovery_time: Instant::now(),
            pending_requests: HashMap::new(),
        })
    }

    pub async fn run(&mut self) -> Result<()> {
        let mut discovery_interval = interval(Duration::from_secs(5)); // Check for new peers every 5 seconds
        let mut stdin = BufReader::new(tokio::io::stdin()).lines();

        println!("🟢 {} is running and ready to discover peers", self.name);
        println!("💡 Type 'peers' to see discovered peers, 'quit' to exit");

        loop {
            tokio::select! {
                // Periodic discovery and welcome check
                _ = discovery_interval.tick() => {
                    self.send_welcome_to_new_peers().await;
                }

                // Handle user commands
                line = stdin.next_line() => {
                    if let Ok(Some(input)) = line {
                        match input.trim() {
                            "quit" | "exit" => {
                                println!("👋 {} shutting down", self.name);
                                break;
                            }
                            "peers" => {
                                self.list_discovered_peers();
                            }
                            "welcome" => {
                                self.send_welcome_to_all_peers().await;
                            }
                            input if input.starts_with("msg ") => {
                                let message = &input[4..];
                                self.broadcast_message(message).await;
                            }
                            _ => {
                                println!("💡 Commands: 'peers', 'welcome', 'msg <text>', 'quit'");
                            }
                        }
                    }
                }

                // Handle network events
                event = self.swarm.select_next_some() => {
                    self.handle_swarm_event(event).await;
                }
            }
        }

        Ok(())
    }

    fn list_discovered_peers(&self) {
        if self.discovered_peers.is_empty() {
            println!("📭 No peers discovered yet");
        } else {
            println!("👥 Discovered peers ({}):", self.discovered_peers.len());
            for (peer_id, addr) in &self.discovered_peers {
                let welcomed = self.welcomed_peers.get(peer_id).unwrap_or(&false);
                let status = if *welcomed {
                    "✅ welcomed"
                } else {
                    "⏳ not welcomed"
                };
                println!("   {} at {} ({})", peer_id, addr, status);
            }
        }
    }

    async fn send_welcome_to_new_peers(&mut self) {
        let new_peers: Vec<_> = self
            .discovered_peers
            .keys()
            .filter(|peer_id| !self.welcomed_peers.contains_key(peer_id))
            .cloned()
            .collect();

        for peer_id in new_peers {
            self.send_welcome_message(&peer_id).await;
        }
    }

    async fn send_welcome_to_all_peers(&mut self) {
        let all_peers: Vec<_> = self.discovered_peers.keys().cloned().collect();

        for peer_id in all_peers {
            self.send_welcome_message(&peer_id).await;
        }
    }

    async fn send_welcome_message(&mut self, peer_id: &PeerId) {
        let payload = json!({
            "action": "welcome",
            "message": format!("🎉 Welcome! This is {} greeting you!", self.name),
            "sender": self.name,
            "sender_peer_id": self.swarm.local_peer_id().to_string(),
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "greeting_type": "initial_welcome"
        });

        let anp_message = AnpMessage::new(
            self.name.clone(),
            peer_id.to_string(),
            payload,
            "welcome_signature".to_string(),
        );

        let request = AnpRequest(anp_message);

        self.swarm
            .behaviour_mut()
            .request_response
            .send_request(peer_id, request);
    }

    async fn broadcast_message(&mut self, message: &str) {
        if self.discovered_peers.is_empty() {
            println!("📭 No peers to send message to");
            return;
        }

        for peer_id in self.discovered_peers.keys() {
            let payload = json!({
                "action": "broadcast",
                "message": message,
                "sender": self.name,
                "timestamp": chrono::Utc::now().to_rfc3339()
            });

            let anp_message = AnpMessage::new(
                self.name.clone(),
                peer_id.to_string(),
                payload,
                "broadcast_signature".to_string(),
            );

            let request = AnpRequest(anp_message);

            self.swarm
                .behaviour_mut()
                .request_response
                .send_request(peer_id, request);
        }
    }

    async fn handle_swarm_event(&mut self, event: SwarmEvent<AgentEvent>) {
        match event {
            SwarmEvent::Behaviour(AgentEvent::RequestResponse(event)) => {
                self.handle_request_response_event(event).await;
            }
            SwarmEvent::Behaviour(AgentEvent::Mdns(event)) => {
                self.handle_mdns_event(event).await;
            }
            SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                println!("🔗 [{}] Connection established with {}", self.name, peer_id);
            }
            SwarmEvent::ConnectionClosed { peer_id, .. } => {
                println!("🔌 [{}] Connection closed with {}", self.name, peer_id);
                self.discovered_peers.remove(&peer_id);
                self.welcomed_peers.remove(&peer_id);
            }
            SwarmEvent::NewListenAddr { address, .. } => {
                println!("🎧 [{}] Now listening on {}", self.name, address);
            }
            SwarmEvent::IncomingConnection { .. } => {
                println!("📞 [{}] Incoming connection", self.name);
            }
            SwarmEvent::OutgoingConnectionError { peer_id, error, .. } => {
                if let Some(peer_id) = peer_id {
                    eprintln!(
                        "⚠️ [{}] Outgoing connection error to {}: {:?}",
                        self.name, peer_id, error
                    );
                }
            }
            SwarmEvent::IncomingConnectionError { error, .. } => {
                eprintln!("⚠️ [{}] Incoming connection error: {:?}", self.name, error);
            }
            other => {
                // Uncomment for more verbose logging
                // println!("⚙️ [{}] Other SwarmEvent: {:?}", self.name, other);
            }
        }
    }

    async fn handle_request_response_event(
        &mut self,
        event: request_response::Event<AnpRequest, AnpResponse>,
    ) {
        match event {
            request_response::Event::OutboundFailure {
                peer,
                error,
                request_id,
                ..
            } => {
                eprintln!(
                    "⚠️ [{}] Outbound failure to {}: {:?}",
                    self.name, peer, error
                );
                self.pending_requests.remove(&request_id);
            }
            request_response::Event::InboundFailure { peer, error, .. } => {
                eprintln!(
                    "⚠️ [{}] Inbound failure from {}: {:?}",
                    self.name, peer, error
                );
            }
            request_response::Event::ResponseSent { peer, .. } => {
                println!("📤 [{}] Response sent to {}", self.name, peer);
            }
            Event::Message { peer, message, .. } => {
                match message {
                    Message::Request {
                        request, channel, ..
                    } => {
                        let action = request
                            .0
                            .payload
                            .get("action")
                            .and_then(|v| v.as_str())
                            .unwrap_or("unknown");

                        match action {
                            "welcome" => {
                                let message = request
                                    .0
                                    .payload
                                    .get("message")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("No message");
                                println!(
                                    "🎉 [{}] Welcome received from {}: {}",
                                    self.name, request.0.from, message
                                );
                            }
                            "broadcast" => {
                                let message = request
                                    .0
                                    .payload
                                    .get("message")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("No message");
                                println!(
                                    "📢 [{}] Broadcast from {}: {}",
                                    self.name, request.0.from, message
                                );
                            }
                            _ => {
                                println!("📥 [{}] Request from {}: {}", self.name, peer, request);
                            }
                        }

                        // Always send an acknowledgment response
                        let response_payload = json!({
                            "action": "ack",
                            "message": format!("Message received by {}", self.name),
                            "original_action": action,
                            "timestamp": chrono::Utc::now().to_rfc3339()
                        });

                        let response_message = AnpMessage::new(
                            self.name.clone(),
                            request.0.from,
                            response_payload,
                            "ack_signature".to_string(),
                        );

                        let response = AnpResponse(response_message);

                        if let Err(e) = self
                            .swarm
                            .behaviour_mut()
                            .request_response
                            .send_response(channel, response)
                        {
                            eprintln!("❌ [{}] Failed to send response: {:?}", self.name, e);
                        }
                    }
                    Message::Response {
                        response,
                        request_id,
                    } => {
                        println!("✅ [{}] Response received: {}", self.name, response);
                        self.pending_requests.remove(&request_id);
                    }
                }
            }
        }
    }

    async fn handle_mdns_event(&mut self, event: mdns::Event) {
        match event {
            mdns::Event::Discovered(peers) => {
                for (peer, addr) in peers {
                    if peer != *self.swarm.local_peer_id() {
                        println!(
                            "🔎 [{}] Discovered new peer: {} at {}",
                            self.name, peer, addr
                        );

                        // Add to discovered peers
                        self.discovered_peers.insert(peer, addr.clone());

                        // Add address to request-response behavior
                        self.swarm
                            .behaviour_mut()
                            .request_response
                            .add_address(&peer, addr);

                        // The welcome message will be sent on the next discovery interval
                    }
                }
            }
            mdns::Event::Expired(expired) => {
                for (peer, addr) in expired {
                    println!("❌ [{}] Peer expired: {} at {}", self.name, peer, addr);
                    self.discovered_peers.remove(&peer);
                    self.welcomed_peers.remove(&peer);
                    self.swarm
                        .behaviour_mut()
                        .request_response
                        .remove_address(&peer, &addr);
                }
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();

    let (name, port) = if args.len() >= 3 {
        (args[1].clone(), args[2].parse::<u16>().unwrap_or(4001))
    } else {
        println!("Usage: {} <node_name> <port>", args[0]);
        println!("Example: {} Alice 4001", args[0]);
        std::process::exit(1);
    };

    let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);

    // Create and run the discovery node
    let mut node = DiscoveryNode::new(&name, &listen_addr).await?;
    node.run().await
}

// Helper function to create multiple nodes for testing
#[allow(dead_code)]
async fn run_multiple_nodes() -> Result<()> {
    println!("🚀 Starting multiple discovery nodes for testing...");

    let nodes = vec![("Alice", 4001), ("Bob", 4002), ("Charlie", 4003)];

    let mut handles = vec![];

    for (name, port) in nodes {
        let name = name.to_string();
        let handle = tokio::spawn(async move {
            let listen_addr = format!("/ip4/0.0.0.0/tcp/{}", port);
            let mut node = DiscoveryNode::new(&name, &listen_addr).await?;
            node.run().await
        });
        handles.push(handle);

        // Small delay to avoid port conflicts
        tokio::time::sleep(Duration::from_millis(100)).await;
    }

    // Wait for all nodes to complete
    for handle in handles {
        if let Err(e) = handle.await? {
            eprintln!("Node error: {:?}", e);
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::timeout;

    #[tokio::test]
    async fn test_node_creation() {
        let node = DiscoveryNode::new("TestNode", "/ip4/127.0.0.1/tcp/0").await;
        assert!(node.is_ok());

        let node = node.unwrap();
        assert_eq!(node.name, "TestNode");
        assert!(node.discovered_peers.is_empty());
        assert!(node.welcomed_peers.is_empty());
    }

    #[tokio::test]
    async fn test_two_nodes_discovery() {
        let mut node1 = DiscoveryNode::new("Node1", "/ip4/127.0.0.1/tcp/0")
            .await
            .unwrap();
        let mut node2 = DiscoveryNode::new("Node2", "/ip4/127.0.0.1/tcp/0")
            .await
            .unwrap();

        // Run both nodes for a short time to allow discovery
        let timeout_duration = Duration::from_secs(10);

        let result = timeout(timeout_duration, async {
            tokio::select! {
                _ = node1.run() => {},
                _ = node2.run() => {},
            }
        })
        .await;

        // Test should timeout, which is expected for this integration test
        assert!(result.is_err());
    }
}
