/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *  
 */

use futures::StreamExt;
use libp2p::multiaddr::Protocol;
use libp2p::swarm::SwarmEvent;
use libp2p::{
    gossipsub::{self, TopicHash},
    identity, rendezvous, Multiaddr, PeerId, Swarm,
};
use std::collections::HashMap;
use std::net::Ipv4Addr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::peer::behaviour::{PeerAdminBehaviour, PeerAdminEvent};
use crate::peer::message::data::{EventType, MessageType, NodeMessage, NodeMessageTransporter};
use crate::peer::peer_swarm::create_swarm;

#[derive(Default, Clone)]
pub struct AdminPeerConfig {
    pub workspace_id: String,
    pub listen_port: Option<u16>,
    pub buffer_size: Option<usize>,
}

static CACHED_TIMESTAMP: AtomicU64 = AtomicU64::new(0);
const DEFAULT_BUFFER_SIZE: usize = 100;
impl AdminPeerConfig {
    pub fn new(listen_port: u16, workspace_id: String, buffer_size: Option<usize>) -> Self {
        Self {
            listen_port: Some(listen_port),
            workspace_id,
            buffer_size,
        }
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

    inside_rx: tokio::sync::mpsc::Receiver<NodeMessageTransporter>,
    inside_tx: tokio::sync::mpsc::Sender<NodeMessageTransporter>,

    _default_address: Multiaddr,
}

impl AdminPeer {
    pub async fn create(
        config: AdminPeerConfig,
        key: identity::Keypair,
    ) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<PeerAdminBehaviour>(key.clone()).await;
        let (outside_tx, outside_rx) = tokio::sync::mpsc::channel::<NodeMessage>(
            config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE),
        );

