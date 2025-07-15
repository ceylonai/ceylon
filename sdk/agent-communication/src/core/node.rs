use anyhow::Result;
use futures::StreamExt;
use libp2p::request_response::{Event, Message, OutboundRequestId};
use libp2p::{
    core::upgrade, identity, mdns, noise, request_response, swarm::SwarmEvent, tcp, yamux,
    Multiaddr, PeerId, Swarm, Transport,
};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::Duration;
use tokio::sync::{broadcast, mpsc};
use tokio::time::{interval, Instant};

use crate::data::AgentConfig;
use crate::messaging::{AnpRequest, AnpResponse, ANP_PROTOCOL};
use crate::network::behaviour::{AgentBehaviour, AgentEvent};
use crate::protocol::anp::AnpMessage;
use crate::protocol::handlers::handle_message;

// Event types that the AgentNode can emit (no libp2p types exposed)
#[derive(Debug, Clone)]
pub enum AgentNodeEvent {
    PeerDiscovered { peer_id: String, address: String },
    PeerDisconnected { peer_id: String },
    MessageReceived { from: String, message: AnpMessage },
    MessageSent { to: String, message: AnpMessage },
    ConnectionEstablished { peer_id: String },
    ConnectionClosed { peer_id: String },
    Error { description: String },
}

pub struct AgentNode {
    pub name: String,
    pub protocol: String,
    pub swarm: Swarm<AgentBehaviour>,
    pub discovered_peers: HashMap<PeerId, Multiaddr>,
    pub last_message_time: Instant,
    pub pending_requests: HashMap<OutboundRequestId, PeerId>,

    // Event broadcasting
    pub event_tx: broadcast::Sender<AgentNodeEvent>,

    // Command receiving (for external control)
    pub command_rx: Option<mpsc::UnboundedReceiver<AgentCommand>>,
}

// Commands that can be sent to the AgentNode (no libp2p types)
#[derive(Debug)]
pub enum AgentCommand {
    SendMessage { to: String, payload: Value },
    BroadcastMessage { payload: Value },
    GetPeers,
    Shutdown,
}

impl AgentNode {
    /// Create a new AgentNode with simple configuration and event broadcasting
    pub async fn new(name: &str, listen_addr: &str) -> Result<Self> {
        let (event_tx, _) = broadcast::channel(1000);

        // 1️⃣ Identity
        let id_keys = identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(id_keys.public());
        println!("🔑 {} Peer ID: {}", name, peer_id);

        // 2️⃣ Create transport
        let transport = tcp::tokio::Transport::new(tcp::Config::default().nodelay(true))
            .upgrade(upgrade::Version::V1)
            .authenticate(noise::Config::new(&id_keys)?)
            .multiplex(yamux::Config::default())
            .boxed();

        // 3️⃣ RequestResponse behavior
        let mut req_resp_config = request_response::Config::default();
        req_resp_config.set_request_timeout(Duration::from_secs(10));

        let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
        let request_response = request_response::Behaviour::new(protocols, req_resp_config);

        // 4️⃣ mDNS for peer discovery
        let mdns = mdns::Behaviour::new(mdns::Config::default(), peer_id)?;

        // 5️⃣ Combined behavior
        let behaviour = AgentBehaviour {
            request_response,
            mdns,
        };

        // 6️⃣ Create swarm
        let mut swarm = Swarm::new(
            transport,
            behaviour,
            peer_id,
            libp2p_swarm::Config::with_tokio_executor(),
        );

        // 7️⃣ Start listening
        let addr: Multiaddr = listen_addr.parse()?;
        swarm.listen_on(addr.clone())?;
        println!("🎧 {} listening on {}", name, addr);

        Ok(Self {
            name: name.to_string(),
            protocol: ANP_PROTOCOL.to_string(),
            swarm,
            discovered_peers: HashMap::new(),
            last_message_time: Instant::now(),
            pending_requests: HashMap::new(),
            event_tx,
            command_rx: None,
        })
    }

    /// Create a new AgentNode from an AgentConfig with event broadcasting
    pub async fn from_config(name: &str, config: AgentConfig) -> Result<Self> {
        let (event_tx, _) = broadcast::channel(1000);

        let keypair = config
            .keypair
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("AgentConfig must have a keypair"))?;

