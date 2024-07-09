use libp2p::swarm::NetworkBehaviour;

pub trait PeerBehaviour
where
    Self: NetworkBehaviour,
{
    fn new(local_public_key: libp2p::identity::Keypair) -> Self;
}