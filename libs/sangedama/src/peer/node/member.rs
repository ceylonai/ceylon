/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use futures::StreamExt;
use libp2p::multiaddr::Protocol;
use libp2p::swarm::{
    dial_opts::{DialOpts, PeerCondition},
    SwarmEvent,
};
use libp2p::{gossipsub, identity, rendezvous, Multiaddr, PeerId, Swarm};
use std::net::Ipv4Addr;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration};
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::peer::behaviour::{ClientPeerBehaviour, ClientPeerEvent};
use crate::peer::message::data::{EventType, MessageType, NodeMessage, NodeMessageTransporter};
use crate::peer::peer_swarm::create_swarm;
use tokio::sync::mpsc;
static CACHED_TIMESTAMP: AtomicU64 = AtomicU64::new(0);

#[derive(Debug, Clone)]
pub struct MemberPeerConfig {
    pub name: String,
    pub workspace_id: String,
    pub admin_peer: PeerId,
    pub rendezvous_point_address: Multiaddr,
    pub buffer_size: Option<usize>,
}

const DEFAULT_BUFFER_SIZE: usize = 100;
impl MemberPeerConfig {
    pub fn new(
        name: String,
        workspace_id: String,
        admin_peer: String,
        rendezvous_point_admin_port: u16,
        rendezvous_point_public_ip: String,
        buffer_size: Option<usize>,
    ) -> Self {
        let rendezvous_point_address = Multiaddr::empty()
            .with(Protocol::Ip4(
                Ipv4Addr::from_str(&rendezvous_point_public_ip).unwrap(),
            ))
            .with(Protocol::Udp(rendezvous_point_admin_port))
            .with(Protocol::QuicV1);

        Self {
            name,
            workspace_id,
            admin_peer: PeerId::from_str(&admin_peer).unwrap(),
            rendezvous_point_address,
            buffer_size,
        }
    }
}

pub struct MemberPeer {
    config: MemberPeerConfig,
    pub id: String,
    swarm: Swarm<ClientPeerBehaviour>,
    outside_tx: mpsc::Sender<NodeMessage>,
    inside_rx: mpsc::Receiver<NodeMessageTransporter>,
    inside_tx: mpsc::Sender<NodeMessageTransporter>,
}

impl MemberPeer {
    pub async fn create(
        config: MemberPeerConfig,
        key: identity::Keypair,
    ) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<ClientPeerBehaviour>(key).await;
        let (outside_tx, outside_rx) =
            mpsc::channel::<NodeMessage>(config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE));
        let (inside_tx, inside_rx) = mpsc::channel::<NodeMessageTransporter>(
            config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE),
        );

        (
            Self {
                config,
                id: swarm.local_peer_id().to_string(),
                swarm,
                outside_tx,
                inside_rx,
                inside_tx,
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

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<NodeMessageTransporter> {
        self.inside_tx.clone()
    }

    pub async fn run(&mut self, cancellation_token: CancellationToken) {
        let name = self.config.name.clone();
        info!("Peer {:?}: {:?} Starting..", name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address.clone());
        info!(
            "Peer {:?}: {:?} External address: {:?}",
            name.clone(),
            self.id.clone(),
            ext_address.clone()
        );
        let admin_peer_id = self.config.admin_peer;
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();
        info!(
            "Peer {:?}: {:?} Rendezvous point address: {:?} / admin peer: {:?}",
            name.clone(),
            self.id.clone(),
            rendezvous_point_address.clone(),
            admin_peer_id.clone()
        );

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(vec![rendezvous_point_address])
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();

        let name_copy = name.clone();

        loop {
            select! {
                _ = cancellation_token.cancelled() => {
                    break;
                }
                event = self.swarm.select_next_some() => {
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            if peer_id ==  self.config.admin_peer {
                                if let Err(error) = self.swarm.behaviour_mut().rendezvous.register(
                                    rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                                     self.config.admin_peer,
                                    None,
                                ) {
                                    error!("Failed to register: {error}");
                                }
                                info!("Connection established with rendezvous point {}", peer_id);
                            }
                        }
                        SwarmEvent::ConnectionClosed { peer_id, cause,.. } => {
                            if peer_id == self.config.admin_peer {
                                error!("Lost connection to rendezvous point {:?}", cause);
                            }
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

                        let from = node_message_tr.0;
                        let message = node_message_tr.1;
                        let to = node_message_tr.2;


                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                        let current_time=  Self::get_current_timestamp();

                        let distributed_message = NodeMessage::Message {
                            data: message,
                            time: current_time,
                            created_by: self.id.clone(),
                            message_type: if to.is_none() { MessageType::Broadcast } else { MessageType::Direct { to_peer: to.unwrap().to_string() } },
                        };
                        match self.swarm.behaviour_mut().gossip_sub.publish(topic.clone(),distributed_message.to_bytes()){
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to broadcast message from {}: {:?} Topic {:?}",name_copy, e, topic.to_string());
                            }
                        }
                    }
                }

                // Update the timestamp every 1 second
                _ = tokio::time::sleep(Duration::from_nanos(1)) => {
                    CACHED_TIMESTAMP.store(0, Ordering::Relaxed);
                }
            }
        }
    }

    async fn process_event(&mut self, event: ClientPeerEvent) {
        let name_ = self.config.name.clone();
        match event {
            ClientPeerEvent::Rendezvous(event) => match event {
                rendezvous::client::Event::Registered {
                    namespace,
                    ttl,
                    rendezvous_node,
                } => {
                    info!(
                            "Registered for namespace '{}' at rendezvous point {} for the next {} seconds",
                            namespace, rendezvous_node, ttl
                        );
                    let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                    self.swarm
                        .behaviour_mut()
                        .gossip_sub
                        .subscribe(&topic)
                        .unwrap();
                }
                _ => {
                    info!("Rendezvous: {:?}", event);
                }
            },

            ClientPeerEvent::GossipSub(event) => match event {
                gossipsub::Event::Message { message, .. } => {
                    let msg = NodeMessage::from_bytes(message.data.clone());
                    if let NodeMessage::Message {
                        message_type,
                        data,
                        created_by,
                        ..
                    } = msg
                    {
                        let current_time = Self::get_current_timestamp();
                        info!(
                            "Process Message {:?} from {}:  Topic {}",
                            message_type,
                            name_,
                            message.topic.to_string()
                        );
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
                gossipsub::Event::Subscribed { peer_id, topic } => {
                    info!("Subscribed to topic: {:?} from peer: {:?}", topic, peer_id);
                    let current_time = Self::get_current_timestamp();
                    if peer_id.to_string() == self.config.admin_peer.to_string() {
                        info!("Member {} Subscribe with Admin", name_.clone());
                        let msg = NodeMessage::Event {
                            time: current_time,
                            created_by: peer_id.to_string(),
                            event: EventType::Subscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        };
                        match self.outside_tx.send(msg).await {
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to send message to outside: {:?}", e);
                            }
                        };
                    }
                }

                gossipsub::Event::Unsubscribed { peer_id, topic } => {
                    info!(
                        "Unsubscribed from topic: {:?} from peer: {:?}",
                        topic, peer_id
                    );
                    if peer_id.to_string() == self.config.admin_peer.to_string() {
                        info!("Member {} Unsubscribe with Admin", name_.clone());
                    }
                }

                _ => {
                    info!("GossipSub: {:?}", event);
                }
            },

            _ => {
                // tracing::info!("Unhandled {:?}", other);
            }
        }
    }
}
