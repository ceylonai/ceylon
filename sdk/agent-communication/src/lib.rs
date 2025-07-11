pub mod anp;
pub mod messaging;
pub mod handlers;
pub mod node;
pub mod behaviour;
pub mod peer;
pub mod peer_swarm;
pub mod peer_builder;
pub mod data;

pub use libp2p::PeerId;
pub use libp2p::Multiaddr;

pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}
