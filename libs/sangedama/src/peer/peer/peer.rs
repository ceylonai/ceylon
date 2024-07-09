use futures::StreamExt;
use libp2p::Swarm;
use libp2p::swarm::SwarmEvent;
use tokio::select;
use tracing::debug;
use crate::peer::behaviour::ClientPeerBehaviour;
use crate::peer::peer_swarm::create_swarm;

pub struct Peer {
    name: String,
    id: String,
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

    pub async fn run(&mut self) {
        self.swarm.listen_on("/ip4/0.0.0.0/udp/0/quic-v1".parse().unwrap()).unwrap();
        self.swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse().unwrap()).unwrap();
        let name_copy = self.name.clone();
        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    match event {
                        SwarmEvent::NewListenAddr { address, .. } => {
                            debug!("{:?} NewListenAddr {:?}", name_copy, address);
                        }
                        SwarmEvent::Behaviour(ev) =>{
                             match ev {
                                 _ => {
                                    debug!("{:?} WILD CARD Behaviour {:?}",name_copy, ev);
                                 }
                             }
                        }
                        _ => {
                           debug!( "{:?} WILD CARD Event {:?}",name_copy, event);
                        }, // Wildcard pattern to cover all other cases
                    }
                }
            }
        }
    }
}