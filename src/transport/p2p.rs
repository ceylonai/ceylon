use std::collections::hash_map::DefaultHasher;
use std::error::Error;
use std::hash::{Hash, Hasher};
use std::time::Duration;
use async_trait::async_trait;

use futures::{future::Either, prelude::*};
use libp2p::{
    core::{muxing::StreamMuxerBox, transport::OrTransport, upgrade},
    gossipsub, identity, mdns, noise,
    PeerId,
    swarm::{SwarmBuilder, SwarmEvent},
    tcp, Transport, yamux,
};
use libp2p::swarm::NetworkBehaviour;
use libp2p_quic as quic;
use log::{debug, error};
use tokio::sync::mpsc;
use tokio::sync::mpsc::{
    Receiver,
    Sender,
};
use crate::transport::Transporter;

use crate::types::{TransportMessage, TransportStatus};


// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
struct MyBehaviour {
    gossipsub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
}

pub struct P2PTransporter {
    owner: String,
    rx: Receiver<String>,
    tx: Sender<String>,
    msg_tx: Sender<TransportStatus>,
}

impl P2PTransporter {
    async fn send(&mut self, status: TransportStatus) {
        match self.msg_tx.clone().send(status).await {
            Ok(_) => {
                debug!("Sent message");
            }
            Err(e) => {
                error!("error {}", e);
            }
        };
    }
}

#[async_trait]
impl Transporter for P2PTransporter {
    fn new(
        msg_tx: Sender<TransportStatus>,
        owner: String,
    ) -> Self {
        let (tx, rx) = mpsc::channel(32);
        Self {
            rx,
            tx,
            msg_tx,
            owner,
        }
    }

    fn get_tx(&mut self) -> Sender<String> {
        self.tx.clone()
    }

    async fn message_processor(&mut self) -> Result<(), Box<dyn Error>> {
        let owner = self.owner.clone();
        // Create a random PeerId
        let id_keys = identity::Keypair::generate_ed25519();
        let local_peer_id = PeerId::from(id_keys.public());
        debug!("Local peer id: {local_peer_id} {owner}");

        // Set up an encrypted DNS-enabled TCP Transport over the yamux protocol.
        let tcp_transport = tcp::tokio::Transport::new(tcp::Config::default().nodelay(true))
            .upgrade(upgrade::Version::V1Lazy)
            .authenticate(noise::Config::new(&id_keys).expect("signing libp2p-noise static keypair"))
            .multiplex(yamux::Config::default())
            .timeout(std::time::Duration::from_secs(20))
            .boxed();
        let quic_transport = quic::tokio::Transport::new(quic::Config::new(&id_keys));
        let transport = OrTransport::new(quic_transport, tcp_transport)
            .map(|either_output, _| match either_output {
                Either::Left((peer_id, muxer)) => (peer_id, StreamMuxerBox::new(muxer)),
                Either::Right((peer_id, muxer)) => (peer_id, StreamMuxerBox::new(muxer)),
            })
            .boxed();

        // To content-address message, we can take the hash of message and use it as an ID.
        let message_id_fn = |message: &gossipsub::Message| {
            let mut s = DefaultHasher::new();
            message.data.hash(&mut s);
            gossipsub::MessageId::from(s.finish().to_string())
        };

        // Set a custom gossipsub configuration
        let gossipsub_config = gossipsub::ConfigBuilder::default()
            .heartbeat_interval(Duration::from_secs(10)) // This is set to aid debugging by not cluttering the log space
            .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
            .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
            .build()
            .expect("Valid config");

        // build a gossipsub network behaviour
        let mut gossipsub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(id_keys),
            gossipsub_config,
        )
            .expect("Correct configuration");
        // Create a Gossipsub topic
        let topic = gossipsub::IdentTopic::new("message-topic");
        // subscribes to our topic
        gossipsub.subscribe(&topic)?;

        // Create a Swarm to manage peers and events
        let mut swarm = {
            let mdns = mdns::tokio::Behaviour::new(mdns::Config::default(), local_peer_id)?;
            let behaviour = MyBehaviour { gossipsub, mdns };
            SwarmBuilder::with_tokio_executor(transport, behaviour, local_peer_id).build()
        };


        // Listen on all interfaces and whatever port the OS assigns
        swarm.listen_on("/ip4/0.0.0.0/udp/0/quic-v1".parse()?)?;
        swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;

        debug!("Enter messages via STDIN and they will be sent to connected peers using Gossipsub");


        self.send(TransportStatus::Started).await;
        loop {
            tokio::select! {
            message = self.rx.recv() => {
                if let Some(message) = message {
                        debug!("[Application] Sent Dispatch Message to [Transporter]-2: {}", message.clone());
                        let server_message = TransportMessage::using_bytes(message.clone());
                    if let Err(e) = swarm
                    .behaviour_mut().gossipsub
                    .publish(topic.clone(),server_message) {
                    debug!("Publish error: {e:?}");
                }
                }
            }

            event = swarm.select_next_some() => match event {
                SwarmEvent::Behaviour(MyBehaviourEvent::Mdns(mdns::Event::Discovered(list))) => {
                    for (peer_id, _multiaddr) in list {
                        let status = format!("{peer_id}");
                        self.send(TransportStatus::PeerDiscovered(status)).await;
                        swarm.behaviour_mut().gossipsub.add_explicit_peer(&peer_id);
                    }
                },
                SwarmEvent::Behaviour(MyBehaviourEvent::Mdns(mdns::Event::Expired(list))) => {
                    for (peer_id, _multiaddr) in list {
                        let status = format!("{peer_id}");
                       self.send(TransportStatus::PeerDisconnected(status)).await;
                        swarm.behaviour_mut().gossipsub.remove_explicit_peer(&peer_id);

                    }
                },
                SwarmEvent::Behaviour(MyBehaviourEvent::Gossipsub(gossipsub::Event::Message {
                    propagation_source: _peer_id,
                    message_id: _id,
                    message,})) => {
                        let data_message = TransportMessage::from_bytes(message.data);

                        let status =data_message.data;
                                debug!("[Transporter] Received Income Message from [Agent]-1: {}", status.clone());
                        self.send(TransportStatus::Data(status)).await;
                    },
                SwarmEvent::NewListenAddr { address, .. } => {
                        let status = format!("{address}");
                        self.send(TransportStatus::PeerConnected(status)).await;
                }
                _ => {}
            }
        }
        }
    }
}