        let (inside_tx, inside_rx) = tokio::sync::mpsc::channel::<NodeMessageTransporter>(
            config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE),
        );

        let default_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(config.listen_port.unwrap_or(0)))
            .with(Protocol::QuicV1);

        (
            Self {
                config,
                id: swarm.local_peer_id().to_string(),
                swarm,
                connected_peers: HashMap::new(),
                outside_tx,

                inside_tx,
                inside_rx,

                _default_address: default_address,
            },
            outside_rx,
        )
    }
    fn get_current_timestamp() -> u64 {
        // First try to get the cached timestamp
        let cached = CACHED_TIMESTAMP.load(Ordering::Relaxed);

        // // Get the current system time
        // let current = SystemTime::now()
        //     .duration_since(UNIX_EPOCH)
        //     .unwrap()
        //     .as_secs_f64() as u64;
        //
        // // If the cached timestamp is too old (more than 1ms old) or zero, update it
        // if cached == 0 || current > cached {
        //     CACHED_TIMESTAMP.store(current, Ordering::Relaxed);
        //     current
        // } else {
        //     cached
        // }
        cached
    }
    pub fn get_address(&self) -> Multiaddr {
        self._default_address.clone()
    }

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<NodeMessageTransporter> {
        self.inside_tx.clone()
    }

    pub async fn run(&mut self, address: Option<Multiaddr>, cancellation_token: CancellationToken) {
        let address_ = if address.is_none() {
            self._default_address.clone()
        } else {
            address.unwrap()
        };

        self.swarm.listen_on(address_.clone()).unwrap();
        info!("Listening on: {:?}", address_.to_string());

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
                    if let Some(node_message_tr) = message {
                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                        let from = node_message_tr.0;
                        let message = node_message_tr.1;
                        let to = node_message_tr.2;


                        let distributed_message = NodeMessage::Message {
                            data: message,
                            time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() as u64,
                            created_by: self.id.clone(),
                           message_type: if to.is_none() { MessageType::Broadcast } else { MessageType::Direct { to_peer: to.unwrap().to_string() } },
                        };
                        match self.swarm.behaviour_mut().gossip_sub.publish(topic,distributed_message.to_bytes()){
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to broadcast message: {:?}", e);
                            }
                        }
                    }
                }

                // Update the timestamp every 1 nano second
                _ = tokio::time::sleep(Duration::from_nanos(1)) => {
                    CACHED_TIMESTAMP.store(0, Ordering::Relaxed);
                }
            }
        }
    }

    async fn process_event(&mut self, event: PeerAdminEvent) {
        let name_ = self.config.workspace_id.clone();
        match event {
            PeerAdminEvent::Rendezvous(event) => match event {
                rendezvous::server::Event::PeerRegistered { peer, .. } => {
                    info!("RendezvousServerConnected: {:?}", peer);

                    let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                    self.swarm
                        .behaviour_mut()
                        .gossip_sub
                        .subscribe(&topic)
                        .unwrap();
                }
                _ => {
                    info!("RendezvousServer: {:?}", event);
                }
            },
            PeerAdminEvent::Ping(_) => {
                // info!( "Ping: {:?}", event);
            }
            PeerAdminEvent::Identify(_) => {
                // info!( "Identify: {:?}", event);
            }

            PeerAdminEvent::GossipSub(event) => match event {


                gossipsub::Event::Unsubscribed { topic, peer_id } => {
                    info!(
                        "GossipSub: Unsubscribed to topic {:?} from peer: {:?}",
                        topic, peer_id
                    );
                    let current_time = Self::get_current_timestamp();
                    self.outside_tx
                        .send(NodeMessage::Event {
                            time: current_time,
                            created_by: peer_id.to_string(),
                            event: EventType::Unsubscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        })
                        .await
                        .expect("Outside tx failed");

                    let peers = self.connected_peers.get_mut(&topic);
                    if let Some(peers) = peers {
                        peers.retain(|p| p != &peer_id);
                    }
                }
                gossipsub::Event::Subscribed { topic, peer_id } => {

                    let current_time = Self::get_current_timestamp();
                    info!(
                        "GossipSub: Subscribed to topic {:?} from peer: {:?}",
                        topic, peer_id
                    );
                    self.connected_peers
                        .get_mut(&topic)
                        .unwrap_or(&mut vec![])
                        .push(peer_id);
                    self.outside_tx
                        .send(NodeMessage::Event {
                            time: current_time,
                            created_by: peer_id.to_string(),
                            event: EventType::Subscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        })
                        .await
                        .expect("Outside tx failed");
                }
                gossipsub::Event::Message { message, .. } => {
                    let msg = NodeMessage::from_bytes(message.data.clone());
                    if let NodeMessage::Message {
                        message_type,
                        data,
                        created_by,
                        ..
                    } = msg
                    {
                        info!(
                            "Process Message {:?} from {}:  Topic {}",
                            message_type,
                            name_,
                            message.topic.to_string()
                        );

                        let current_time = Self::get_current_timestamp();
                        match message_type {
                            MessageType::Direct { to_peer } => {
                                // Only process if we're the intended recipient
                                if to_peer == self.id {
                                    match self
                                        .outside_tx
                                        .send(NodeMessage::Message {
                                            time: current_time,
                                            created_by,
                                            message_type: MessageType::Direct { to_peer },
                                            data,
                                        })
                                        .await
                                    {
                                        Ok(_) => {}
                                        Err(e) => {
                                            error!("Failed to forward direct message: {:?}", e)
                                        }
                                    }
                                }
                            }
                            MessageType::Broadcast => {
                                // Process broadcast messages as before
                                match self
                                    .outside_tx
                                    .send(NodeMessage::from_bytes(message.data))
                                    .await
                                {
                                    Ok(_) => {}
                                    Err(e) => {
                                        error!("Failed to forward broadcast message: {:?}", e)
                                    }
                                }
                            }
                        }
                    }
                }
                _ => {
                    info!("GossipSub: {:?}", event);
                }
            },
        }
    }
}
