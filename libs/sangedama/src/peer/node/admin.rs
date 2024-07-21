use std::collections::HashMap;
use std::net::Ipv4Addr;
use crate::peer::behaviour::{PeerAdminBehaviour, PeerAdminEvent};
use crate::peer::peer_swarm::create_swarm;
use futures::StreamExt;
use libp2p::swarm::SwarmEvent;
use libp2p::{gossipsub, identity, Multiaddr, PeerId, rendezvous, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p_gossipsub::TopicHash;
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};
use crate::peer::message::data::{EventType, NodeMessage};

#[derive(Default, Clone)]
pub struct AdminPeerConfig {
    pub workspace_id: String,
    pub listen_port: Option<u16>,
}

impl AdminPeerConfig {
    pub fn new(listen_port: u16, workspace_id: String) -> Self {
        Self { listen_port: Some(listen_port), workspace_id }
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

    outside_tx: tokio::sync::mpsc::Sender<NodeMessage>,

    inside_rx: tokio::sync::mpsc::Receiver<Vec<u8>>,
    inside_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
}

impl AdminPeer {
    pub async fn create(config: AdminPeerConfig, key: identity::Keypair) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<PeerAdminBehaviour>(
            key.clone(),
        ).await;
        let (outside_tx, outside_rx) = tokio::sync::mpsc::channel::<NodeMessage>(100);

        let (inside_tx, inside_rx) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        (Self {
            config,
            id: swarm.local_peer_id().to_string(),
            swarm,
            connected_peers: HashMap::new(),
            outside_tx,

            inside_tx,
            inside_rx,
        },
         outside_rx)
    }

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<Vec<u8>> {
        self.inside_tx.clone()
    }

    pub async fn run(&mut self, address: Option<Multiaddr>, cancellation_token: CancellationToken) {
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
                _ = cancellation_token.cancelled() => {
                    break;
                }
                event = self.swarm.select_next_some() => {
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            info!("Connected to {}", peer_id);
                        }
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            info!("Disconnected from {}", peer_id);
                        }
                        SwarmEvent::Behaviour(event) => {
                            self.process_event(event).await;
                        }
                        other => {
                            debug!("Unhandled {:?}", other);
                        }
                    }
                }

                message = self.inside_rx.recv() => {
                    if let Some(message) = message {
                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());

                        let distributed_message = NodeMessage::Message {
                            data: message,
                            time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() as u64,
                            created_by: self.id.clone(),
                        };
                        match self.swarm.behaviour_mut().gossip_sub.publish(topic,distributed_message.to_bytes()){
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to broadcast message: {:?}", e);
                            }
                        }
                    }
                }
            }
        }
    }


    async fn process_event(&mut self, event: PeerAdminEvent) {
        match event {
            PeerAdminEvent::Rendezvous(event) => {
                match event {
                    rendezvous::server::Event::PeerRegistered { peer, .. } => {
                        info!( "RendezvousServerConnected: {:?}", peer);

                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                        self.swarm.behaviour_mut().gossip_sub.subscribe(&topic).unwrap();
                    }
                    _ => {
                        info!( "RendezvousServer: {:?}", event);
                    }
                }
            }
            PeerAdminEvent::Ping(_) => {
                // info!( "Ping: {:?}", event);
            }
            PeerAdminEvent::Identify(_) => {
                // info!( "Identify: {:?}", event);
            }

            PeerAdminEvent::GossipSub(event) => {
                match event {
                    gossipsub::Event::Unsubscribed { topic, peer_id } => {
                        info!( "GossipSub: Unsubscribed to topic {:?} from peer: {:?}", topic , peer_id);
                        self.outside_tx.send(NodeMessage::Event {
                            time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() as u64,
                            created_by: peer_id.to_string(),
                            event: EventType::Unsubscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        }).await.expect("Outside tx failed");

                        let peers = self.connected_peers.get_mut(&topic);
                        if let Some(peers) = peers {
                            peers.retain(|p| p != &peer_id);
                        }
                    }
                    gossipsub::Event::Subscribed { topic, peer_id } => {
                        info!( "GossipSub: Subscribed to topic {:?} from peer: {:?}", topic , peer_id);
                        self.connected_peers.get_mut(&topic).unwrap_or(&mut vec![]).push(peer_id);
                        self.outside_tx.send(NodeMessage::Event {
                            time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() as u64,
                            created_by: peer_id.to_string(),
                            event: EventType::Subscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        }).await.expect("Outside tx failed");
                    }
                    gossipsub::Event::Message { message, .. } => {
                        let msg = NodeMessage::from_bytes(message.data);
                        match self.outside_tx.send(msg).await {
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to send message to outside: {:?}", e);
                            }
                        };
                    }
                    _ => {
                        info!( "GossipSub: {:?}", event);
                    }
                }
            }
        }
    }
}
