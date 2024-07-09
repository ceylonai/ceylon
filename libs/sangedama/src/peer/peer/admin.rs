use std::net::Ipv4Addr;
use std::str::FromStr;
use crate::peer::behaviour::PeerAdminBehaviour;
use crate::peer::peer_swarm::create_swarm;
use futures::StreamExt;
use libp2p::swarm::SwarmEvent;
use libp2p::{Multiaddr, PeerId, Swarm};
use libp2p::multiaddr::Protocol;
use tokio::select;
use tracing::{debug, info};

#[derive(Default)]
pub struct AdminPeerConfig {
    pub listen_port: Option<u16>,
}

impl AdminPeerConfig {
    pub fn new(listen_port: u16) -> Self {
        Self { listen_port: Some(listen_port) }
    }
    
    pub fn get_listen_address(&self) -> Multiaddr {
        Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(self.listen_port.unwrap_or(0)))
            .with(Protocol::QuicV1)
    }
}

pub struct AdminPeer {
    pub id: String,
    swarm: Swarm<PeerAdminBehaviour>,
    pub config: AdminPeerConfig,
}

impl AdminPeer {
    pub async fn create(config: AdminPeerConfig) -> Self {
        let swarm = create_swarm::<PeerAdminBehaviour>().await;
        Self {
            config,
            id: swarm.local_peer_id().to_string(),
            swarm,
        }
    }

    pub async fn run(&mut self, address: Option<Multiaddr>) {
        let address_ = if address.is_none() {
            Multiaddr::empty()
                .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
                .with(Protocol::Udp(self.config.listen_port.unwrap_or(0)))
                .with(Protocol::QuicV1)
        } else { address.unwrap() };

        self.swarm
            .listen_on(address_.clone())
            .unwrap();
        info!( "Listening on: {:?}", address_.to_string());

        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    info!( "Event: {:?}", event);
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            info!("Connected to {}", peer_id);
                        }
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            info!("Disconnected from {}", peer_id);
                        }
                        SwarmEvent::Behaviour(event) => {
                            self.swarm.behaviour_mut().process_event(event);
                        }
                        other => {
                            debug!("Unhandled {:?}", other);
                        }
                    }
                }
            }
        }
    }
}
