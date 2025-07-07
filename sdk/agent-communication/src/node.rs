use libp2p::{
    identity::{self, Keypair},
    PeerId, Swarm, noise,
    tcp, websocket,
    yamux,
    swarm::{SwarmEvent, NetworkBehaviour},
    request_response::{self, Event as RequestResponseEvent, Config, ProtocolSupport},
    mdns::{self, Event as MdnsEvent},
    core::upgrade,
    Transport,
    multiaddr::Protocol,
};

use crate::messaging::{AnpCodec, AnpRequest, AnpResponse, ANP_PROTOCOL};
use crate::handlers::handle_message;
use anyhow::Result;
use tokio::io::AsyncBufReadExt;

#[derive(NetworkBehaviour)]
#[behaviour(out_event = "MyBehaviourEvent")]
pub struct MyBehaviour {
    request_response: request_response::Behaviour<AnpCodec>,
    mdns: mdns::tokio::Behaviour,
}

#[derive(Debug)]
pub enum MyBehaviourEvent {
    RequestResponse(RequestResponseEvent<AnpRequest, AnpResponse>),
    Mdns(MdnsEvent),
}

impl From<RequestResponseEvent<AnpRequest, AnpResponse>> for MyBehaviourEvent {
    fn from(event: RequestResponseEvent<AnpRequest, AnpResponse>) -> Self {
        MyBehaviourEvent::RequestResponse(event)
    }
}

impl From<MdnsEvent> for MyBehaviourEvent {
    fn from(event: MdnsEvent) -> Self {
        MyBehaviourEvent::Mdns(event)
    }
}

pub async fn run_node() -> Result<()> {
    // Identity
    let id_keys = identity::Keypair::generate_ed25519();
    let peer_id = PeerId::from(id_keys.public());
    println!("Local Peer ID: {:?}", peer_id);

    // Transport
    let noise_keys = noise::Config::new(&id_keys)?;
    let transport = websocket::WsConfig::new(tcp::Config::new().nodelay(true))
        .upgrade(upgrade::Version::V1)
        .authenticate(noise_keys)
        .multiplex(yamux::Config::default())
        .boxed();

    // Protocol
    let mut cfg = Config::default();
    cfg = cfg.with_request_timeout(std::time::Duration::from_secs(10));

    let protocols = std::iter::once((ANP_PROTOCOL, ProtocolSupport::Full));
    let request_response = request_response::Behaviour::new(protocols, cfg);

    // mDNS
    let mdns = mdns::tokio::Behaviour::new(mdns::Config::default(), peer_id)?;

    // Combined Behaviour
    let behaviour = MyBehaviour {
        request_response,
        mdns,
    };

    // Swarm
    let mut swarm = Swarm::new(transport, behaviour, peer_id);

    // Listen on all interfaces
    swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;
    swarm.listen_on("/ip4/0.0.0.0/tcp/0/ws".parse()?)?;

    // Event Loop
    let stdin = tokio::io::BufReader::new(tokio::io::stdin()).lines();

    tokio::pin!(stdin);

    loop {
        tokio::select! {
            line = stdin.next_line() => {
                if let Ok(Some(line)) = line {
                    println!("User Input: {}", line);
                    // TODO: parse input and send message
                }
            }
            event = swarm.select_next_some() => match event {
                SwarmEvent::Behaviour(MyBehaviourEvent::RequestResponse(event)) => {
                    match event {
                        RequestResponseEvent::Message { message, .. } => {
                            match message {
                                request_response::Message::Request { request, channel, .. } => {
                                    println!("Received request: {:?}", request);
                                    handle_message(request.0).await;
                                    let response = AnpResponse(request.0);
                                    let _ = swarm.behaviour_mut().request_response.send_response(channel, response);
                                }
                                request_response::Message::Response { response, .. } => {
                                    println!("Received response: {:?}", response);
                                }
                            }
                        }
                        RequestResponseEvent::OutboundFailure { peer, error, .. } => {
                            println!("OutboundFailure to {:?}: {:?}", peer, error);
                        }
                        RequestResponseEvent::InboundFailure { peer, error, .. } => {
                            println!("InboundFailure from {:?}: {:?}", peer, error);
                        }
                        RequestResponseEvent::ResponseSent { peer, .. } => {
                            println!("Response sent to {:?}", peer);
                        }
                        _ => {}
                    }
                }
                SwarmEvent::Behaviour(MyBehaviourEvent::Mdns(event)) => {
                    match event {
                        MdnsEvent::Discovered(peers) => {
                            for (peer_id, addr) in peers {
                                println!("Discovered peer {:?} at {:?}", peer_id, addr);
                                swarm.behaviour_mut().request_response.add_address(&peer_id, addr);
                            }
                        }
                        MdnsEvent::Expired(expired) => {
                            for (peer_id, addr) in expired {
                                println!("Expired peer {:?} at {:?}", peer_id, addr);
                                swarm.behaviour_mut().request_response.remove_address(&peer_id, &addr);
                            }
                        }
                    }
                }
                SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                    println!("Connection established with {:?}", peer_id);
                }
                SwarmEvent::ConnectionClosed { peer_id, .. } => {
                    println!("Connection closed with {:?}", peer_id);
                }
                SwarmEvent::NewListenAddr { address, .. } => {
                    println!("Listening on {:?}", address);
                }
                _ => {}
            }
        }
    }
}