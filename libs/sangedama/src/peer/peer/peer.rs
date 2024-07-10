use std::net::Ipv4Addr;
use futures::StreamExt;
use libp2p::{Multiaddr, PeerId, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p::swarm::SwarmEvent;
use tokio::select;
use tracing::{debug, info};
use crate::peer::behaviour::ClientPeerBehaviour;
use crate::peer::peer_swarm::create_swarm;

pub struct Peer {
    name: String,
    pub id: String,
    swarm: Swarm<ClientPeerBehaviour>,
}


impl Peer {
    pub async fn create(name: String) -> Self {
        let swarm = create_swarm::<ClientPeerBehaviour>().await;
        Self {
            name,
            id: swarm.local_peer_id().to_string(),
            swarm,
        }
    }

    pub async fn run(&mut self, rendezvous_point_address: Multiaddr, admin_peer_id: PeerId) {
        info!("Peer {:?}: {:?} Starting..", self.name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address);
        self.swarm.dial(rendezvous_point_address).unwrap();

        let name_copy = self.name.clone();
        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    self.swarm.behaviour_mut().process_event(event, admin_peer_id);
                }
            }
        }
    }
}