use std::net::Ipv4Addr;

use futures::StreamExt;
use libp2p::{gossipsub, Multiaddr, PeerId, rendezvous, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p::swarm::dial_opts::{DialOpts, PeerCondition};
use libp2p::swarm::SwarmEvent;
use tokio::select;
use tracing::{debug, info};

use crate::peer::behaviour::{ClientPeerBehaviour, ClientPeerEvent};
use crate::peer::peer_swarm::create_swarm;

pub struct MemberPeerConfig {
    pub name: String,
    pub workspace_id: String,
    pub admin_peer: PeerId,
    pub rendezvous_point_address: Multiaddr,
}

pub struct MemberPeer {
    config: MemberPeerConfig,
    pub id: String,
    swarm: Swarm<ClientPeerBehaviour>,
}


impl MemberPeer {
    pub async fn create(config: MemberPeerConfig) -> Self {
        let swarm = create_swarm::<ClientPeerBehaviour>().await;
        Self {
            config,
            id: swarm.local_peer_id().to_string(),
            swarm,
        }
    }

    pub async fn run(&mut self) {
        let name = self.config.name.clone();
        info!("Peer {:?}: {:?} Starting..", name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address.clone());

        let admin_peer_id = self.config.admin_peer;
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(
                vec![rendezvous_point_address]
            )
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();


        let name_copy = name.clone();
        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            if peer_id ==  self.config.admin_peer {
                                if let Err(error) = self.swarm.behaviour_mut().rendezvous.register(
                                    rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                                     self.config.admin_peer,
                                    None,
                                ) {
                                    tracing::error!("Failed to register: {error}");
                                }
                                info!("Connection established with rendezvous point {}", peer_id);
                            }
                        }
                        SwarmEvent::ConnectionClosed { peer_id, cause,.. } => {
                            if peer_id == self.config.admin_peer {
                                tracing::error!("Lost connection to rendezvous point {:?}", cause);
                            }
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


    fn process_event(&mut self, event: ClientPeerEvent) {
        match event {
            ClientPeerEvent::Rendezvous(event) => {
                match event {
                    rendezvous::client::Event::Registered { namespace, ttl, rendezvous_node } => {
                        info!(
                            "Registered for namespace '{}' at rendezvous point {} for the next {} seconds",
                            namespace, rendezvous_node, ttl
                        );
                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                        self.swarm.behaviour_mut().gossip_sub.subscribe(&topic).unwrap();
                    }
                    _ => {
                        info!( "Rendezvous: {:?}", event);
                    }
                }
            }

            ClientPeerEvent::GossipSub(event) => {
                match event {
                    _ => {
                        info!( "GossipSub: {:?}", event);
                    }
                }
            }

            other => {
                // tracing::info!("Unhandled {:?}", other);
            }
        }
    }
}