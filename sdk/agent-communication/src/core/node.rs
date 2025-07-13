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

use crate::data::AgentConfig;
use crate::messaging::{ANP_PROTOCOL, AnpCodec, AnpRequest, AnpResponse};
use crate::network::behaviour::{AgentBehaviour, AgentEvent};
use crate::protocol::anp::AnpMessage;
use crate::protocol::handlers::handle_message;

pub struct AgentNode {
    pub name: String,
    pub protocol: String, // Store the protocol in the node
    pub swarm: Swarm<AgentBehaviour>,
    pub discovered_peers: HashMap<PeerId, Multiaddr>,
    pub last_message_time: Instant,
    pub pending_requests: HashMap<OutboundRequestId, PeerId>,
}

impl AgentNode {
    /// Create a new AgentNode with simple configuration
    pub async fn new(name: &str, listen_addr: &str) -> Result<Self> {
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
        })
    }

    /// Create a new AgentNode from an AgentConfig
    pub async fn from_config(name: &str, config: AgentConfig) -> Result<Self> {
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

        // Use the ANP_PROTOCOL constant to avoid lifetime issues
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
        })
    }

    pub async fn run(&mut self) -> Result<()> {
        let mut message_interval = interval(Duration::from_secs(10));
        let mut stdin = BufReader::new(tokio::io::stdin()).lines();

        println!("🟢 {} is running", self.name);

        loop {
            tokio::select! {
                // Handle periodic message sending
                _ = message_interval.tick() => {
                    self.send_messages_to_peers().await;
                }

                // Handle user input
                line = stdin.next_line() => {
                    if let Ok(Some(input)) = line {
                        if input.trim() == "quit" || input.trim() == "exit" {
                            println!("👋 {} shutting down", self.name);
                            break;
                        }
                        println!("📥 [{}] User input: {}", self.name, input);
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

    async fn send_messages_to_peers(&mut self) {
        if self.discovered_peers.is_empty() {
            return;
        }

        // Send a message to each discovered peer
        for (peer_id, _addr) in &self.discovered_peers {
            let payload = json!({
                "action": "greeting",
                "message": format!("Hello from {}!", self.name),
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "sender": self.name
            });

            let anp_message = AnpMessage::new(
                self.name.clone(),
                peer_id.to_string(),
                payload,
                "signature_placeholder".to_string(),
            );

            let request = AnpRequest(anp_message);

            self.swarm
                .behaviour_mut()
                .request_response
                .send_request(peer_id, request);
        }

        self.last_message_time = Instant::now();
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
                println!("⚙️ [{}] Other SwarmEvent: {:?}", self.name, other);
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
                        println!(
                            "📥 [{}] Request received from {}: {}",
                            self.name, peer, request
                        );

                        // Handle the incoming message
                        handle_message(request.0.clone()).await;

                        // Send a response
                        let response_payload = json!({
                            "action": "response",
                            "message": format!("Response from {}", self.name),
                            "original_sender": request.0.from,
                            "timestamp": chrono::Utc::now().to_rfc3339()
                        });

                        let response_message = AnpMessage::new(
                            self.name.clone(),
                            request.0.from,
                            response_payload,
                            "response_signature".to_string(),
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
                            .add_address(&peer, addr);
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
                }
            }
        }
    }
}

// Keep the original run_node function for backward compatibility
pub async fn run_node() -> Result<()> {
    let mut node = AgentNode::new("DefaultNode", "/ip4/0.0.0.0/tcp/4001").await?;
    node.run().await
}