        println!("🔑 {} Peer ID: {}", name, config.peer_id);

        // Create transport with the provided keypair
        let transport = tcp::tokio::Transport::new(tcp::Config::default().nodelay(true))
            .upgrade(upgrade::Version::V1)
            .authenticate(noise::Config::new(keypair)?)
            .multiplex(yamux::Config::default())
            .boxed();

        // RequestResponse behavior with custom configuration
        let mut req_resp_config = request_response::Config::default();
        // req_resp_config.set_request_timeout(Duration::from_secs(config.request_timeout_secs));
        // req_resp_config.set_connection_keep_alive(Duration::from_secs(config.keep_alive_secs));

        let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
        let request_response = request_response::Behaviour::new(protocols, req_resp_config);

        // mDNS for peer discovery
        let mdns = mdns::Behaviour::new(mdns::Config::default(), config.peer_id)?;

        // Combined behavior
        let behaviour = AgentBehaviour {
            request_response,
            mdns,
        };

        // Create swarm
        let mut swarm = Swarm::new(
            transport,
            behaviour,
            config.peer_id,
            libp2p_swarm::Config::with_tokio_executor(),
        );

        // Start listening on all configured addresses
        for addr in &config.listen_addrs {
            swarm.listen_on(addr.clone())?;
            println!("🎧 {} listening on {}", name, addr);
        }

