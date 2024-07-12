use std::net::Ipv4Addr;

use futures::StreamExt;
use libp2p::{Multiaddr, PeerId, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p::swarm::dial_opts::{DialOpts, PeerCondition};
use tokio::select;
use tracing::{info};

use crate::peer::behaviour::ClientPeerBehaviour;
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

        let admin_peer_id = self.config.admin_peer.clone();
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(
                vec![rendezvous_point_address]
            )
            // .extend_addresses_through_behaviour()
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();


        let name_copy = name.clone();
        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    self.swarm.behaviour_mut().process_event(event, admin_peer_id);
                }
            }
        }
    }
}