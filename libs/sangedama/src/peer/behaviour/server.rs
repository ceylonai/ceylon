use libp2p::{gossipsub, identify, rendezvous};
use libp2p::swarm::NetworkBehaviour;

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
pub struct PeerAdminBehaviour {
    pub rendezvous: rendezvous::server::Behaviour,
    pub gossip_sub: gossipsub::Behaviour,
    pub identify: identify::Behaviour,
}