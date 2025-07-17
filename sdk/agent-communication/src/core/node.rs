use anyhow::Result;
use futures::StreamExt;
use libp2p::ping::Failure;
use libp2p::request_response::{Event, Message, OutboundRequestId};
use libp2p::{
    Multiaddr, PeerId, Swarm, Transport, core::upgrade, gossipsub, identity, mdns, noise, ping,
    request_response, swarm::SwarmEvent, tcp, yamux,
};
use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};
use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;
use tokio::sync::{broadcast, mpsc};
use tokio::time::{Instant, interval};

use crate::data::AgentConfig;
use crate::messaging::{ANP_PROTOCOL, AnpRequest, AnpResponse};
use crate::network::behaviour::{AgentBehaviour, AgentEvent};
use crate::protocol::anp::AnpMessage;
use crate::protocol::handlers::handle_message;

// Event types that the AgentNode can emit (no libp2p types exposed)
#[derive(Debug, Clone)]
pub enum AgentNodeEvent {
    PeerDiscovered {
        peer_id: String,
        address: String,
    },
    PeerDisconnected {
        peer_id: String,
    },
    MessageReceived {
        from: String,
        message: AnpMessage,
    },
    MessageSent {
        to: String,
        message: AnpMessage,
    },
    ConnectionEstablished {
        peer_id: String,
    },
    ConnectionClosed {
        peer_id: String,
    },
    PingSuccess {
        peer_id: String,
        rtt: Duration,
    },
    PingFailure {
        peer_id: String,
    },
    GossipSubMessageReceived {
        topic: String,
        from: String,
        message: String,
        message_id: String,
    },
    TopicSubscribed {
        topic: String,
    },
    TopicUnsubscribed {
        topic: String,
    },
    PeerSubscribedToTopic {
        peer_id: String,
        topic: String,
    },
    PeerUnsubscribedFromTopic {
        peer_id: String,
        topic: String,
    },
    Error {
        description: String,
    },
}

pub struct AgentNode {
    pub name: String,
    pub protocol: String,
    pub swarm: Swarm<AgentBehaviour>,
    pub discovered_peers: HashMap<PeerId, Multiaddr>,
    pub last_message_time: Instant,
    pub pending_requests: HashMap<OutboundRequestId, PeerId>,

    // GossipSub management
    pub subscribed_topics: HashSet<String>,
    pub topic_peers: HashMap<String, HashSet<PeerId>>,

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
    PublishToTopic { topic: String, message: String },
    SubscribeToTopic { topic: String },
    UnsubscribeFromTopic { topic: String },
    GetPeers,
    GetTopics,
    GetTopicPeers { topic: String },
    Shutdown,
}

