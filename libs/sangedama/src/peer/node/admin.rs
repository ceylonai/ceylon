use std::collections::HashMap;
use std::net::Ipv4Addr;
use crate::peer::behaviour::{PeerAdminBehaviour, PeerAdminEvent};
use crate::peer::peer_swarm::create_swarm;
use futures::StreamExt;
use libp2p::swarm::SwarmEvent;
use libp2p::{gossipsub, Multiaddr, PeerId, rendezvous, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p_gossipsub::TopicHash;
use tokio::select;
use tracing::{debug, info};

#[derive(Default, Clone)]
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

    connected_peers: HashMap<TopicHash, Vec<PeerId>>,
}

impl AdminPeer {
    pub async fn create(config: AdminPeerConfig) -> Self {
        let swarm = create_swarm::<PeerAdminBehaviour>().await;
        Self {
            config,
            id: swarm.local_peer_id().to_string(),
            swarm,
            connected_peers: HashMap::new(),
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
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            info!("Connected to {}", peer_id);
                        }
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            info!("Disconnected from {}", peer_id);
                        }
                        SwarmEvent::Behaviour(event) => {
                            self.process_event(event);
                        }
                        other => {
                            debug!("Unhandled {:?}", other);
                        }
                    }
                }
            }
        }
    }


    fn process_event(&mut self, event: PeerAdminEvent) {
        match event {
            PeerAdminEvent::Rendezvous(event) => {
                match event {
                    rendezvous::server::Event::PeerRegistered { peer, .. } => {
                        info!( "RendezvousServerConnected: {:?}", peer);

                        let topic = gossipsub::IdentTopic::new("test_topic");
                        self.swarm.behaviour_mut().gossip_sub.subscribe(&topic).unwrap();
                    }
                    _ => {
                        info!( "RendezvousServer: {:?}", event);
                    }
                }
            }
            PeerAdminEvent::Ping(event) => {
                // info!( "Ping: {:?}", event);
            }
            PeerAdminEvent::Identify(event) => {
                // info!( "Identify: {:?}", event);
            }

            PeerAdminEvent::GossipSub(event) => {
                match event {
                    gossipsub::Event::Unsubscribed { topic, peer_id } => {
                        info!( "GossipSub: Unsubscribed from topic {:?}", topic);
                        let peers = self.connected_peers.get_mut(&topic);
                        if let Some(peers) = peers {
                            peers.retain(|p| p != &peer_id);
                        }
                    }
                    gossipsub::Event::Subscribed { topic, peer_id } => {
                        info!( "GossipSub: Subscribed to topic {:?}", topic);
                        self.connected_peers.get_mut(&topic).unwrap_or(&mut vec![]).push(peer_id);
                    }

                    _ => {
                        info!( "GossipSub: {:?}", event);
                    }
                }
            }
        }
    }
}
