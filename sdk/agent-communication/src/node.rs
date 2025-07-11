use anyhow::Result;
use futures::StreamExt;
use libp2p::core::transport::dummy::DummyTransport;
use libp2p::request_response::{Event, Message};
use libp2p::{
    Multiaddr, PeerId, Swarm, Transport, core::upgrade, identity, mdns, noise, request_response,
    swarm::SwarmEvent, tcp, websocket, yamux,
};
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};

use crate::behaviour::{AgentBehaviour, AgentEvent};
use crate::handlers::handle_message;
use crate::messaging::{ANP_PROTOCOL, AnpCodec, AnpRequest, AnpResponse};

pub async fn run_node() -> Result<()> {
    // 1️⃣ Identity
    let id_keys = identity::Keypair::generate_ed25519();
    let peer_id = PeerId::from(id_keys.public());
    println!("\n🔑 Local Peer ID: {}\n", peer_id);

    // 2️⃣ Noise encryption
    let noise_config = noise::Config::new(&identity::Keypair::generate_ed25519());

    // 3️⃣ Transport - Updated for libp2p 0.56
    let tcp_transport = tcp::Config::new().nodelay(true);

    // let transport = websocket::Config::new(tcp_transport)
    //     .upgrade(upgrade::Version::V1)
    //     .authenticate(noise_config)
    //     .multiplex(yamux::Config::default())
    //     .boxed();
    let transport =
        websocket::Config::new(tcp::tokio::Transport::new(tcp::Config::default())).boxed();

    // 4️⃣ RequestResponse - Updated configuration
    let mut req_resp_config = request_response::Config::default();

    let protocols = std::iter::once((ANP_PROTOCOL, request_response::ProtocolSupport::Full));
    let request_response = request_response::Behaviour::new(protocols, req_resp_config);

    // 5️⃣ mDNS - Updated for libp2p 0.56
    let mdns = mdns::Behaviour::new(mdns::Config::default(), peer_id)?;
    println!("🌐 mDNS Discovery enabled.");

    // 6️⃣ Combined Behaviour
    let behaviour = AgentBehaviour {
        request_response,
        mdns,
    };

    // 7️⃣ Swarm
    // let mut swarm = SwarmBuilder::with_tokio_executor(transport, behaviour, peer_id).build();
    let mut swarm = Swarm::new(
        DummyTransport::new().boxed(),
        behaviour,
        peer_id,
        libp2p_swarm::Config::with_tokio_executor(),
    );

    // 8️⃣ Listen on all interfaces
    swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;

    // 9️⃣ Optional CLI Input
    println!("🟢 Agent Node running. Type anything to simulate user input.");
    let mut stdin = BufReader::new(tokio::io::stdin()).lines();

    // 🔟 Event loop
    loop {
        tokio::select! {
            line = stdin.next_line() => {
                if let Ok(Some(input)) = line {
                    println!("📥 [stdin] User input: {}", input);
                    // Optional: Handle CLI commands
                }
            }

            event = swarm.select_next_some() => {
                match event {
                    SwarmEvent::Behaviour(AgentEvent::RequestResponse(event)) => {
                        handle_request_response_event(event, &mut swarm).await;
                    }
                    SwarmEvent::Behaviour(AgentEvent::Mdns(event)) => {
                        handle_mdns_event(event, &mut swarm).await;
                    }
                    SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                        println!("🔗 Connection established with {}", peer_id);
                    }
                    SwarmEvent::ConnectionClosed { peer_id, .. } => {
                        println!("🔌 Connection closed with {}", peer_id);
                    }
                    SwarmEvent::NewListenAddr { address, .. } => {
                        println!("🎧 Listening on {}", address);
                    }
                    other => {
                        println!("⚙️ Other SwarmEvent: {:?}", other);
                    }
                }
            }
        }
    }
}

// 📌 Handle ANP messages
async fn handle_request_response_event(
    event: request_response::Event<AnpRequest, AnpResponse>,
    swarm: &mut libp2p::Swarm<AgentBehaviour>,
) {
    match event {
        request_response::Event::OutboundFailure { peer, error, .. } => {
            eprintln!("⚠️ Outbound failure to {}: {:?}", peer, error);
        }
        request_response::Event::InboundFailure { peer, error, .. } => {
            eprintln!("⚠️ Inbound failure from {}: {:?}", peer, error);
        }
        request_response::Event::ResponseSent { peer, .. } => {
            println!("📤 Response sent to {}", peer);
        }
        Event::Message {
            peer,
            connection_id,
            message,
        } => {
            match message {
                Message::Request {
                    request_id,
                    request,
                    channel,
                } => {
                    println!(
                        "📥 Request received from {}: {} with channel: {:?}",
                        peer, request, channel
                    );
                }
                Message::Response {
                    request_id,
                    response,
                } => {
                    println!(
                        "📤 Response received from {}: {} with request_id: {:?}",
                        peer, response, request_id
                    );
                    // Optional: Handle the response
                }
            }
        }
    }
}

// 📌 Handle mDNS discovery - Updated for libp2p 0.56
async fn handle_mdns_event(event: mdns::Event, swarm: &mut libp2p::Swarm<AgentBehaviour>) {
    match event {
        mdns::Event::Discovered(peers) => {
            for (peer, addr) in peers {
                println!("🔎 Discovered peer: {} at {:?}", peer, addr);
                swarm
                    .behaviour_mut()
                    .request_response
                    .add_address(&peer, addr);
            }
        }
        mdns::Event::Expired(expired) => {
            for (peer, addr) in expired {
                println!("❌ Expired peer: {} at {:?}", peer, addr);
                swarm
                    .behaviour_mut()
                    .request_response
                    .remove_address(&peer, &addr);
            }
        }
    }
}
