use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;

use libp2p::core::muxing::StreamMuxerBox;
use libp2p::core::transport::dummy::DummyTransport;
use libp2p::{
    futures::StreamExt,
    gossipsub, mdns, noise,
    swarm::{NetworkBehaviour, Swarm, SwarmEvent},
    tcp, tls, yamux, PeerId, SwarmBuilder,
};
use serde::{Deserialize, Serialize};
use tokio::io::{self, AsyncBufReadExt};
use tokio::sync::Mutex;

use crate::blockchain::{Block, Blockchain};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct BlockchainMessage {
    sender: String,
    blocks: Vec<Block>,
}

#[derive(NetworkBehaviour)]
struct BlockBehaviour {
    gossipsub: gossipsub::Behaviour,
    mdns: mdns::tokio::Behaviour,
}

enum Event {
    Gossipsub(gossipsub::Event),
    Mdns(mdns::Event),
}

impl BlockBehaviour {
    fn new(key: &libp2p::identity::Keypair) -> Self {
        let message_id_fn = |message: &gossipsub::Message| {
            let mut s = DefaultHasher::new();
            message.data.hash(&mut s);
            gossipsub::MessageId::from(s.finish().to_string())
        };

        // Set a custom gossipsub configuration
        let gossipsub_config = gossipsub::ConfigBuilder::default()
            .history_length(10)
            .history_gossip(10)
            .heartbeat_interval(Duration::from_secs(1)) // This is set to aid debugging by not cluttering the log space
            .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
            .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
            .build()
            .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
            .unwrap(); // Temporary hack because `build` does not return a proper `std::error::Error`.

        // build a gossipsub network behaviour
        let gossipsub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(key.clone()),
            gossipsub_config,
        )
        .unwrap();

        Self {
            gossipsub,
            mdns: mdns::tokio::Behaviour::new(mdns::Config::default(), key.public().to_peer_id())
                .unwrap(),
        }
    }
}

pub struct P2P {
    swarm: Swarm<BlockBehaviour>,
    topics: Vec<String>,
    // topics: RwLock<Vec<String>>,
}

impl P2P {
    pub async fn new() -> Self {
        let swarm = SwarmBuilder::with_new_identity()
            .with_tokio()
            .with_tcp(
                tcp::Config::default(),
                noise::Config::new,
                yamux::Config::default,
            )
            .unwrap()
            .with_quic()
            .with_other_transport(|_key| DummyTransport::<(PeerId, StreamMuxerBox)>::new())
            .unwrap()
            .with_dns()
            .unwrap()
            .with_websocket(
                (tls::Config::new, noise::Config::new),
                yamux::Config::default,
            )
            .await
            .unwrap()
            .with_relay_client(
                (tls::Config::new, noise::Config::new),
                yamux::Config::default,
            )
            .unwrap()
            .with_behaviour(|_key, relay| Ok(BlockBehaviour::new(_key)))
            .unwrap()
            .with_swarm_config(|cfg| {
                // Edit cfg here.
                cfg.with_idle_connection_timeout(Duration::from_secs(240))
            })
            .build();

        P2P {
            swarm,
            topics: vec!["test_topic".to_string()],
        }
    }

    pub fn connect(&mut self, url: &str, topic_str: &str) {
        let topic = gossipsub::IdentTopic::new(topic_str);
        match self.swarm.behaviour_mut().gossipsub.subscribe(&topic) {
            Ok(_) => {}
            Err(e) => {}
        }

        self.swarm.listen_on(url.parse().unwrap()).unwrap();
    }

    pub async fn run(&mut self) {
        let mut stdin = io::BufReader::new(io::stdin()).lines();
        let blockchain = Mutex::new(Blockchain::new(4));

        loop {
            tokio::select! {
                line = stdin.next_line() => {
                    let line = line.unwrap();
                    if let Some(line) = line {
                        let id = self.swarm.local_peer_id();
                        let mut blockchain = blockchain.lock().await;
                        blockchain.add_block(line.to_string().into_bytes());
                        let block = blockchain.get_last().clone();
                        if blockchain.is_valid() {
                            let message: BlockchainMessage = BlockchainMessage {
                                blocks: vec![block],
                                sender: id.to_string().clone(),
                            };
                            self.broadcast(message).await;
                        }
                    }
                },
                event = self.swarm.select_next_some() => match event {
                    SwarmEvent::Behaviour(ev) => {
                        match ev{
                            BlockBehaviourEvent::Gossipsub(ev) => {
                                match ev{
                                    gossipsub::Event::Message { propagation_source, message_id, message } => {
                                            let block_message:BlockchainMessage = serde_json::from_slice(message.data.as_slice()).unwrap();
                                            let mut blockchain = blockchain.lock().await;
                                            blockchain.add_block(message.data);
                                    },
                                    gossipsub::Event::Subscribed { peer_id, topic }  => {
                                        println!("Subscribed to topic: {:?}", topic);
                                        // self.subscribed_to_topic( topic.clone().into_string().as_str()).await;
                                    },
                                    _ => {
                                        println!("Unhandled gossipsub event: {:?}", ev);
                                    },
                                }
        
                            }
                            BlockBehaviourEvent::Mdns(ev) => {
                                println!("Mdns event: {:?}", ev);
                                match ev{
                                     mdns::Event::Discovered(list) => {
                                        println!("Discovered: {:?}", list);
                                        for (peer_id, _) in list {
                                            self.swarm.behaviour_mut().gossipsub.add_explicit_peer(&peer_id);
                                        }
                                    },
        
                                    mdns::Event::Expired(list) => {
                                        println!("Expired: {:?}", list);
                                        for (peer_id, _) in list {
                                            self.swarm.behaviour_mut().gossipsub.remove_explicit_peer(&peer_id);
                                        }
                                    },
                                }
                            }
                            _ => {
                                println!("Unhandled event: {:?}", ev);
                            }
                        }
                    },
                    _ => {
                         println!( "Unhandled event: {:?}", event);
                    },
                },
            }
        }
    }

    async fn broadcast(&mut self, message: BlockchainMessage) {
        let topics = self.topics.clone();

        for topic in topics.clone() {
            let topic = gossipsub::IdentTopic::new(topic);
            match self
                .swarm
                .behaviour_mut()
                .gossipsub
                .publish(topic, serde_json::to_vec(&message).unwrap().as_slice())
            {
                Ok(_) => {}
                Err(e) => {
                    println!("Error: {:?}", e);
                }
            }
        }
    }
}