        Ok(Self {
            name: name.to_string(),
            protocol: config.protocol.clone(),
            swarm,
            discovered_peers: HashMap::new(),
            last_message_time: Instant::now(),
            pending_requests: HashMap::new(),
            event_tx,
            command_rx: None,
        })
    }

    /// Subscribe to events from this node
    pub fn subscribe_events(&self) -> broadcast::Receiver<AgentNodeEvent> {
        self.event_tx.subscribe()
    }

    /// Set up command channel for external control
    pub fn setup_command_channel(&mut self) -> mpsc::UnboundedSender<AgentCommand> {
        let (tx, rx) = mpsc::unbounded_channel();
        self.command_rx = Some(rx);
        tx
    }

    /// Send a message to a specific peer
    pub fn send_message_to_peer(&mut self, peer_id: &str, payload: Value) -> Result<()> {
        // Convert string peer_id back to PeerId
        let peer_id = peer_id.parse::<PeerId>()
            .map_err(|e| anyhow::anyhow!("Invalid peer ID: {}", e))?;

        let anp_message = AnpMessage::new(
            self.name.clone(),
            peer_id.to_string(),
            payload,
            "signature_placeholder".to_string(),
        );

        let request = AnpRequest(anp_message.clone());

        let request_id = self.swarm
            .behaviour_mut()
            .request_response
            .send_request(&peer_id, request);

        self.pending_requests.insert(request_id, peer_id);

        // Emit event
        let _ = self.event_tx.send(AgentNodeEvent::MessageSent {
            to: peer_id.to_string(),
            message: anp_message,
        });

        Ok(())
    }

    /// Broadcast a message to all discovered peers
    pub fn broadcast_message(&mut self, payload: Value) -> Result<()> {
        let peer_ids: Vec<PeerId> = self.discovered_peers.keys().cloned().collect();

        for peer_id in peer_ids {
            if let Err(e) = self.send_message_to_peer(&peer_id.to_string(), payload.clone()) {
                eprintln!("Failed to send message to {}: {:?}", peer_id, e);
            }
        }

        Ok(())
    }

    /// Get list of discovered peers (returns strings, not libp2p types)
    pub fn get_peers(&self) -> Vec<(String, String)> {
        self.discovered_peers.iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }

    /// Get local peer ID as string
    pub fn local_peer_id(&self) -> String {
        self.swarm.local_peer_id().to_string()
    }

    /// Run the agent node with event processing
    pub async fn run(&mut self) -> Result<()> {
        let mut heartbeat_interval = interval(Duration::from_secs(30));

        println!("🟢 {} is running", self.name);

        loop {
            tokio::select! {
                // Handle external commands
                Some(command) = async {
                    if let Some(ref mut rx) = self.command_rx {
                        rx.recv().await
                    } else {
                        std::future::pending().await
                    }
                } => {
                    match command {
                        AgentCommand::SendMessage { to, payload } => {
                            if let Err(e) = self.send_message_to_peer(&to, payload) {
                                let _ = self.event_tx.send(AgentNodeEvent::Error {
                                    description: format!("Failed to send message: {:?}", e),
                                });
                            }
                        }
                        AgentCommand::BroadcastMessage { payload } => {
                            if let Err(e) = self.broadcast_message(payload) {
                                let _ = self.event_tx.send(AgentNodeEvent::Error {
                                    description: format!("Failed to broadcast message: {:?}", e),
                                });
                            }
                        }
                        AgentCommand::GetPeers => {
                            // Peers can be accessed via get_peers() method
                        }
                        AgentCommand::Shutdown => {
                            println!("👋 {} shutting down", self.name);
                            break;
                        }
                    }
                }

                // Send periodic heartbeat
                _ = heartbeat_interval.tick() => {
                    if !self.discovered_peers.is_empty() {
                        let heartbeat = json!({
                            "action": "heartbeat",
                            "timestamp": chrono::Utc::now().to_rfc3339(),
                            "sender": self.name
                        });
                        let _ = self.broadcast_message(heartbeat);
                    }
                }

                // Handle swarm events
                event = self.swarm.select_next_some() => {
                    self.handle_swarm_event(event).await;
                }
            }
        }

        Ok(())
    }

    /// Run without external command processing (simpler version)
    pub async fn run_simple(&mut self) -> Result<()> {
        let mut heartbeat_interval = interval(Duration::from_secs(30));
        let mut ping_interval = interval(Duration::from_secs(60)); // Ping every minute

        println!("🟢 {} is running", self.name);

        loop {
            tokio::select! {
                // Send periodic pings to keep connections alive
                _ = ping_interval.tick() => {
                    self.send_ping_to_all_peers().await;
                }

                // Send periodic heartbeat
                _ = heartbeat_interval.tick() => {
                    if !self.discovered_peers.is_empty() {
                        let heartbeat = json!({
                            "action": "heartbeat",
                            "timestamp": chrono::Utc::now().to_rfc3339(),
                            "sender": self.name,
                            "keep_alive": true
                        });
                        let _ = self.broadcast_message(heartbeat);
                    }
                }

                // Handle swarm events
                event = self.swarm.select_next_some() => {
                    self.handle_swarm_event(event).await;
                }
            }
        }
    }

    // Fix 3: Add ping method to maintain connections
    async fn send_ping_to_all_peers(&mut self) {
        for peer_id in self.discovered_peers.keys().cloned().collect::<Vec<_>>() {
            let ping_payload = json!({
                "action": "ping",
                "sender": self.name,
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "ping_id": uuid::Uuid::new_v4().to_string()
            });

            let anp_message = AnpMessage::new(
                self.name.clone(),
                peer_id.to_string(),
                ping_payload,
                "ping_signature".to_string(),
            );

            let request = AnpRequest(anp_message);

            // Send ping but don't wait for response
            let request_id = self.swarm
                .behaviour_mut()
                .request_response
                .send_request(&peer_id, request);

            self.pending_requests.insert(request_id, peer_id);
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
                let _ = self.event_tx.send(AgentNodeEvent::ConnectionEstablished {
                    peer_id: peer_id.to_string()
                });
            }
            SwarmEvent::ConnectionClosed { peer_id, .. } => {
                println!("🔌 [{}] Connection closed with {}", self.name, peer_id);
                self.discovered_peers.remove(&peer_id);
                let _ = self.event_tx.send(AgentNodeEvent::ConnectionClosed {
                    peer_id: peer_id.to_string()
                });
                let _ = self.event_tx.send(AgentNodeEvent::PeerDisconnected {
                    peer_id: peer_id.to_string()
                });
            }
            SwarmEvent::NewListenAddr { address, .. } => {
                println!("🎧 [{}] Now listening on {}", self.name, address);
            }
            SwarmEvent::IncomingConnection { .. } => {
                // Connection details will be handled in ConnectionEstablished
            }
            SwarmEvent::OutgoingConnectionError { peer_id, error, .. } => {
                if let Some(peer_id) = peer_id {
                    eprintln!("⚠️ [{}] Outgoing connection error to {}: {:?}", self.name, peer_id, error);
                    let _ = self.event_tx.send(AgentNodeEvent::Error {
                        description: format!("Connection error to {}: {:?}", peer_id, error),
                    });
                }
            }
            SwarmEvent::IncomingConnectionError { error, .. } => {
                eprintln!("⚠️ [{}] Incoming connection error: {:?}", self.name, error);
                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Incoming connection error: {:?}", error),
                });
            }
            _ => {
                // Other events can be logged if needed
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
                eprintln!("⚠️ [{}] Outbound failure to {}: {:?}", self.name, peer, error);
                self.pending_requests.remove(&request_id);
                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Message send failure to {}: {:?}", peer, error),
                });
            }
            request_response::Event::InboundFailure { peer, error, .. } => {
                eprintln!("⚠️ [{}] Inbound failure from {}: {:?}", self.name, peer, error);
                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Message receive failure from {}: {:?}", peer, error),
                });
            }
            request_response::Event::ResponseSent { peer, .. } => {
                println!("📤 [{}] Response sent to {}", self.name, peer);
            }
            Event::Message { peer, message, .. } => {
                match message {
                    Message::Request { request, channel, .. } => {
                        println!("📥 [{}] Request received from {}: {}", self.name, peer, request);

                        // Emit message received event
                        let _ = self.event_tx.send(AgentNodeEvent::MessageReceived {
                            from: peer.to_string(),
                            message: request.0.clone(),
                        });

                        // Handle the incoming message
                        handle_message(request.0.clone()).await;

                        // Send acknowledgment response
                        let response_payload = json!({
                            "action": "ack",
                            "message": format!("Message acknowledged by {}", self.name),
                            "original_sender": request.0.from,
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
                    Message::Response { response, request_id } => {
                        println!("📤 [{}] Response received: {}", self.name, response);
                        self.pending_requests.remove(&request_id);

                        // Emit message received event for responses too
                        let _ = self.event_tx.send(AgentNodeEvent::MessageReceived {
                            from: peer.to_string(),
                            message: response.0.clone(),
                        });

                        // Handle the response
                        handle_message(response.0).await;
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
                        println!("🔎 [{}] Discovered peer: {} at {}", self.name, peer, addr);
                        self.discovered_peers.insert(peer, addr.clone());

                        self.swarm
                            .behaviour_mut()
                            .request_response
                            .add_address(&peer, addr.clone());

                        // Emit peer discovered event
                        let _ = self.event_tx.send(AgentNodeEvent::PeerDiscovered {
                            peer_id: peer.to_string(),
                            address: addr.to_string(),
                        });
                    }
                }
            }
            mdns::Event::Expired(expired) => {
                for (peer, addr) in expired {
                    println!("❌ [{}] Expired peer: {} at {}", self.name, peer, addr);
                    self.discovered_peers.remove(&peer);

                    self.swarm
                        .behaviour_mut()
                        .request_response
                        .remove_address(&peer, &addr);

                    // Emit peer disconnected event
                    let _ = self.event_tx.send(AgentNodeEvent::PeerDisconnected {
                        peer_id: peer.to_string()
                    });
                }
            }
        }
    }
    async fn handle_connection_closed(&mut self, peer_id: &PeerId) {
        println!("🔌 [{}] Connection closed with {}", self.name, peer_id);

        // Keep the peer in discovered_peers for potential reconnection
        // Don't remove it immediately

        // Schedule a reconnection attempt
        self.schedule_reconnect(peer_id.clone()).await;
    }

    async fn schedule_reconnect(&mut self, peer_id: PeerId) {
        if let Some(addr) = self.discovered_peers.get(&peer_id) {
            let addr = addr.clone();
            println!("📞 [{}] Scheduling reconnect to {}", self.name, peer_id);

            // Re-add the address to trigger reconnection
            self.swarm
                .behaviour_mut()
                .request_response
                .add_address(&peer_id, addr);
        }
    }
}

// Keep the original run_node function for backward compatibility
pub async fn run_node() -> Result<()> {
    let mut node = AgentNode::new("DefaultNode", "/ip4/0.0.0.0/tcp/4001").await?;
    node.run_simple().await
}