pub fn message_id_fn(message: &gossipsub::Message) -> gossipsub::MessageId {
    let mut s = DefaultHasher::new();
    message.data.hash(&mut s);
    gossipsub::MessageId::from(s.finish().to_string())
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
        let transport =
            tcp::tokio::Transport::new(tcp::Config::default().nodelay(true).listen_backlog(256))
                .upgrade(upgrade::Version::V1)
                .authenticate(noise::Config::new(&id_keys)?)
                .multiplex(
                    yamux::Config::default()
                        .set_max_num_streams(2 * 1024 * 1024)
                        .to_owned(),
                )
                .timeout(Duration::from_secs(20))
                .boxed();

        // 3️⃣ RequestResponse behavior
        let req_resp_config = request_response::Config::default()
            .with_request_timeout(Duration::from_secs(10))
            .with_max_concurrent_streams(2 * 1024 * 1024);

        let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
        let request_response = request_response::Behaviour::new(protocols, req_resp_config);

        // 4️⃣ mDNS for peer discovery
        let mdns = mdns::Behaviour::new(mdns::Config::default(), peer_id)?;

        // 5️⃣ Ping for connection keep-alive
        let ping = ping::Behaviour::new(ping::Config::new());

        // 6️⃣ GossipSub configuration
        let gossip_sub_config = gossipsub::ConfigBuilder::default()
            .heartbeat_interval(Duration::from_millis(700)) // How often to send heartbeat
            .mesh_n_low(16) // Lower bound for mesh network degree
            .mesh_n(32) // Target number of peers in mesh
            .mesh_n_high(64) // Upper bound for mesh network degree
            .history_length(64) // Number of heartbeat intervals to retain message IDs
            .history_gossip(32) // Number of past heartbeat intervals to gossip about
            .max_transmit_size(1024 * 1024) // Maximum size of messages to transmit
            .validation_mode(gossipsub::ValidationMode::Strict) // Validate messages
            .message_id_fn(message_id_fn) // Custom message ID function
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to build gossipsub config: {}", e))?;

        let mut gossipsub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(id_keys.clone()),
            gossip_sub_config,
        )
        .map_err(|e| anyhow::anyhow!("Failed to create gossipsub behavior: {}", e))?;

        // Subscribe to a default general topic
        let default_topic = gossipsub::IdentTopic::new("agent-network");
        gossipsub
            .subscribe(&default_topic)
            .map_err(|e| anyhow::anyhow!("Failed to subscribe to default topic: {}", e))?;

        // 7️⃣ Combined behavior
        let behaviour = AgentBehaviour {
            request_response,
            mdns,
            ping,
            gossipsub,
        };

        // 8️⃣ Create swarm
        let mut swarm = Swarm::new(
            transport,
            behaviour,
            peer_id,
            libp2p_swarm::Config::with_tokio_executor(),
        );

        // 9️⃣ Start listening
        let addr: Multiaddr = listen_addr.parse()?;
        swarm.listen_on(addr.clone())?;
        println!("🎧 {} listening on {}", name, addr);

        // Initialize subscribed topics with default topic
        let mut subscribed_topics = HashSet::new();
        subscribed_topics.insert("agent-network".to_string());

        Ok(Self {
            name: name.to_string(),
            protocol: ANP_PROTOCOL.to_string(),
            swarm,
            discovered_peers: HashMap::new(),
            last_message_time: Instant::now(),
            pending_requests: HashMap::new(),
            subscribed_topics,
            topic_peers: HashMap::new(),
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
        let transport =
            tcp::tokio::Transport::new(tcp::Config::default().nodelay(true).listen_backlog(256))
                .upgrade(upgrade::Version::V1)
                .authenticate(noise::Config::new(keypair)?)
                .multiplex(
                    yamux::Config::default()
                        .set_max_num_streams(2 * 1024 * 1024)
                        .to_owned(),
                )
                .timeout(Duration::from_secs(20))
                .boxed();

        // RequestResponse behavior with custom configuration
        let req_resp_config = request_response::Config::default()
            .with_request_timeout(Duration::from_secs(10))
            .with_max_concurrent_streams(2 * 1024 * 1024);

        let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
        let request_response = request_response::Behaviour::new(protocols, req_resp_config);

        // mDNS for peer discovery
        let mdns = mdns::Behaviour::new(mdns::Config::default(), config.peer_id)?;

        // Ping with custom interval
        let ping = ping::Behaviour::new(ping::Config::new().with_interval(Duration::from_secs(30)));

        // GossipSub configuration
        let gossip_sub_config = gossipsub::ConfigBuilder::default()
            .heartbeat_interval(Duration::from_millis(700))
            .mesh_n_low(16)
            .mesh_n(32)
            .mesh_n_high(64)
            .history_length(64)
            .history_gossip(32)
            .max_transmit_size(1024 * 1024)
            .validation_mode(gossipsub::ValidationMode::Strict)
            .message_id_fn(message_id_fn)
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to build gossipsub config: {}", e))?;

        let mut gossipsub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(keypair.clone()),
            gossip_sub_config,
        )
        .map_err(|e| anyhow::anyhow!("Failed to create gossipsub behavior: {}", e))?;

        // Subscribe to default topic
        let default_topic = gossipsub::IdentTopic::new("agent-network");
        gossipsub
            .subscribe(&default_topic)
            .map_err(|e| anyhow::anyhow!("Failed to subscribe to default topic: {}", e))?;

        // Combined behavior
        let behaviour = AgentBehaviour {
            request_response,
            mdns,
            ping,
            gossipsub,
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

        // Initialize subscribed topics with default topic
        let mut subscribed_topics = HashSet::new();
        subscribed_topics.insert("agent-network".to_string());

        Ok(Self {
            name: name.to_string(),
            protocol: config.protocol.clone(),
            swarm,
            discovered_peers: HashMap::new(),
            last_message_time: Instant::now(),
            pending_requests: HashMap::new(),
            subscribed_topics,
            topic_peers: HashMap::new(),
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

    /// Subscribe to a GossipSub topic
    pub fn subscribe_to_topic(&mut self, topic: &str) -> Result<()> {
        let topic_hash = gossipsub::IdentTopic::new(topic);

        match self.swarm.behaviour_mut().gossipsub.subscribe(&topic_hash) {
            Ok(_) => {
                self.subscribed_topics.insert(topic.to_string());
                println!("📡 [{}] Subscribed to topic: {}", self.name, topic);

                let _ = self.event_tx.send(AgentNodeEvent::TopicSubscribed {
                    topic: topic.to_string(),
                });

                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to subscribe to topic {}: {:?}", topic, e);
                eprintln!("❌ [{}] {}", self.name, error_msg);

                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: error_msg.clone(),
                });

                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Unsubscribe from a GossipSub topic
    pub fn unsubscribe_from_topic(&mut self, topic: &str) -> Result<()> {
        let topic_hash = gossipsub::IdentTopic::new(topic);

        match self
            .swarm
            .behaviour_mut()
            .gossipsub
            .unsubscribe(&topic_hash)
        {
            true => {
                self.subscribed_topics.remove(topic);
                self.topic_peers.remove(topic);
                println!("📡 [{}] Unsubscribed from topic: {}", self.name, topic);

                let _ = self.event_tx.send(AgentNodeEvent::TopicUnsubscribed {
                    topic: topic.to_string(),
                });

                Ok(())
            }
            false => {
                let error_msg = format!("Failed to unsubscribe from topic {}", topic);
                eprintln!("❌ [{}] {}", self.name, error_msg);

                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: error_msg.clone(),
                });

                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Publish a message to a GossipSub topic
    pub fn publish_to_topic(&mut self, topic: &str, message: &str) -> Result<()> {
        let topic_hash = gossipsub::IdentTopic::new(topic);

        // Create a structured message with metadata
        let message_data = json!({
            "sender": self.name,
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "content": message,
            "message_type": "gossipsub"
        });

        let message_bytes = serde_json::to_vec(&message_data)
            .map_err(|e| anyhow::anyhow!("Failed to serialize message: {}", e))?;

        match self
            .swarm
            .behaviour_mut()
            .gossipsub
            .publish(topic_hash, message_bytes)
        {
            Ok(message_id) => {
                println!(
                    "📢 [{}] Published to {}: {} (ID: {})",
                    self.name, topic, message, message_id
                );
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to publish to topic {}: {:?}", topic, e);
                eprintln!("❌ [{}] {}", self.name, error_msg);

                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: error_msg.clone(),
                });

                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Send a message to a specific peer
    pub fn send_message_to_peer(&mut self, peer_id: &str, payload: Value) -> Result<()> {
        // Convert string peer_id back to PeerId
        let peer_id = peer_id
            .parse::<PeerId>()
            .map_err(|e| anyhow::anyhow!("Invalid peer ID: {}", e))?;

        let anp_message = AnpMessage::new(
            self.name.clone(),
            peer_id.to_string(),
            payload,
            "signature_placeholder".to_string(),
        );

        let request = AnpRequest(anp_message.clone());

        let request_id = self
            .swarm
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
        self.discovered_peers
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }

    /// Get list of subscribed topics
    pub fn get_subscribed_topics(&self) -> Vec<String> {
        self.subscribed_topics.iter().cloned().collect()
    }

    /// Get peers subscribed to a specific topic
    pub fn get_topic_peers(&self, topic: &str) -> Vec<String> {
        self.topic_peers
            .get(topic)
            .map(|peers| peers.iter().map(|p| p.to_string()).collect())
            .unwrap_or_default()
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
                        AgentCommand::PublishToTopic { topic, message } => {
                            if let Err(e) = self.publish_to_topic(&topic, &message) {
                                let _ = self.event_tx.send(AgentNodeEvent::Error {
                                    description: format!("Failed to publish to topic: {:?}", e),
                                });
                            }
                        }
                        AgentCommand::SubscribeToTopic { topic } => {
                            if let Err(e) = self.subscribe_to_topic(&topic) {
                                let _ = self.event_tx.send(AgentNodeEvent::Error {
                                    description: format!("Failed to subscribe to topic: {:?}", e),
                                });
                            }
                        }
                        AgentCommand::UnsubscribeFromTopic { topic } => {
                            if let Err(e) = self.unsubscribe_from_topic(&topic) {
                                let _ = self.event_tx.send(AgentNodeEvent::Error {
                                    description: format!("Failed to unsubscribe from topic: {:?}", e),
                                });
                            }
                        }
                        AgentCommand::GetPeers => {
                            // Peers can be accessed via get_peers() method
                        }
                        AgentCommand::GetTopics => {
                            // Topics can be accessed via get_subscribed_topics() method
                        }
                        AgentCommand::GetTopicPeers { topic } => {
                            // Topic peers can be accessed via get_topic_peers() method
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

                    // Also publish heartbeat to default topic
                    let _ = self.publish_to_topic("agent-network",
                        &format!("Heartbeat from {}", self.name));
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

        println!("🟢 {} is running", self.name);

        loop {
            tokio::select! {
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

                    // Also publish heartbeat to default topic
                    let _ = self.publish_to_topic("agent-network",
                        &format!("Heartbeat from {}", self.name));
                }

                // Handle swarm events
                event = self.swarm.select_next_some() => {
                    self.handle_swarm_event(event).await;
                }
            }
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
            SwarmEvent::Behaviour(AgentEvent::Ping(event)) => {
                self.handle_ping_event(event).await;
            }
            SwarmEvent::Behaviour(AgentEvent::GossipSub(event)) => {
                self.handle_gossipsub_event(event).await;
            }
            SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                println!("🔗 [{}] Connection established with {}", self.name, peer_id);
                let _ = self.event_tx.send(AgentNodeEvent::ConnectionEstablished {
                    peer_id: peer_id.to_string(),
                });
            }
            SwarmEvent::ConnectionClosed { peer_id, .. } => {
                println!("🔌 [{}] Connection closed with {}", self.name, peer_id);
                self.discovered_peers.remove(&peer_id);

                // Clean up topic peer tracking
                for peers in self.topic_peers.values_mut() {
                    peers.remove(&peer_id);
                }

                let _ = self.event_tx.send(AgentNodeEvent::ConnectionClosed {
                    peer_id: peer_id.to_string(),
                });
                let _ = self.event_tx.send(AgentNodeEvent::PeerDisconnected {
                    peer_id: peer_id.to_string(),
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
                    eprintln!(
                        "⚠️ [{}] Outgoing connection error to {}: {:?}",
                        self.name, peer_id, error
                    );
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

    async fn handle_gossipsub_event(&mut self, event: gossipsub::Event) {
        match event {
            gossipsub::Event::Message {
                propagation_source,
                message_id,
                message,
            } => {
                let topic = message.topic.to_string();
                let from = propagation_source.to_string();

                // Try to parse the message as JSON
                match serde_json::from_slice::<Value>(&message.data) {
                    Ok(parsed_message) => {
                        let content = parsed_message
                            .get("content")
                            .and_then(|v| v.as_str())
                            .unwrap_or_else(|| {
                                std::str::from_utf8(&message.data).unwrap_or("Invalid UTF-8")
                            });

                        let sender = parsed_message
                            .get("sender")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Unknown");

                        println!(
                            "📻 [{}] GossipSub message from {}: {} (topic: {}, id: {})",
                            self.name, sender, content, topic, message_id
                        );

                        let _ = self
                            .event_tx
                            .send(AgentNodeEvent::GossipSubMessageReceived {
                                topic: topic.clone(),
                                from: sender.to_string(),
                                message: content.to_string(),
                                message_id: message_id.to_string(),
                            });
                    }
                    Err(_) => {
                        // Fallback to raw message
                        let content = std::str::from_utf8(&message.data).unwrap_or("Invalid UTF-8");

                        println!(
                            "📻 [{}] GossipSub raw message from {}: {} (topic: {}, id: {})",
                            self.name, from, content, topic, message_id
                        );

                        let _ = self
                            .event_tx
                            .send(AgentNodeEvent::GossipSubMessageReceived {
                                topic: topic.clone(),
                                from: from.clone(),
                                message: content.to_string(),
                                message_id: message_id.to_string(),
                            });
                    }
                }
            }
            gossipsub::Event::Subscribed { peer_id, topic } => {
                let topic_str = topic.to_string();
                println!(
                    "🔔 [{}] Peer {} subscribed to topic: {}",
                    self.name, peer_id, topic_str
                );

                // Track peer subscription
                self.topic_peers
                    .entry(topic_str.clone())
                    .or_insert_with(HashSet::new)
                    .insert(peer_id);

                let _ = self.event_tx.send(AgentNodeEvent::PeerSubscribedToTopic {
                    peer_id: peer_id.to_string(),
                    topic: topic_str,
                });
            }
            gossipsub::Event::Unsubscribed { peer_id, topic } => {
                let topic_str = topic.to_string();
                println!(
                    "🔕 [{}] Peer {} unsubscribed from topic: {}",
                    self.name, peer_id, topic_str
                );

                // Remove peer from topic tracking
                if let Some(peers) = self.topic_peers.get_mut(&topic_str) {
                    peers.remove(&peer_id);
                    if peers.is_empty() {
                        self.topic_peers.remove(&topic_str);
                    }
                }

                let _ = self
                    .event_tx
                    .send(AgentNodeEvent::PeerUnsubscribedFromTopic {
                        peer_id: peer_id.to_string(),
                        topic: topic_str,
                    });
            }
            gossipsub::Event::GossipsubNotSupported { peer_id } => {
                println!(
                    "⚠️ [{}] Peer {} does not support GossipSub",
                    self.name, peer_id
                );

                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Peer {} does not support GossipSub", peer_id),
                });
            }

            gossipsub::Event::SlowPeer { peer_id, .. } => {
                println!("⚠️ [{}] Peer {} is slow", self.name, peer_id);
            }
        }
    }

    async fn handle_ping_event(&mut self, event: ping::Event) {
        match event {
            ping::Event {
                peer,
                connection: _,
                result: res,
            } => {
                match res {
                    Ok(rtt) => {
                        println!(
                            "🏓 [{}] Ping success to {} (RTT: {:?})",
                            self.name, peer, rtt
                        );
                        let _ = self.event_tx.send(AgentNodeEvent::PingSuccess {
                            peer_id: peer.to_string(),
                            rtt,
                        });
                    }
                    Err(err) => match err {
                        ping::Failure::Timeout => {
                            println!("⏰ [{}] Ping timeout to {}", self.name, peer);
                            let _ = self.event_tx.send(AgentNodeEvent::PingFailure {
                                peer_id: peer.to_string(),
                            });
                        }
                        ping::Failure::Unsupported => {
                            println!("❌ [{}] Ping protocol not supported to {}", self.name, peer);
                            let _ = self.event_tx.send(AgentNodeEvent::PingFailure {
                                peer_id: peer.to_string(),
                            });
                        }
                        ping::Failure::Other { error: failure } => {
                            println!("❌ [{}] Ping failure to {}: {:?}", self.name, peer, failure);
                            let _ = self.event_tx.send(AgentNodeEvent::PingFailure {
                                peer_id: peer.to_string(),
                            });
                        }
                    },
                };
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
                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Message send failure to {}: {:?}", peer, error),
                });
            }
            request_response::Event::InboundFailure { peer, error, .. } => {
                eprintln!(
                    "⚠️ [{}] Inbound failure from {}: {:?}",
                    self.name, peer, error
                );
                let _ = self.event_tx.send(AgentNodeEvent::Error {
                    description: format!("Message receive failure from {}: {:?}", peer, error),
                });
            }
            request_response::Event::ResponseSent { peer, .. } => {
                println!("📤 [{}] Response sent to {}", self.name, peer);
            }
            Event::Message { peer, message, .. } => {
                match message {
                    Message::Request {
                        request, channel, ..
                    } => {
                        println!(
                            "📥 [{}] Request received from {}: {}",
                            self.name, peer, request
                        );

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
                    Message::Response {
                        response,
                        request_id,
                    } => {
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

                    // Clean up topic peer tracking
                    for peers in self.topic_peers.values_mut() {
                        peers.remove(&peer);
                    }

                    self.swarm
                        .behaviour_mut()
                        .request_response
                        .remove_address(&peer, &addr);

                    // Emit peer disconnected event
                    let _ = self.event_tx.send(AgentNodeEvent::PeerDisconnected {
                        peer_id: peer.to_string(),
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
